# GeoAudio Backend — Architecture Document

## 1. Project Overview

The GeoAudio backend is a GeoDjango + Django REST Framework application that serves
as the API layer for the GeoAudio iOS app. Its responsibilities are:

- Authenticating users via Google OAuth (ID token exchange → backend JWT)
- Returning a randomized batch of geotagged audio clips proximate to a given location
- Receiving and storing user play history, synced from mobile clients
- Managing audio clip content via Django Admin and bulk import tooling
- Serving audio file metadata only — audio files themselves are delivered via CDN

The backend is stateless per-request, containerized, and designed to be deployable
to any Docker-capable hosting provider without provider-specific coupling.

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────┐
│                  iOS App (client)                    │
└────────────┬─────────────────┬───────────────────────┘
             │ REST API         │ Audio stream (direct)
             ▼                 ▼
┌────────────────────┐   ┌────────────────────────────┐
│  GeoAudio Backend   │   │  CDN (django-storages       │
│  Django + DRF       │   │  abstraction layer)         │
│  Gunicorn / Uvicorn │   │  S3 / R2 / Spaces / etc.   │
└────────┬───────────┘   └────────────────────────────┘
         │
┌────────▼───────────┐
│  PostgreSQL +       │
│  PostGIS            │
│  (Docker container) │
└────────────────────┘
```

Audio files are **never proxied through Django**. The backend stores and returns CDN
URIs only. The iOS app streams directly from the CDN.

---

## 3. Repository Structure

```
geoaudio-backend/
├── config/                         # Project-level Django config
│   ├── settings/
│   │   ├── base.py                 # Shared settings
│   │   ├── local.py                # Local dev overrides
│   │   └── production.py           # Production overrides
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── audio/                      # AudioClip content management
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── admin.py
│   │   ├── managers.py             # Custom QuerySet for proximity queries
│   │   └── management/
│   │       └── commands/
│   │           └── import_clips.py # Bulk import from JSON/CSV
│   ├── accounts/                   # User auth + profile
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── services.py             # Google token verification logic
│   └── history/                    # Play history sync
│       ├── models.py
│       ├── serializers.py
│       ├── views.py
│       └── urls.py
├── docker/
│   ├── Dockerfile
│   └── entrypoint.sh
├── docker-compose.yml              # Local dev: Django + PostGIS
├── docker-compose.prod.yml         # Production variant (no dev volumes)
├── requirements/
│   ├── base.txt
│   ├── local.txt
│   └── production.txt
├── .env.example                    # Template for required env vars
├── manage.py
└── pytest.ini
```

---

## 4. Data Models

### 4.1 AudioClip

Supports two geometry types: a point + radius, or a polygon (neighborhood boundary).
Exactly one of (`location` + `radius_meters`) or `geofence` must be set per record.

```python
# apps/audio/models.py
from django.contrib.gis.db import models as gis_models
from django.db import models

class AudioClip(models.Model):
    title           = models.CharField(max_length=255)
    topic           = models.CharField(max_length=100)
    audio_uri       = models.URLField()          # CDN URL, set by admin on upload
    duration_seconds = models.IntegerField()

    # Source material — freeform, not exposed to mobile API at MVP
    source_text     = models.TextField(blank=True)

    # Geometry — one of these pairs must be populated
    location        = gis_models.PointField(null=True, blank=True, geography=True)
    radius_meters   = models.IntegerField(null=True, blank=True)
    geofence        = gis_models.PolygonField(null=True, blank=True, geography=True)

    is_active       = models.BooleanField(default=True)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['topic']),
        ]

    def clean(self):
        from django.core.exceptions import ValidationError
        has_point = self.location is not None and self.radius_meters is not None
        has_poly  = self.geofence is not None
        if has_point == has_poly:  # both or neither
            raise ValidationError(
                "Set either (location + radius_meters) or geofence, not both or neither."
            )
```

### 4.2 UserProfile

```python
# apps/accounts/models.py
class UserProfile(models.Model):
    google_sub    = models.CharField(max_length=255, unique=True)  # Google subject ID
    email         = models.EmailField(unique=True)
    display_name  = models.CharField(max_length=255)
    created_at    = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.display_name} <{self.email}>"
```

### 4.3 PlayHistoryEntry

```python
# apps/history/models.py
class PlayHistoryEntry(models.Model):
    user             = models.ForeignKey('accounts.UserProfile', on_delete=models.CASCADE,
                                         related_name='play_history')
    clip             = models.ForeignKey('audio.AudioClip', on_delete=models.CASCADE)
    played_at        = models.DateTimeField()           # client-reported timestamp
    completed        = models.BooleanField()            # False if skipped
    synced_at        = models.DateTimeField(auto_now_add=True)  # server receipt time

    class Meta:
        indexes = [
            models.Index(fields=['user', 'clip']),
            models.Index(fields=['user', 'played_at']),
        ]
        # Prevent duplicate sync submissions
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'clip', 'played_at'],
                name='unique_play_event'
            )
        ]
