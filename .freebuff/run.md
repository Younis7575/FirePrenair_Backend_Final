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

## Flutter on iPad (responsive audit)
Backend chalu rakho, phir:
```bash
cd /Users/apple/Desktop/FirePrenair_Final
# unit + integration tests (matrix: 5 viewport profiles, real API)
flutter test
flutter test integration_test/responsive_audit_test.dart \
  -d <iPad-udid> --dart-define=API_HOST=127.0.0.1
# run/debug on the simulator
flutter run -d <iPad-udid> --dart-define=API_HOST=127.0.0.1
# if `flutter build ios --simulator` fails (exit 255), build via xcodebuild:
cd ios && xcodebuild -workspace Runner.xcworkspace -scheme Runner \
  -configuration Debug -sdk iphonesimulator \
  -destination 'platform=iOS Simulator,id=<udid>' build
# product lands in ~/Library/Developer/Xcode/DerivedData/Runner-*/
#   Build/Products/Debug-iphonesimulator/Runner.app
xcrun simctl install <udid> <path-to-Runner.app>
xcrun simctl launch <udid> com.example.firetrainerapp
```
Login (local backend): admin@example.com / admin123

NOTE: the default home API uses `home/home/`; the public content endpoints
(pricing, features, legal pages, digi categories) are AllowAny since the
Sep 2026 audit — no token needed for them.

## Files Changed (this session — gap analysis fixes)
- `core_api/missing_apis_v3.py` — NEW: profile recovery, check availability, admin sales, send tag email
- `core_api/missing_urls.py` — UPDATED: registered all v3 APIs + disconnected APIs
