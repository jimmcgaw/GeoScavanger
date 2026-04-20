# CLAUDE.md — GeoAudio Backend

This file is the authoritative reference for all AI agents working on this codebase.
Read it fully before writing or modifying any code.

---

## Project Summary

GeoAudio backend is a GeoDjango + Django REST Framework API server. It serves
geotagged audio clip metadata to the GeoAudio iOS app based on the user's
current location. It does NOT serve audio files — those come from a CDN directly.

**Stack:** Python 3.12, Django 5.x, GeoDjango, DRF, PostgreSQL 16 + PostGIS 3.4, Docker.

---

## Repository Structure

```
geoaudio-backend/
├── config/
│   ├── settings/
│   │   ├── base.py          # All shared settings
│   │   ├── local.py         # Local dev overrides (DEBUG=True, etc.)
│   │   └── production.py    # Production overrides
│   ├── urls.py              # Root URL conf — mounts /api/v1/
│   └── wsgi.py
├── apps/
│   ├── audio/               # AudioClip model, nearby query, admin, import command
│   ├── accounts/            # UserProfile, Google auth exchange, JWT issuance
│   └── history/             # PlayHistoryEntry, sync endpoint
├── docker/
│   ├── Dockerfile
│   └── entrypoint.sh
├── docker-compose.yml       # Local dev
├── docker-compose.prod.yml  # Production
├── requirements/
│   ├── base.txt
│   ├── local.txt
│   └── production.txt
├── .env.example
├── manage.py
└── pytest.ini
```

---

## App Responsibilities

### `apps/audio/`
- `AudioClip` model with PostGIS geometry fields.
- `AudioClipManager` with `get_nearby_clips(lat, lng, limit, exclude_ids)` method.
- DRF view + serializer for `POST /api/v1/clips/nearby/`.
- Django Admin registration with `GISModelAdmin` map widget.
- `management/commands/import_clips.py` for bulk JSON/CSV import.

### `apps/accounts/`
- `UserProfile` model keyed on Google `sub` (subject ID).
- `POST /api/v1/auth/google/` — accepts Google ID token, verifies it locally
  using `google-auth`, creates or fetches `UserProfile`, returns simplejwt tokens.
- `POST /api/v1/auth/token/refresh/` — standard simplejwt refresh.
- `services.py` contains all Google token verification logic (not in views).

### `apps/history/`
- `PlayHistoryEntry` model.
- `POST /api/v1/history/sync/` — idempotent batch upsert using
  `bulk_create(ignore_conflicts=True)`.

---

## API Versioning

All endpoints are mounted at `/api/v1/`. This is non-negotiable from day one.
Do not create unversioned endpoints. Future versions get their own prefix.

---

## URL Structure

```python
# config/urls.py
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include([
        path('auth/', include('apps.accounts.urls')),
        path('clips/', include('apps.audio.urls')),
        path('history/', include('apps.history.urls')),
    ])),
]
```

---

## Models — Critical Rules

### AudioClip geometry constraint
Every `AudioClip` must have EITHER:
- `location` (PointField) + `radius_meters` (IntegerField)
- `geofence` (PolygonField)

Never both, never neither. This is enforced in `AudioClip.clean()`. Always call
`full_clean()` before saving in tests and management commands.

All geometry fields must use `geography=True` for accurate meter-based distance
calculations via PostGIS. Do not use raw degree-based approximations in production
query logic.

### PlayHistoryEntry uniqueness
`(user, clip, played_at)` has a `UniqueConstraint`. The sync endpoint must use
`bulk_create(ignore_conflicts=True)` — never raise on duplicate sync submissions.

---

## Nearby Clips Query

The proximity query lives in `apps/audio/managers.py` on `AudioClipManager`.
It is the most performance-sensitive code in the project.

Rules:
- Use PostGIS `ST_DWithin` with geography=True for point+radius clips.
- Use PostGIS `ST_Within` / `__contains` for polygon/geofence clips.
- Union both querysets with `|`, call `.distinct()`.
- Exclude `exclude_ids` before returning.
- Randomize in Python with `random.shuffle()` on the result list — do not use
  `order_by('?')` (it is extremely slow on large tables).
- Return at most `limit` results (default 5, max 20).

Do not add sorting, ranking, or personalization logic to this method without
explicit instruction. Keep it simple and fast.

---

## Authentication Flow

1. iOS client sends Google ID token to `POST /api/v1/auth/google/`.
2. Backend verifies the token using `google.oauth2.id_token.verify_oauth2_token()`
   from the `google-auth` library (local verification, no outbound call).
3. Extract `sub`, `email`, `name` from verified payload.
4. `get_or_create` a `UserProfile` on `google_sub`.
5. Issue access + refresh tokens via `djangorestframework-simplejwt`.
6. Return tokens and basic user info.