```

---

## 5. API Design

All endpoints live under `/api/v1/`. Versioning is in the URL path from day one.

### 5.1 Authentication

`POST /api/v1/auth/google/`

The client sends the Google ID token obtained from the iOS Google Sign-In SDK.
The backend verifies it against Google's public keys and returns a backend-issued JWT.

Request:
```json
{ "id_token": "<google_id_token>" }
```

Response `200`:
```json
{
  "access_token": "<jwt>",
  "refresh_token": "<opaque_refresh_token>",
  "user": {
    "id": 42,
    "email": "user@example.com",
    "display_name": "Jane Smith"
  }
}
```

Implementation notes:
- Use `google-auth` library to verify the ID token locally (no outbound call to Google
  per request — just JWKS-based local verification).
- On first sign-in, create a `UserProfile`. On subsequent sign-ins, update `display_name`
  and `email` if changed.
- Issue JWTs using `djangorestframework-simplejwt`. Access token TTL: 15 minutes.
  Refresh token TTL: 30 days, stored in the database for revocation support.

`POST /api/v1/auth/token/refresh/`

Standard simplejwt refresh endpoint. Client sends refresh token, receives new access token.

### 5.2 Nearby Clips

`POST /api/v1/clips/nearby/`

Authenticated. Returns a randomized batch of active clips proximate to the given location,
excluding any clip IDs the client has already seen this session.

Request:
```json
{
  "latitude": 40.6782,
  "longitude": -73.9442,
  "limit": 5,
  "exclude_ids": ["abc123", "def456"]
}
```

Response `200`:
```json
{
  "clips": [
    {
      "id": "xyz789",
      "title": "The Brooklyn Bridge Construction",
      "topic": "Infrastructure",
      "audio_uri": "https://cdn.example.com/clips/xyz789.mp3",
      "duration_seconds": 142
    }
  ]
}
```

**Query logic (in `AudioClipManager`):**

```python
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from django.db.models import Q
import random

def get_nearby_clips(lat, lng, limit, exclude_ids):
    user_point = Point(lng, lat, srid=4326)

    point_radius_qs = AudioClip.objects.filter(
        is_active=True,
        location__isnull=False,
    ).filter(
        location__dwithin=(user_point, F('radius_meters') / 111320)
        # Approximate degrees from meters; use ST_DWithin with geography=True for accuracy
    )

    geofence_qs = AudioClip.objects.filter(
        is_active=True,
        geofence__isnull=False,
        geofence__contains=user_point,
    )

    combined = (point_radius_qs | geofence_qs).exclude(id__in=exclude_ids).distinct()
    results = list(combined)
    random.shuffle(results)
    return results[:limit]
```

Note: use `geography=True` on geometry fields and `ST_DWithin` with a meter-based
distance for accurate proximity queries. The approximation above is for illustration;
the actual implementation should use PostGIS geography distance directly.

### 5.3 Play History Sync

`POST /api/v1/history/sync/`

Authenticated. Accepts a batch of play history entries from the client. Idempotent —
duplicate entries (same user + clip + played_at) are silently ignored via `update_or_create`
or `ignore_conflicts=True`.

Request:
```json
{
  "entries": [
    {
      "clip_id": "xyz789",
      "played_at": "2026-04-18T14:32:00Z",
      "completed": true
    }
  ]
}
```

Response `200`:
```json
{ "synced": 3, "ignored": 0 }
```

Use `PlayHistoryEntry.objects.bulk_create(..., ignore_conflicts=True)` for efficiency.

---

## 6. Authentication Architecture

```
iOS App                          Backend                        Google
   │                                │                              │
   │── Google Sign-In ─────────────────────────────────────────────▶│
   │◀─ id_token ────────────────────────────────────────────────────│
   │                                │                              │
   │── POST /auth/google/ ─────────▶│                              │
   │   { id_token }                 │── verify token locally ──────▶│
   │                                │   (google-auth JWKS)         │
   │                                │◀─ valid / invalid ────────────│
   │                                │                              │
   │                                │── get_or_create UserProfile   │
   │                                │── issue JWT (simplejwt)       │
   │◀─ { access_token, refresh } ──│                              │
   │                                │                              │
   │── GET /api/v1/clips/nearby/ ──▶│                              │
   │   Authorization: Bearer <jwt>  │                              │
