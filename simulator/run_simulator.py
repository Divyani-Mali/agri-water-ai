"""Live virtual IoT sensors: sends readings to the API like real devices would."""
import argparse
import math
import sys
import time
from datetime import date, datetime, timedelta, timezone

import numpy as np
import requests

from sensor_model import (
    CROPS, HOUR_WEIGHTS, HOUR_WEIGHT_SUM, MM_TO_PCT, SOILS, crop_coefficient,
    generate_daily_weather, irrigation_trigger, reference_et,
)

LATITUDE = 18.5


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def clip(v, lo, hi):
    return float(min(max(v, lo), hi))


class FieldSim:
    """Simulates the sensors of ONE field."""

    def __init__(self, info: dict, seed: int):
        self.field_id = info["id"]
        self.name = info["name"]
        self.crop = info["crop_type"]
        self.soil = info["soil_type"]
        self.planting = date.fromisoformat(info["planting_date"])
        self.rng = np.random.default_rng(seed + self.field_id)
        self.moisture = SOILS[self.soil]["fc"] * 0.9
        self.today = None
        self.day = None
        self.etc_day = 0.0
        self.rain_hours: list[int] = []
        self.irrigations = 0

    def _new_day(self, d: date):
        doy = d.timetuple().tm_yday
        self.day = generate_daily_weather(doy, self.rng)
        w = self.day
        et0 = reference_et(w["temp_max"], w["temp_min"], w["humidity"], w["wind_speed"], doy, LATITUDE)
        day_in_season = (d - self.planting).days % CROPS[self.crop]["days"]
        self.etc_day = crop_coefficient(self.crop, day_in_season) * et0
        if w["rainfall"] > 0:
            start = int(self.rng.integers(12, 18))
            self.rain_hours = list(range(start, start + 4))
        else:
            self.rain_hours = []
        self.today = d

    def tick(self, sim_time: datetime) -> dict:
        """Advance the farm by one simulated hour and return a sensor reading."""
        if self.today != sim_time.date():
            self._new_day(sim_time.date())
        h = sim_time.hour
        w = self.day
        s = SOILS[self.soil]

        tmean = (w["temp_max"] + w["temp_min"]) / 2
        temp = tmean + (w["temp_max"] - w["temp_min"]) / 2 * math.sin(2 * math.pi * (h - 9) / 24)
        humidity = w["humidity"] - (temp - tmean) * 1.5
        wind = w["wind_speed"] * (0.8 + 0.4 * math.sin(2 * math.pi * (h - 8) / 24))
        rain = w["rainfall"] / len(self.rain_hours) if h in self.rain_hours else 0.0

        etc_hour = self.etc_day * HOUR_WEIGHTS[h] / HOUR_WEIGHT_SUM
        self.moisture += (0.8 * rain - etc_hour) * MM_TO_PCT
        self.moisture = min(max(self.moisture, s["wp"]), s["fc"])
        if self.moisture < irrigation_trigger(self.soil):  # automatic irrigation
            self.moisture = s["fc"]
            self.irrigations += 1

        n = self.rng.normal
        return {
            "soil_moisture": round(clip(self.moisture + n(0, 0.3), 0, 100), 2),
            "temperature": round(clip(temp + n(0, 0.2), -10, 60), 2),
            "humidity": round(clip(humidity + n(0, 1.0), 0, 100), 2),
            "rainfall": round(clip(rain, 0, 500), 2),
            "wind_speed": round(clip(wind + n(0, 0.5), 0, 200), 2),
        }


def login(session, api, email, password) -> str:
    r = session.post(f"{api}/api/auth/login", data={"username": email, "password": password}, timeout=10)
    if r.status_code != 200:
        sys.exit(f"Login failed ({r.status_code}): {r.text}")
    return r.json()["access_token"]


def fetch_field(session, api, token, field_id) -> dict:
    r = session.get(f"{api}/api/fields/{field_id}", headers={"Authorization": f"Bearer {token}"}, timeout=10)
    if r.status_code != 200:
        sys.exit(f"Field {field_id} not available ({r.status_code}). Check the field id and login.")
    return r.json()