All Google verification logic lives in `apps/accounts/services.py`, not in views.
Views call services; services contain business logic.

Access token TTL: 15 minutes.
Refresh token TTL: 30 days.

---

## Settings Architecture

Use `config/settings/base.py` for all shared settings. Never put secrets in
settings files — always read from environment variables using `os.environ` or
`python-decouple`.

`local.py` imports from `base.py` and overrides: `DEBUG=True`, relaxed
`ALLOWED_HOSTS`, console email backend.

`production.py` imports from `base.py` and overrides: `DEBUG=False`, strict
`ALLOWED_HOSTS` from env, production logging, `SECURE_*` headers.

Always set `DJANGO_SETTINGS_MODULE` via environment variable. Never hardcode it.

---

## Required Environment Variables

See `.env.example` for the full list. Key variables:

```
SECRET_KEY            # Django secret key
DATABASE_URL          # postgis://user:pass@host:port/dbname
GOOGLE_CLIENT_ID      # From Google Cloud Console — used to verify ID tokens
ALLOWED_HOSTS         # Comma-separated list
DJANGO_SETTINGS_MODULE
```

Storage variables (deferred — not required at MVP):
```
DJANGO_STORAGE_BACKEND
AWS_STORAGE_BUCKET_NAME
AWS_S3_CUSTOM_DOMAIN
```

---

## Docker & Local Dev

Local development uses `docker-compose.yml` with two services:
- `db`: `postgis/postgis:16-3.4` — provides PostgreSQL + PostGIS
- `web`: Django dev server via `manage.py runserver`

The `Dockerfile` is in `docker/Dockerfile`. It installs GDAL system libraries
(`gdal-bin`, `libgdal-dev`, `libgeos-dev`, `libproj-dev`) — these are required
by GeoDjango and must not be removed.

To start local dev:
```bash
docker-compose up
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
```

---

## Dependencies

```
# requirements/base.txt
Django>=5.0
djangorestframework
djangorestframework-simplejwt
django-environ          # or python-decouple for env var management
psycopg[binary]         # PostgreSQL adapter (psycopg3)
google-auth             # Google ID token verification
django-storages         # Storage abstraction (configured but not active at MVP)

# requirements/local.txt
-r base.txt
pytest-django
pytest-cov
factory-boy             # Test fixtures
ipython                 # Django shell enhancement

# requirements/production.txt
-r base.txt
gunicorn
```

---

## Testing Rules

- Framework: `pytest-django`.
- Tests run against a real PostGIS database — do not mock geometry operations.
- Use `factory-boy` for model factories, not raw `Model.objects.create()` in tests.
- Google ID token verification must be mocked in auth tests (use `unittest.mock.patch`
  on `google.oauth2.id_token.verify_oauth2_token`).
- The nearby clips query must be tested with real geometry (create clips at known
  coordinates, assert that a user at a given location receives the correct clips).
- All tests go in a `tests/` directory within each app.
- Use `pytest.ini` to set `DJANGO_SETTINGS_MODULE = config.settings.local`.

---

## Django Admin

`AudioClip` must be registered with `django.contrib.gis.admin.GISModelAdmin`
to enable the map widget for visual geotag placement.

`UserProfile` and `PlayHistoryEntry` are registered with standard `ModelAdmin`.
No inline editing of play history from the clip admin — keep admin simple.

---

## What NOT to Do

- Do not serve audio files through Django. The backend returns CDN URIs only.
- Do not use `order_by('?')` for randomization — it is a full table sort in Postgres.
- Do not use SQLite for any environment — PostGIS requires PostgreSQL.
- Do not put business logic in views. Views call serializers and services; services
  contain logic.
- Do not use `os.environ[]` directly in settings — use `django-environ` or
  `python-decouple` so missing variables fail loudly with clear errors.
- Do not add Celery, Redis, or any async task queue without explicit instruction.
  The history sync endpoint is synchronous at MVP.
- Do not add social features, content ratings, or sharing endpoints — deferred.
- Do not add content tiering or access control beyond basic JWT auth — deferred.
- Do not use degree-based distance approximations in production spatial queries.
  Use PostGIS geography mode (`geography=True`) for meter-accurate distances.
- Do not commit `.env` files. Only `.env.example` (with no real values) is committed.
- Do not hardcode any URLs, domain names, bucket names, or client IDs in source code.

---

## Code Style

- Follow PEP 8. Use `black` for formatting.
- Use type hints on all function signatures in `services.py` and `managers.py`.
- Write docstrings on all public methods in the Core service layer.
- Django views should be class-based (DRF `APIView` or `GenericAPIView`).
- Do not use function-based views unless there is a specific reason.