```

---

## 7. Storage Abstraction (django-storages)

Audio files are stored in and served from an object storage provider.
The backend does not handle audio upload at MVP — files are uploaded manually
or via the Django Admin using a `URLField`. The `audio_uri` field stores the
final CDN URL directly.

When a file upload workflow is added later, `django-storages` provides a
storage backend that works with S3, Cloudflare R2, DigitalOcean Spaces,
and others via a common interface. Configure via environment variables:

```
DJANGO_STORAGE_BACKEND=storages.backends.s3boto3.S3Boto3Storage  # or equivalent
AWS_STORAGE_BUCKET_NAME=...
AWS_S3_CUSTOM_DOMAIN=...  # CDN domain
```

For MVP: `audio_uri` is set manually by the content admin. Storage abstraction
is a deferred addition once an upload workflow is needed.

---

## 8. Local Development Setup

### docker-compose.yml

```yaml
version: "3.9"
services:
  db:
    image: postgis/postgis:16-3.4
    environment:
      POSTGRES_DB: geoaudio
      POSTGRES_USER: geoaudio
      POSTGRES_PASSWORD: geoaudio
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  web:
    build:
      context: .
      dockerfile: docker/Dockerfile
    command: python manage.py runserver 0.0.0.0:8000
    environment:
      DJANGO_SETTINGS_MODULE: config.settings.local
      DATABASE_URL: postgis://geoaudio:geoaudio@db:5432/geoaudio
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    depends_on:
      - db

volumes:
  postgres_data:
```

### Dockerfile

```dockerfile
FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    gdal-bin libgdal-dev libgeos-dev libproj-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements/ requirements/
RUN pip install --no-cache-dir -r requirements/local.txt

COPY . .
```

GDAL system libraries are required for GeoDjango. The `postgis/postgis` image
provides PostGIS on the database side; the Django container needs GDAL on the
application side.

---

## 9. Environment Variables

All environment-specific configuration is via environment variables.
Never commit secrets. Provide an `.env.example` with all required keys.

```bash
# .env.example
DJANGO_SETTINGS_MODULE=config.settings.local
SECRET_KEY=change-me
DATABASE_URL=postgis://geoaudio:geoaudio@db:5432/geoaudio
GOOGLE_CLIENT_ID=<from Google Cloud Console>
ALLOWED_HOSTS=localhost,127.0.0.1
DEBUG=True

# Storage (deferred — not required at MVP)
# DJANGO_STORAGE_BACKEND=
# AWS_STORAGE_BUCKET_NAME=
# AWS_S3_CUSTOM_DOMAIN=
```

---

## 10. Content Authoring

### Django Admin
`AudioClip` is registered with a custom `ModelAdmin` that includes a map widget
(via `django.contrib.gis.admin.GISModelAdmin`) for visual geotag placement.

### Bulk Import Management Command

```
python manage.py import_clips --file clips.json
```

JSON format:
```json
[
  {
    "title": "The Brooklyn Bridge",
    "topic": "Infrastructure",
    "audio_uri": "https://cdn.example.com/clips/brooklyn-bridge.mp3",
    "duration_seconds": 142,
    "source_text": "...",
    "latitude": 40.7061,
    "longitude": -73.9969,
    "radius_meters": 400
  }
]
```

Polygon geofence import uses GeoJSON `Polygon` geometry in place of
`latitude`/`longitude`/`radius_meters`.

---

## 11. Testing Strategy

- Framework: `pytest-django` with a real PostGIS database (not SQLite — geometry
  queries must run against the actual extension).
- Fixtures: use `pytest` fixtures to create test clips with known geometry for
  proximity query assertions.
- Test database: same `postgis/postgis` Docker image, separate DB name.
- Auth tests: mock Google ID token verification with a known test payload.
- No mocking of PostGIS queries — test the actual spatial logic.

```ini
# pytest.ini
[pytest]
DJANGO_SETTINGS_MODULE = config.settings.local
```

---

## 12. Future Extensibility Hooks (Deferred, Not Forgotten)

- **Celery / task queue**: the `docker-compose.yml` can add a Redis + Celery worker
  service when needed (e.g., for async audio transcoding, scheduled jobs, email).
- **Signed CDN URLs**: swap `audio_uri` generation in the serializer to produce
  short-lived signed URLs for tiered content access. No model changes needed.
- **Server-side history filtering**: the `/clips/nearby/` query can be extended
  to join `PlayHistoryEntry` and exclude recently-heard clips without client changes.
- **Content tiering**: add a `tier` field to `AudioClip` and a `subscription_tier`
  field to `UserProfile`; filter in the nearby query.
- **Analytics**: `PlayHistoryEntry` is already the event log. Aggregate queries or
  export to a data warehouse can be layered on without model changes.
