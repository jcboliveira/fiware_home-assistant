"""FIWARE integration for Home Assistant.

This integration polls a FIWARE context broker for `AirQualityObserved` and
`WeatherObserved` entities and exposes them as native Home Assistant sensors.

Configuration (configuration.yaml):

fiware:
  api_url: https://broker.fiware.urbanplatform.portodigital.pt/v2/entities
  scan_interval: 60
  stations:  # optional comma-separated include list
    - Station A
  exclude:  # optional comma-separated exclude list
    - Station B

This is a minimal, self-contained integration that uses the DataUpdateCoordinator
to fetch data and create sensor entities for each measurement.
"""

from __future__ import annotations

from datetime import timedelta, datetime, timezone
import logging
import re
import unicodedata
from typing import Any

from homeassistant.core import HomeAssistant
import yaml
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
import importlib

DOMAIN = "fiware"

_LOGGER = logging.getLogger(__name__)


# AQI helpers ported from the original script
def calc_aqi(value: float, breakpoints: list[tuple[float, float, int, int]]) -> int | None:
    for bp in breakpoints:
        c_low, c_high, aqi_low, aqi_high = bp
        if c_low <= value <= c_high:
            return round(((aqi_high - aqi_low) / (c_high - c_low)) * (value - c_low) + aqi_low)
    return None


def compute_aqi(entity: dict[str, Any]) -> int | None:
    aqi_values = []

    if "pm25" in entity:
        aqi = calc_aqi(
            entity["pm25"]["value"],
            [
                (0.0, 12.0, 0, 50),
                (12.1, 35.4, 51, 100),
                (35.5, 55.4, 101, 150),
                (55.5, 150.4, 151, 200),
            ],
        )
        if aqi:
            aqi_values.append(aqi)

    if "pm10" in entity:
        aqi = calc_aqi(
            entity["pm10"]["value"],
            [(0, 54, 0, 50), (55, 154, 51, 100), (155, 254, 101, 150)],
        )
        if aqi:
            aqi_values.append(aqi)

    if "o3" in entity:
        aqi = calc_aqi(entity["o3"]["value"], [(0, 100, 0, 100), (101, 160, 101, 150)])
        if aqi:
            aqi_values.append(aqi)

    if "no2" in entity:
        aqi = calc_aqi(entity["no2"]["value"], [(0, 100, 0, 100), (101, 200, 101, 150)])
        if aqi:
            aqi_values.append(aqi)

    return max(aqi_values) if aqi_values else None


def compute_main_pollutant(entity: dict[str, Any]) -> str:
    pollutants: dict[str, int | None] = {}

    if "pm25" in entity:
        pollutants["pm25"] = calc_aqi(
            entity["pm25"]["value"],
            [
                (0.0, 12.0, 0, 50),
                (12.1, 35.4, 51, 100),
                (35.5, 55.4, 101, 150),
                (55.5, 150.4, 151, 200),
            ],
        )

    if "pm10" in entity:
        pollutants["pm10"] = calc_aqi(
            entity["pm10"]["value"], [(0, 54, 0, 50), (55, 154, 51, 100), (155, 254, 101, 150)]
        )

    if "o3" in entity:
        pollutants["o3"] = calc_aqi(entity["o3"]["value"], [(0, 100, 0, 100), (101, 160, 101, 150)])

    if "no2" in entity:
        pollutants["no2"] = calc_aqi(entity["no2"]["value"], [(0, 100, 0, 100), (101, 200, 101, 150)])

    pollutants = {k: v for k, v in pollutants.items() if v is not None}

    return max(pollutants, key=pollutants.get) if pollutants else "unknown"


def normalize_station_name(name: str) -> str:
    name = unicodedata.normalize("NFD", name)
    name = "".join(c for c in name if unicodedata.category(c) != "Mn")
    name = name.lower()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    return name.strip("_")


def parse_fiware_datetime(dt: str) -> datetime:
    if dt.endswith("Z"):
        dt = dt[:-1] + "+00:00"

    dt = dt.replace(".00+", "+").replace(".000+", "+").replace(".0+", "+")

    try:
        return datetime.fromisoformat(dt)
    except Exception:
        from dateutil import parser

        return parser.parse(dt)


