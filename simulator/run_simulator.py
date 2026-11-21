"""Live virtual IoT sensors: sends readings to the API like real devices would."""
import argparse
import getpass
import os
import sys
import time
from datetime import date, datetime, timedelta, timezone

import numpy as np
import requests

from sensor_model import (
    MM_TO_PCT, SOILS, crop_coefficient, irrigation_trigger,
)
from weather_client import OpenMeteoWeather, WeatherError


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def clip(v, lo, hi):
    return float(min(max(v, lo), hi))


class FieldSim:
    """Simulates the sensors of ONE field."""

    def __init__(self, info: dict, seed: int, weather: OpenMeteoWeather):
        self.field_id = info["id"]
        self.name = info["name"]
        self.crop = info["crop_type"]
        self.soil = info["soil_type"]
        self.planting = date.fromisoformat(info["planting_date"])
        self.farm = info["farm"]
        self.weather = weather
        self.rng = np.random.default_rng(seed + self.field_id)
        self.moisture = SOILS[self.soil]["fc"] * 0.9
        self.last_tick: datetime | None = None
        self.irrigations = 0

    def _advance_soil(self, start: datetime, end: datetime) -> float:
        rainfall = 0.0
        cursor = start
        while cursor < end:
            hour = cursor.replace(minute=0, second=0, microsecond=0)
            segment_end = min(end, hour + timedelta(hours=1))
            fraction = (segment_end - cursor).total_seconds() / 3600
            weather = self.weather.hourly(self.farm, hour)
            day_in_season = (hour.date() - self.planting).days
            kc = crop_coefficient(self.crop, day_in_season)
            rain = weather["precipitation"] * fraction
            etc = weather["et0_fao_evapotranspiration"] * kc * fraction

            rainfall += rain
            self.moisture += (0.8 * rain - etc) * MM_TO_PCT
            soil = SOILS[self.soil]
            self.moisture = min(max(self.moisture, soil["wp"]), soil["fc"])
            if self.moisture < irrigation_trigger(self.soil):
                self.moisture = soil["fc"]
                self.irrigations += 1
            cursor = segment_end
        return rainfall

    def tick(self, sim_time: datetime) -> dict:
        """Return a sensor reading using weather at the farm's location."""
        if self.last_tick is None:
            rainfall = 0.0
        elif sim_time < self.last_tick:
            raise ValueError("Simulator timestamps must be chronological.")
        else:
            rainfall = self._advance_soil(self.last_tick, sim_time)
        self.last_tick = sim_time
        weather = self.weather.hourly(self.farm, sim_time)

        n = self.rng.normal
        return {
            "soil_moisture": round(clip(self.moisture + n(0, 0.3), 0, 100), 2),
            "temperature": round(clip(weather["temperature_2m"] + n(0, 0.2), -10, 60), 2),
            "humidity": round(clip(weather["relative_humidity_2m"] + n(0, 1.0), 0, 100), 2),
            "rainfall": round(clip(rainfall, 0, 500), 2),
            "wind_speed": round(clip(weather["wind_speed_10m"] + n(0, 0.5), 0, 200), 2),
        }


def login(session, api, email, password) -> str:
    r = session.post(f"{api}/api/auth/login", data={"username": email, "password": password}, timeout=10)
    if r.status_code != 200:
        sys.exit(f"Login failed ({r.status_code}): {r.text}")
    return r.json()["access_token"]


def fetch_field(session, api, token, field_id) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    r = session.get(f"{api}/api/fields/{field_id}", headers=headers, timeout=10)
    if r.status_code != 200:
        sys.exit(f"Field {field_id} not available ({r.status_code}). Check the field id and login.")
    field = r.json()
    farm_response = session.get(
        f"{api}/api/farms/{field['farm_id']}", headers=headers, timeout=10
    )
    if farm_response.status_code != 200:
        sys.exit(f"Could not load farm location for field {field_id} ({farm_response.status_code}).")
    field["farm"] = farm_response.json()
    return field


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


def send(session, api, key, token, field_id, reading, ts) -> bool:
    payload = {**reading, "timestamp": ts.isoformat()}
    r = session.post(
        f"{api}/api/fields/{field_id}/readings",
        json=payload,
        headers={"X-API-Key": key, "Authorization": f"Bearer {token}"},
        timeout=10,
    )
    if r.status_code == 401:
        sys.exit("Sensor API key rejected. Check --key against SENSOR_API_KEY in backend/.env")
    if r.status_code != 201:
        print(f"  ! field {field_id}: {r.status_code} {r.text[:120]}")
        return False
    return True


