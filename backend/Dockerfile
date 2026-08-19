FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Only touches STATIC_ROOT/whitenoise's manifest
RUN python manage.py collectstatic --noinput

EXPOSE 8000
# gunicorn serves website.wsgi:application directly
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn website.wsgi:application --bind 0.0.0.0:8000 --workers ${GUNICORN_WORKERS:-3}"]
