FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gdal-bin \
        libgdal-dev \
        libgeos-dev \
        libproj-dev \
        gcc \
        libpq-dev \
        binutils \
        libproj-dev \
        gdal-bin \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements/ /app/requirements/

ARG REQUIREMENTS_FILE=requirements/local.txt
RUN pip install --no-cache-dir -r ${REQUIREMENTS_FILE}

COPY . /app

RUN chmod +x /app/docker/entrypoint.sh

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