def main():
    p = argparse.ArgumentParser(description="Virtual IoT sensors using local farm weather")
    p.add_argument("--api", default="http://127.0.0.1:8000")
    p.add_argument("--email", required=True)
    p.add_argument("--password", help="account password (prompted if omitted)")
    p.add_argument(
        "--key",
        default=os.getenv("SENSOR_API_KEY"),
        help="sensor API key; must match SENSOR_API_KEY in backend/.env",
    )
    p.add_argument(
        "--fields",
        required=True,
        help="field IDs shown on the dashboard (comma-separated) or 'all' (admin only)",
    )
    p.add_argument("--interval", type=float, default=3.0, help="real seconds between live readings")
    p.add_argument(
        "--backfill-days",
        type=int,
        default=14,
        help="weather history to create first (0 = none; maximum 92 days)",
    )
    p.add_argument("--dropout", type=float, default=0.03, help="chance a sensor misses a reading")
    p.add_argument("--seed", type=int, default=2026)
    args = p.parse_args()
    password = args.password or os.getenv("SIMULATOR_PASSWORD")
    if password is None:
        password = getpass.getpass("Account password: ")
    if not args.key:
        p.error("Set SENSOR_API_KEY or provide --key.")

    if args.interval <= 0:
        p.error("--interval must be greater than zero.")
    if not 0 <= args.dropout <= 1:
        p.error("--dropout must be between 0 and 1.")
    if not 0 <= args.backfill_days <= 92:
        p.error("--backfill-days must be between 0 and 92.")

    api = args.api.rstrip("/")
    session = requests.Session()
    rng = np.random.default_rng(args.seed)

    try:
        token = login(session, api, args.email, password)
        if args.fields.strip().lower() == "all":
            ids = fetch_all_field_ids(session, api, token)
        else:
            try:
                ids = [int(x) for x in args.fields.split(",") if x.strip()]
            except ValueError:
                p.error("--fields must contain numeric field IDs or 'all'.")
            if not ids:
                sys.exit("Provide at least one field ID or use --fields all.")
            if any(field_id < 1 for field_id in ids):
                p.error("Field IDs must be positive integers.")
        field_info = [fetch_field(session, api, token, field_id) for field_id in ids]
        weather = OpenMeteoWeather(session, args.backfill_days)
        sims = [
            FieldSim(info, args.seed, weather)
            for info in field_info
        ]
        for sim in sims:
            weather.prepare(sim.farm)
    except WeatherError as exc:
        sys.exit(str(exc))
    except requests.exceptions.RequestException:
        sys.exit("Cannot reach the API. Is the server running (uvicorn app.main:app --reload)?")

    for s in sims:
        print(f"Simulating field {s.field_id} '{s.name}': {s.crop} on {s.soil} soil")

    now = utc_now()
    sim_clock = now.replace(minute=0, second=0, microsecond=0)

    # 1) history, so charts and ML have data immediately
    if args.backfill_days > 0:
        sim_clock -= timedelta(days=args.backfill_days)
        for sim in sims:
            sim.last_tick = sim_clock
        sent = 0
        try:
            while sim_clock <= now:
                for s in sims:
                    reading = s.tick(sim_clock)
                    if rng.random() >= args.dropout:
                        sent += send(session, api, args.key, token, s.field_id, reading, sim_clock)
                if sim_clock.hour == 0:
                    print(f"  history up to {sim_clock:%Y-%m-%d} ... {sent} readings sent")
                sim_clock += timedelta(hours=1)
            print(f"Backfill done: {sent} readings sent.\n")
        except WeatherError as exc:
            sys.exit(str(exc))

    # 2) live mode: use current weather and real timestamps
    print("Live mode started. Press Ctrl+C to stop.\n")
    try:
        while True:
            sim_time = utc_now()
            for s in sims:
                reading = s.tick(sim_time)
                if rng.random() < args.dropout:
                    print(f"[{sim_time:%H:%M:%S}] field {s.field_id}: sensor offline (missed reading)")
                    continue
                if send(session, api, args.key, token, s.field_id, reading, sim_time):
                    print(
                        f"[{sim_time:%H:%M:%S}] field {s.field_id}: "
                        f"moisture {reading['soil_moisture']}%  temp {reading['temperature']}C  "
                        f"humidity {reading['humidity']}%  rain {reading['rainfall']}mm  "
                        f"wind {reading['wind_speed']}km/h"
                    )
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nSimulator stopped.")
    except WeatherError as exc:
        sys.exit(str(exc))
    except requests.exceptions.RequestException:
        sys.exit("Cannot reach the API. Is the server running (uvicorn app.main:app --reload)?")


if __name__ == "__main__":
    main()