# API guide for the frontend

Backend: http://127.0.0.1:8000 (start it with `uvicorn app.main:app --reload` inside `backend`)
Interactive docs with every endpoint: http://127.0.0.1:8000/docs

## Login flow
1. `POST /api/auth/register` with JSON `{ "email", "full_name", "password" }`. Password: at least 8 characters, with a letter and a number. The first registered user becomes admin.
2. `POST /api/auth/login` as **form-urlencoded** (not JSON) with `username` (the email) and `password`. Returns `{ "access_token", "token_type": "bearer" }`.
3. Send `Authorization: Bearer <token>` on every other request.
4. `GET /api/auth/me` returns the logged-in user (`id, email, full_name, role, is_active, created_at`). Role is `farmer` or `admin`.

## Password reset
- `POST /api/auth/password-reset/request` with `{ "email" }` sends a one-time reset link when the address belongs to an active account. The response is generic to avoid account enumeration.
- `POST /api/auth/password-reset/confirm` with `{ "token", "password" }` changes the password. Tokens expire after 30 minutes and can only be used once.
- Configure `SMTP_HOST`, `SMTP_PORT`, `SMTP_FROM`, and optional SMTP credentials in `backend/.env` to deliver reset email. `PASSWORD_RESET_DEV_MODE=true` returns the link in the API response for local testing only; keep it `false` in production.

## Errors
- Most errors: `{ "detail": "readable message" }`.
- Validation errors (422): `detail` is a list, show `detail[0].msg`.
- 401 = missing or expired token, send the user to login. 403 = disabled account or admin-only page. 404 = not found, or it belongs to someone else.

## Data
- Farms: `GET/POST /api/farms` (`name, location, latitude?, longitude?`), `GET/DELETE /api/farms/{id}`
- Fields: `GET/POST /api/farms/{farm_id}/fields`, `GET/DELETE /api/fields/{id}`
  - `crop_type`: wheat, rice, cotton, sugarcane, maize, soybean, tomato, onion
  - `soil_type`: sandy, loamy, clay
  - `area_acres` > 0, `planting_date` as YYYY-MM-DD and not in the future
- Sensor readings (newest first): `GET /api/fields/{id}/readings?limit=100`, `GET /api/fields/{id}/readings/latest`. Device `POST /api/fields/{id}/readings` requests require the `X-API-Key` header to match `SENSOR_API_KEY` in `backend/.env` (the copied `.env.example` value is `change-this-sensor-key`).
  - `id, field_id, timestamp, soil_moisture (%), temperature (C), humidity (%), rainfall (mm), wind_speed (km/h)`
  - Timestamps are UTC without a "Z". Add "Z" before parsing in JavaScript.
- Forecast: `GET /api/fields/{id}/forecast?days=1..7` returns `forecast: [{ target_date, growth_stage, kc, predicted_water_mm, total_liters }]` plus `model_name`, `assumptions`. It returns 400 until the field has one full day of readings.
- Alerts: `GET /api/alerts?unread_only=true&limit=50`, `GET /api/alerts/unread-count` (returns `{ count }`), `POST /api/alerts/{id}/read`, `POST /api/alerts/read-all`
  - `alert_type`: dry_soil, heat_stress, heavy_rain, sensor_offline. `severity`: info, warning, critical.
- Admin only: `GET /api/admin/stats`, `GET /api/admin/users`, `PATCH /api/admin/users/{id}` with `{ is_active?, role? }`

## Useful numbers for gauges
Soil moisture range in %, from wilting point (empty) to field capacity (full): sandy 8 to 20, loamy 14 to 32, clay 24 to 42. Irrigation is needed when moisture falls below the half-way point.

## Suggested refresh rates
Sensor readings every 5 seconds, alert count every 15 seconds.