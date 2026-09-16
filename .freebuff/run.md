# FirePrenair Dev Server

## How to Reproduce
1. Copy `.env` from the main checkout if missing
2. `cd prenair && source venv/bin/activate`
3. `pip install -r requirements.txt` (if needed)
4. `python manage.py migrate`
5. `python manage.py runserver 0.0.0.0:8000`

## How to Run
```bash
cd /Users/apple/Desktop/Fireprenair-main/prenair
source venv/bin/activate
DJANGO_SETTINGS_MODULE=prenair.settings python manage.py runserver 0.0.0.0:8000
```

Server: http://127.0.0.1:8000
Admin: http://127.0.0.1:8000/admin/ (admin / admin123)

## Files Changed (this session — gap analysis fixes)
- `core_api/missing_apis_v3.py` — NEW: profile recovery, check availability, admin sales, send tag email
- `core_api/missing_urls.py` — UPDATED: registered all v3 APIs + disconnected APIs
