"""Location lookup and cached hourly weather from Open-Meteo."""
from datetime import datetime, timedelta, timezone

import requests

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
HOURLY_FIELDS = (
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "wind_speed_10m",
    "et0_fao_evapotranspiration",
)


class WeatherError(RuntimeError):
    """Raised when location or live weather data cannot be retrieved."""


class OpenMeteoWeather:
    def __init__(self, session: requests.Session, past_days: int):
        if not 0 <= past_days <= 92:
            raise ValueError("backfill-days must be between 0 and 92")
        self.session = session
        self.past_days = min(past_days + 1, 92)
        self._locations: dict[str, tuple[float, float]] = {}
        self._forecasts: dict[
            tuple[float, float],
            tuple[datetime, dict[datetime, dict[str, float]]],
        ] = {}

    def prepare(self, farm: dict) -> None:
        coordinates = self._coordinates(farm)
        cached = self._forecasts.get(coordinates)
        if cached is None or datetime.now(timezone.utc) - cached[0] >= timedelta(hours=1):
            self._load_forecast(coordinates)

    def hourly(self, farm: dict, timestamp: datetime) -> dict[str, float]:
        coordinates = self._coordinates(farm)
        hour = timestamp
        if hour.tzinfo is not None:
            hour = hour.astimezone(timezone.utc).replace(tzinfo=None)
        hour = hour.replace(minute=0, second=0, microsecond=0)

        forecast = self._forecasts.get(coordinates)
        now = datetime.now(timezone.utc)
        if (
            forecast is None
            or now - forecast[0] >= timedelta(hours=1)
            or hour not in forecast[1]
        ):
            self._load_forecast(coordinates)
            forecast = self._forecasts[coordinates]

        weather = forecast[1].get(hour)
        if weather is None:
            raise WeatherError(
                f"Open-Meteo has no hourly data for {hour:%Y-%m-%d %H:%M} UTC. "
                "Reduce --backfill-days or try again later."
            )
        return weather

    def _coordinates(self, farm: dict) -> tuple[float, float]:
        latitude = farm.get("latitude")
        longitude = farm.get("longitude")
        if latitude is not None and longitude is not None:
            return float(latitude), float(longitude)

        location = str(farm.get("location") or "").strip()
        if not location:
            raise WeatherError(
                "Farm has no coordinates or location name for live weather lookup."
            )
        key = location.casefold()
        cached = self._locations.get(key)
        if cached is not None:
            return cached

        data = self._request_json(
            GEOCODING_URL,
            {
                "name": location,
                "count": 1,
                "language": "en",
                "format": "json",
            },
            "geocoding",
        )
        results = data.get("results") or []
        if not results:
            raise WeatherError(f"Could not find farm location '{location}'.")

        result = results[0]
        try:
            coordinates = (float(result["latitude"]), float(result["longitude"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise WeatherError(
                f"Geocoding returned no valid coordinates for '{location}'."
            ) from exc
        self._locations[key] = coordinates
        return coordinates

    def _load_forecast(self, coordinates: tuple[float, float]) -> None:
        data = self._request_json(
            FORECAST_URL,
            {
                "latitude": coordinates[0],
                "longitude": coordinates[1],
                "hourly": ",".join(HOURLY_FIELDS),
                "past_days": self.past_days,
                "forecast_days": 16,
                "timezone": "UTC",
                "temperature_unit": "celsius",
                "wind_speed_unit": "kmh",
                "precipitation_unit": "mm",
            },
            "weather forecast",
        )

        hourly = data.get("hourly")
        if not isinstance(hourly, dict):
            raise WeatherError("Open-Meteo returned no hourly weather data.")
        times = hourly.get("time")
        values = {name: hourly.get(name) for name in HOURLY_FIELDS}
        if not isinstance(times, list) or any(
            not isinstance(series, list) or len(series) != len(times)
            for series in values.values()
        ):
            raise WeatherError("Open-Meteo returned incomplete hourly weather data.")

        rows: dict[datetime, dict[str, float]] = {}
        for index, value in enumerate(times):
            try:
                timestamp = datetime.fromisoformat(value)
                row = {name: float(series[index]) for name, series in values.items()}
            except (TypeError, ValueError) as exc:
                # Missing weather values are omitted; a requested missing hour
                # will produce a clear error instead of fabricated sensor data.
                continue
            rows[timestamp] = row

        if not rows:
            raise WeatherError("Open-Meteo returned no usable hourly weather values.")
        self._forecasts[coordinates] = (datetime.now(timezone.utc), rows)

    def _request_json(self, url: str, params: dict, purpose: str) -> dict:
        try:
            response = self.session.get(url, params=params, timeout=20)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as exc:
            raise WeatherError(f"Open-Meteo {purpose} request failed: {exc}") from exc
        except ValueError as exc:
            raise WeatherError(f"Open-Meteo returned invalid {purpose} data.") from exc
        if not isinstance(data, dict):
            raise WeatherError(f"Open-Meteo returned invalid {purpose} data.")
        return data
