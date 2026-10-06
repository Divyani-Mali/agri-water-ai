# 💧 Smart Irrigation AI: Agricultural Water Demand Forecasting

![CI](https://github.com/Divyani-Mali/agri-water-ai/actions/workflows/ci.yml/badge.svg)

A full-stack platform that monitors fields with (simulated) IoT sensors and uses machine learning to forecast how much water each field needs over the next 3 to 7 days. It also raises automatic alerts for dry soil, heat stress, heavy rain and offline sensors.

> **Note on data:** sensors are simulated in software (no hardware cost). The simulator generates realistic weather, soil moisture and crop water use based on FAO-56-style agronomic models. The system is designed so real sensors can post to the same API.

## Screenshots

| | |
|---|---|
| ![Dashboard](docs/screenshots/dashboard.png) | ![Live field](docs/screenshots/field-live.png) |
| ![Forecast](docs/screenshots/forecast.png) | ![Alerts](docs/screenshots/alerts.png) |
| ![Admin](docs/screenshots/admin.png) | ![Login](docs/screenshots/login.png) |

## Features

- **Authentication:** register/login with JWT, password rules, role-based access (farmer / admin), disabled accounts blocked instantly
- **Farm management:** farms and fields (crop, soil type, area, planting date) with ownership checks, so farmers only see their own data
- **Live monitoring:** soil moisture, temperature, humidity, rainfall and wind, refreshed every 5 seconds, with charts
- **AI forecast:** XGBoost model predicts daily irrigation need (mm and liters) for the next 3 to 7 days
- **Alert engine:** dry soil, heat stress, heavy rain and sensor-offline alerts with cooldowns and severity escalation
- **Admin panel:** system statistics, enable/disable users, change roles
- **Sensor security:** devices authenticate with an API key header
- **Tests and CI:** 47 automated backend tests, GitHub Actions pipeline

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React, Vite, Tailwind CSS, Recharts, React Router, Axios |
| Backend | FastAPI, SQLAlchemy, Pydantic, JWT (python-jose), bcrypt |
| Database | SQLite (development) |
| ML | XGBoost, Random Forest, scikit-learn, pandas |
| Simulator | Python (virtual farm: weather, crop coefficients, soil water balance) |
| Testing / CI | pytest, GitHub Actions |

## How the forecast works

1. The simulator generates 3 years of daily data for 8 crops × 3 soil types (about 26,000 rows) with missing sensor values added on purpose.
2. Cleaning interpolates gaps, then feature engineering adds temperature range, recent rainfall, soil dryness, crop coefficient (Kc), growth stage and seasonality.
3. Features computed from the answer (ET0, ETc, irrigation applied) are removed to prevent data leakage.
4. Models are compared on a **time-based split** (the last 180 days are held out).
5. The live API builds the same features from the field's real sensor readings and predicts the next days.

### Model results (held-out last 180 days)

| Model | MAE (mm/day) | RMSE | R² |
|---|---|---|---|
| Baseline (crop average) | 1.563 | 1.852 | -0.02 |
| Random Forest | 0.086 | 0.154 | 0.993 |
| **XGBoost** | **0.051** | **0.094** | **0.997** |

These results are on simulated data whose labels come from agronomic formulas, so they show the pipeline works. They are not a claim of real-farm accuracy. The model is meant to be retrained on real sensor data.

## Quick start (Windows)

You need Python 3.12, Node 18+ and Git.

```powershell
git clone https://github.com/Divyani-Mali/agri-water-ai.git
cd agri-water-ai
```

**1. Backend**

```powershell
cd backend
py -3.12 -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
cd ..
python simulator/generate_dataset.py
cd backend
python -m ml.train
uvicorn app.main:app --reload
```

API docs: http://127.0.0.1:8000/docs

**2. Frontend** (new terminal)

```powershell
cd frontend
copy .env.example .env
npm install
npm run dev
```

Open http://localhost:5173. The first registered user becomes the admin.

**3. Sensor simulator** (new terminal, from the project root)

```powershell
backend\venv\Scripts\activate
python simulator/run_simulator.py --email YOUR_EMAIL --password YOUR_PASSWORD --fields 1
```

Use `--backfill-days 0` on later runs to avoid duplicate history. Use `--key` if you changed `SENSOR_API_KEY`.

## Run tests

```powershell
cd backend
python -m pytest -q
```

## Main API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/auth/register` | Create account |
| POST | `/api/auth/login` | Get JWT token |
| GET | `/api/auth/me` | Current user |
| GET/POST | `/api/farms` | List / create farms |
| GET/POST | `/api/farms/{id}/fields` | List / create fields |
| POST | `/api/fields/{id}/readings` | Sensor data in (API key) |
| GET | `/api/fields/{id}/readings` | Reading history |
| GET | `/api/fields/{id}/forecast?days=3` | AI irrigation forecast |
| GET | `/api/alerts` | Alerts for the user |
| GET | `/api/admin/users` | User management (admin) |

## Project structure

```
agri-water-ai/
├── backend/
│   ├── app/          # FastAPI: routers, models, schemas, services
│   ├── ml/           # features, training, saved model
│   └── tests/        # 47 automated tests
├── frontend/         # React app
├── simulator/        # virtual farm + dataset generator + live sensor script
└── docs/             # charts and screenshots
```

## Limitations and future work

- Future weather is assumed equal to the last 3 days; a weather-forecast API would improve accuracy.
- Trained on simulated data; the next step is to retrain on real sensor data.
- Planned: Docker + PostgreSQL deployment, LSTM time-series model, SMS/email alerts.

## Team

Final-year project, Vishwakarma Institute of Information Technology, Pune.