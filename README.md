# 💧 Smart Irrigation AI

![CI](https://github.com/Divyani-Mali/agri-water-ai/actions/workflows/ci.yml/badge.svg)

A full-stack agricultural monitoring and forecasting platform for farms, fields, and sensor-driven irrigation planning. The app combines a FastAPI backend, a React dashboard, and a Python simulator to collect readings, generate irrigation forecasts, raise alerts, and support multi-user farm management.

> Sensors are simulated in software by default, but the backend is designed to accept real field data through the same API contract.

## Screenshots

| | |
|---|---|
| ![Dashboard](docs/screenshots/dashboard.png) | ![Live field](docs/screenshots/field-live.png) |
| ![Forecast](docs/screenshots/forecast.png) | ![Alerts](docs/screenshots/alerts.png) |
| ![Admin](docs/screenshots/admin.png) | ![Login](docs/screenshots/login.png) |

## Features

- JWT-based authentication with farmer/admin roles, disabled-account checks, and password reset support
- Farm and field management with per-user ownership rules so farmers only see their own records
- Real-time sensor dashboard for soil moisture, temperature, humidity, rainfall, and wind speed
- AI-powered irrigation forecast for the next 3 to 7 days using an XGBoost model
- Alert engine for dry soil, heat stress, heavy rain, and offline sensor conditions
- Admin area for user management, account toggling, role changes, and system statistics
- Sensor API key validation for secure device ingestion
- Background offline monitor that checks silent sensors every minute
- Password-reset flow with email delivery support and a local dev fallback mode

## Tech stack

| Layer | Technologies |
|---|---|
| Frontend | React, Vite, Tailwind CSS, Recharts, React Router, Axios |
| Backend | FastAPI, SQLAlchemy, Pydantic, JWT (python-jose), bcrypt |
| Database | SQLite for local development |
| ML | XGBoost, Random Forest, scikit-learn, pandas, NumPy, joblib |
| Simulator | Python-based virtual farm and sensor generator |
| Testing / CI | pytest, GitHub Actions |

## Forecast pipeline

1. The simulator creates multi-year field data across crop and soil combinations with realistic agronomic behavior.
2. Missing values are handled with interpolation and feature engineering, including temperature range, recent rainfall, soil dryness, crop coefficient, growth stage, and seasonal patterns.
3. Features derived from target variables such as ET0, ETc, and irrigation applied are excluded to reduce leakage.
4. Models are evaluated with a time-based split, holding back the final 180 days.
5. The live API builds the same feature set from current readings and predicts irrigation needs for upcoming days.

### Model results (held-out last 180 days)

| Model | MAE (mm/day) | RMSE | R² |
|---|---:|---:|---:|
| Baseline (crop average) | 1.563 | 1.852 | -0.02 |
| Random Forest | 0.086 | 0.154 | 0.993 |
| XGBoost | 0.051 | 0.094 | 0.997 |

These results are based on simulated agronomic data and validate the pipeline. They do not represent guaranteed real-farm accuracy; the system is intended to be retrained on real data from deployed fields.

## Quick start (Windows)

Requirements: Python 3.12, Node 18+, and Git.

```powershell
git clone https://github.com/Divyani-Mali/agri-water-ai.git
cd agri-water-ai
```

### 1) Backend

```powershell
cd backend
py -3.12 -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python -m ml.train
uvicorn app.main:app --reload
```

Open the API docs at http://127.0.0.1:8000/docs.

### 2) Frontend

Start a new terminal:

```powershell
cd frontend
copy .env.example .env
npm install
npm run dev
```

Open http://localhost:5173.

The very first account created becomes the admin user. If you want to test password reset locally without SMTP, enable `PASSWORD_RESET_DEV_MODE=true` in `backend/.env` and the API will return a reset link in its response.

### 3) Sensor simulator

In another terminal from the project root:

```powershell
.\backend\venv\Scripts\Activate.ps1
python simulator/run_simulator.py --email YOUR_EMAIL --password YOUR_PASSWORD --fields 1 --key change-this-sensor-key
```

The simulator key must match `SENSOR_API_KEY` in `backend/.env`. If you change the key, update both places. Use `--backfill-days 0` on later runs to avoid duplicate sensor history.

## Run tests

```powershell
cd backend
python -m pytest -q
```

## Main API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/auth/register` | Create a new user |
| POST | `/api/auth/login` | Sign in and receive a JWT |
| GET | `/api/auth/me` | Get the authenticated user |
| POST | `/api/auth/password-reset/request` | Request a password reset link |
| POST | `/api/auth/password-reset/confirm` | Reset password using a token |
| GET | `/api/farms` | List farms |
| POST | `/api/farms` | Create a farm |
| GET | `/api/farms/{farm_id}` | Get one farm |
| POST | `/api/farms/{farm_id}/fields` | Create a field |
| GET | `/api/farms/{farm_id}/fields` | List fields in a farm |
| GET | `/api/fields/{field_id}` | Get a field |
| POST | `/api/fields/{field_id}/readings` | Post sensor readings using `X-API-Key` |
| GET | `/api/fields/{field_id}/readings` | Get reading history |
| GET | `/api/fields/{field_id}/readings/latest` | Get the latest reading |
| GET | `/api/fields/{field_id}/forecast?days=3` | Fetch irrigation forecast |
| GET | `/api/alerts` | List user alerts |
| GET | `/api/admin/users` | Admin: list users |
| PATCH | `/api/admin/users/{user_id}` | Admin: enable/disable users or change roles |
| GET | `/api/admin/stats` | Admin: system stats |
| GET | `/api/ml/model-info` | Model metadata and evaluation metrics |

## Project structure

```text
agri-water-ai/
├── backend/
│   ├── app/          # FastAPI app: models, routers, schemas, services, config
│   ├── ml/           # data prep, feature engineering, model training
│   ├── tests/        # backend test suite
│   ├── .env          # local settings
│   ├── .env.example  # environment template
│   └── requirements.txt
├── frontend/         # React + Vite dashboard
├── simulator/        # synthetic weather and sensor generator
├── docs/             # screenshots and supporting docs
├── README.md
└── .gitignore
```

## Current limitations and future work

- Weather forecast inputs are still approximated from recent field conditions; integrating a live weather API would improve planning.
- The model is trained on simulated agronomic data and should be retrained with real sensor data for production use.
- Planned improvements include Dockerized deployment, PostgreSQL support, richer alert delivery channels, and more advanced sequence models.

## Team

Final-year project, Vishwakarma Institute of Information Technology, Pune.