def station_allowed(local_name: str, include: list[str] | None, exclude: list[str] | None) -> bool:
    name = local_name.lower()

    if include:
        allowed = [s.strip().lower() for s in include]
        return name in allowed

    if exclude:
        blocked = [s.strip().lower() for s in exclude]
        return name not in blocked

    return True


async def _async_fetch(hass: HomeAssistant, api_url: str, type_name: str) -> list[dict]:
    session = async_get_clientsession(hass)
    delay = 1
    while True:
        try:
            resp = await session.get(api_url, params={"type": type_name}, timeout=10)
            resp.raise_for_status()
            return await resp.json()
        except Exception as e:
            _LOGGER.error("ERROR FIWARE (%s): %s. Retrying in %ss...", type_name, e, delay)
            await hass.async_add_executor_job(__import__("time").sleep, delay)
            delay = min(delay * 2, 60)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the integration. Only legacy YAML support here; prefer UI config."""
    hass.data.setdefault(DOMAIN, {})
    # Do not read configuration.yaml by default; user should use integrations UI
    return True


async def async_setup_entry(hass: HomeAssistant, entry) -> bool:
    """Set up FIWARE from a config entry created in the UI."""
    api_url = entry.data.get("api_url")
    scan = entry.data.get("scan_interval", 60)
    include = entry.data.get("stations")
    exclude = entry.data.get("exclude")

    # Normalize include/exclude if comma-separated strings
    if isinstance(include, str) and include:
        include = [s.strip() for s in include.split(",") if s.strip()]
    else:
        include = None
    if isinstance(exclude, str) and exclude:
        exclude = [s.strip() for s in exclude.split(",") if s.strip()]
    else:
        exclude = None

    async def _update_data():
        air = await _async_fetch(hass, api_url, "AirQualityObserved")
        weather = await _async_fetch(hass, api_url, "WeatherObserved")

        def _process(list_entities: list[dict], kind: str) -> list[dict]:
            results: list[dict] = []
            name_counts: dict[str, int] = {}
            for entity in list_entities:
                local_name = entity.get("name", {}).get("value", "Unknown")
                if not local_name or local_name == "Unknown":
                    _LOGGER.warning("Entity missing name: %s", entity.get("id"))
                    continue

                if not station_allowed(local_name, include, exclude):
                    _LOGGER.debug("Station '%s' filtered.", local_name)
                    continue

                safe_local = normalize_station_name(local_name)
                count = name_counts.get(safe_local, 0) + 1
                name_counts[safe_local] = count
                entity_id = f"{safe_local}_{count}" if count > 1 else safe_local

                # Validate observation timestamp and ignore stale measurements >1 day
                date_obs_str = entity.get("dateObserved", {}).get("value")
                if date_obs_str:
                    try:
                        date_obs = parse_fiware_datetime(date_obs_str)
                        age = datetime.now(timezone.utc) - date_obs
                        if age > timedelta(days=1):
                            _LOGGER.info("%s ignored (stale observation): %s", kind, entity_id)
                            continue
                    except Exception as e:
                        _LOGGER.debug("Invalid date in %s: %s", kind, e)

                # Extract coordinates
                loc = entity.get("location", {}).get("value", {})
                coords = loc.get("coordinates") if isinstance(loc, dict) else None
                lat = lon = None
                if coords and isinstance(coords, (list, tuple)) and len(coords) >= 2:
                    lon, lat = coords[0], coords[1]

                # Compute AQI and main pollutant for air quality entities
                aqi = compute_aqi(entity) if kind == "airquality" else None
                main = compute_main_pollutant(entity) if kind == "airquality" else None

                results.append(
                    {
                        "entity_id": entity_id,
                        "raw_id": entity.get("id"),
                        "name": local_name,
                        "kind": kind,
                        "lat": lat,
                        "lon": lon,
                        "dateObserved": date_obs_str,
                        "data": entity,
                        "aqi": aqi,
                        "main_pollutant": main,
                    }
                )

            return results

        return {"airquality": _process(air, "airquality"), "weather": _process(weather, "weather")}

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"{DOMAIN}_{entry.entry_id}",
        update_interval=timedelta(seconds=scan),
        update_method=_update_data,
    )

    # Perform initial fetch
    await coordinator.async_refresh()

    hass.data[DOMAIN].setdefault(entry.entry_id, {})
    hass.data[DOMAIN][entry.entry_id]["coordinator"] = coordinator

    async def _create_zones_service(call) -> None:
        """Service handler to generate a YAML file with zones for all stations."""
        stations: dict[str, dict] = {}
        user_radius = None
        try:
            user_radius = int(call.data.get("radius", 0)) if call and call.data else None
            if user_radius == 0:
                user_radius = None
        except Exception:
            user_radius = None

        from decimal import Decimal, InvalidOperation

        def _compute_radius(lat_val, lon_val) -> int:
            """Estimate a sensible radius (meters) from coordinate precision."""
            try:
                lat_d = Decimal(str(lat_val)).normalize()
                lon_d = Decimal(str(lon_val)).normalize()
                # number of fractional digits equals -exponent for normalized Decimal
                lat_frac = -lat_d.as_tuple().exponent if lat_d.as_tuple().exponent < 0 else 0
                lon_frac = -lon_d.as_tuple().exponent if lon_d.as_tuple().exponent < 0 else 0
                precision = min(lat_frac, lon_frac)
            except (InvalidOperation, Exception):
                precision = 2

            # Map precision to radius (meters)
            if precision >= 5:
                return 50
            if precision == 4:
                return 100
            if precision == 3:
                return 250
            if precision == 2:
                return 1000
            if precision == 1:
                return 5000
            return 10000

        for kind in ("airquality", "weather"):
            for ent in coordinator.data.get(kind, []):
                eid = ent.get("entity_id")
                name = ent.get("name")
                lat = ent.get("lat")
                lon = ent.get("lon")
                if not lat or not lon:
                    continue
                # Use name as key to avoid duplicates
                if name in stations:
                    continue
                stations[name] = {"name": name, "latitude": lat, "longitude": lon}

        if not stations:
            _LOGGER.info("FIWARE: no stations with coordinates found to create zones")
            return

        zones = []
        for s in stations.values():
            lat = s["latitude"]
            lon = s["longitude"]
            radius = user_radius if user_radius is not None else _compute_radius(lat, lon)
            zones.append(
                {
                    "name": s["name"],
                    "latitude": float(lat),
                    "longitude": float(lon),
                    "radius": int(radius),
                    # use weather-related icon for meteorological stations
                    "icon": "mdi:weather-partly-cloudy",
                }
            )

        out_path = hass.config.path("fiware_zones.yaml")
        try:
            with open(out_path, "w", encoding="utf-8") as f:
                yaml.dump(zones, f, sort_keys=False, allow_unicode=True)
            _LOGGER.info("FIWARE: wrote %d zones to %s", len(zones), out_path)
        except Exception as e:
            _LOGGER.error("FIWARE: failed to write zones file: %s", e)
            return

        # Attempt to reload zones if the service exists
        try:
            await hass.services.async_call("zone", "reload", {})
            _LOGGER.info("FIWARE: requested zone.reload")
        except Exception:
            _LOGGER.debug("FIWARE: zone.reload service not available or failed; you may need to restart HA or reload zones manually")

    hass.services.async_register(DOMAIN, "create_zones", _create_zones_service)
    # Debug dump service removed

    # Pre-import platform module in executor to avoid blocking the event loop
    try:
        await hass.async_add_executor_job(importlib.import_module, f"custom_components.{DOMAIN}.sensor")
    except Exception:
        # ignore import errors here; loader will report later if needed
        pass

    # Forward setup to platforms (support multiple HA versions)
    try:
        await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    except AttributeError:
        # Older HA versions: fall back to discovery helper
        from homeassistant.helpers import discovery

        await discovery.async_load_platform(hass, "sensor", DOMAIN, {}, entry.data)

    return True


async def async_unload_entry(hass: HomeAssistant, entry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor"])
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