def fetch_all_field_ids(session, api, token) -> list[int]:
    headers = {"Authorization": f"Bearer {token}"}
    user_response = session.get(f"{api}/api/auth/me", headers=headers, timeout=10)
    if user_response.status_code != 200:
        sys.exit(f"Could not verify account ({user_response.status_code}). Check the login.")
    if user_response.json().get("role") != "admin":
        sys.exit("--fields all requires an admin account so it can access every user's farms.")

    farms_response = session.get(f"{api}/api/farms", headers=headers, timeout=10)
    if farms_response.status_code != 200:
        sys.exit(f"Could not list farms ({farms_response.status_code}).")

    field_ids = []
    for farm in farms_response.json():
        fields_response = session.get(
            f"{api}/api/farms/{farm['id']}/fields", headers=headers, timeout=10
        )
        if fields_response.status_code != 200:
            sys.exit(f"Could not list fields for farm {farm['id']} ({fields_response.status_code}).")
        field_ids.extend(field["id"] for field in fields_response.json())

    if not field_ids:
        sys.exit("No fields found to simulate.")
    return field_ids


def send(session, api, key, field_id, reading, ts) -> bool:
    payload = {**reading, "timestamp": ts.isoformat()}
    r = session.post(
        f"{api}/api/fields/{field_id}/readings",
        json=payload, headers={"X-API-Key": key}, timeout=10,
    )
    if r.status_code == 401:
        sys.exit("Sensor API key rejected. Check --key against SENSOR_API_KEY in backend/.env")
    if r.status_code != 201:
        print(f"  ! field {field_id}: {r.status_code} {r.text[:120]}")
        return False
    return True


def main():
    p = argparse.ArgumentParser(description="Virtual IoT sensor simulator")
    p.add_argument("--api", default="http://127.0.0.1:8000")
    p.add_argument("--email", required=True)
    p.add_argument("--password", required=True)
    p.add_argument("--key", default="agri-sensor-key-12345")
    p.add_argument("--fields", default="1", help="comma-separated field IDs (e.g. 1,2) or 'all' (admin only)")
    p.add_argument("--interval", type=float, default=3.0, help="real seconds between live readings")
    p.add_argument("--backfill-days", type=int, default=14, help="history to create first (0 = none)")
    p.add_argument("--dropout", type=float, default=0.03, help="chance a sensor misses a reading")
    p.add_argument("--seed", type=int, default=2026)
    args = p.parse_args()

    api = args.api.rstrip("/")
    session = requests.Session()
    rng = np.random.default_rng(args.seed)

    try:
        token = login(session, api, args.email, args.password)
        if args.fields.strip().lower() == "all":
            ids = fetch_all_field_ids(session, api, token)
        else:
            ids = [int(x) for x in args.fields.split(",") if x.strip()]
            if not ids:
                sys.exit("Provide at least one field ID or use --fields all.")
        sims = [FieldSim(fetch_field(session, api, token, i), args.seed) for i in ids]
    except requests.exceptions.ConnectionError:
        sys.exit("Cannot reach the API. Is the server running (uvicorn app.main:app --reload)?")

    for s in sims:
        print(f"Simulating field {s.field_id} '{s.name}': {s.crop} on {s.soil} soil")

    now = utc_now()
    sim_clock = now.replace(minute=0, second=0, microsecond=0)

    # 1) history, so charts and ML have data immediately
    if args.backfill_days > 0:
        sim_clock -= timedelta(days=args.backfill_days)
        sent = 0
        while sim_clock <= now:
            for s in sims:
                reading = s.tick(sim_clock)
                if rng.random() >= args.dropout:
                    sent += send(session, api, args.key, s.field_id, reading, sim_clock)
            if sim_clock.hour == 0:
                print(f"  history up to {sim_clock:%Y-%m-%d} ... {sent} readings sent")
            sim_clock += timedelta(hours=1)
        print(f"Backfill done: {sent} readings sent.\n")

    # 2) live mode: one simulated hour per tick, stamped with the real time
    print("Live mode started. Press Ctrl+C to stop.\n")
    try:
        while True:
            for s in sims:
                reading = s.tick(sim_clock)
                if rng.random() < args.dropout:
                    print(f"[{utc_now():%H:%M:%S}] field {s.field_id}: sensor offline (missed reading)")
                    continue
                if send(session, api, args.key, s.field_id, reading, utc_now()):
                    print(
                        f"[{utc_now():%H:%M:%S}] field {s.field_id}: "
                        f"moisture {reading['soil_moisture']}%  temp {reading['temperature']}C  "
                        f"humidity {reading['humidity']}%  rain {reading['rainfall']}mm  "
                        f"wind {reading['wind_speed']}km/h"
                    )
            sim_clock += timedelta(hours=1)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nSimulator stopped.")


if __name__ == "__main__":
    main()