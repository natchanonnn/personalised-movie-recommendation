FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
# Dev-style server (matches website/settings.py's "quick-start development
# settings" -- DEBUG=True by default, no whitenoise/gunicorn wired up).
# Swap for gunicorn + collectstatic if this ever needs to run with DEBUG=False.
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py runserver 0.0.0.0:8000"]
