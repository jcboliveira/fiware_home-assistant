"""Sensor platform for FIWARE integration."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass, SensorDeviceClass
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.core import HomeAssistant
from homeassistant.util.dt import parse_datetime, utcnow

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)


# English field maps
FIELD_MAP_AIR_EN = {
    "pm25": {
        "name": "PM2.5",
        "unit": "µg/m³",
        "device_class": "pm25",
        "icon": "mdi:air-filter",
        "state_class": True,
    },
    "pm10": {
        "name": "PM10",
        "unit": "µg/m³",
        "device_class": "pm10",
        "icon": "mdi:air-filter",
        "state_class": True,
    },
    "no2": {
        "name": "NO₂",
        "unit": "µg/m³",
        "device_class": "nitrogen_dioxide",
        "icon": "mdi:molecule",
        "state_class": True,
    },
    "o3": {
        "name": "O₃",
        "unit": "µg/m³",
        "device_class": "ozone",
        "icon": "mdi:weather-fog",
        "state_class": True,
    },
    "co": {
        "name": "CO",
        "unit": "µg/m³",
        "device_class": "carbon_monoxide",
        "icon": "mdi:molecule-co",
        "state_class": True,
    },
    "aqi": {
        "name": "AQI",
        "unit": None,
        "device_class": "aqi",
        "icon": "mdi:gauge",
        "state_class": True,
    },
    "main_pollutant": {
        "name": "Main Pollutant",
        "unit": None,
        "icon": "mdi:biohazard",
        "state_class": False,
    },
}

FIELD_MAP_WEATHER_EN = {
    "temperature": {
        "name": "Temperature",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": "temperature",
        "icon": "mdi:thermometer",
        "state_class": True,
    },
    "relativeHumidity": {
        "name": "Humidity",
        "unit": PERCENTAGE,
        "device_class": "humidity",
        "icon": "mdi:water-percent",
        "state_class": True,
    },
    "windSpeed": {
        "name": "Wind Speed",
        "unit": "km/h",
        "device_class": "wind_speed",
        "icon": "mdi:weather-windy",
        "state_class": True,
    },
    "precipitation": {
        "name": "Precipitation",
        "unit": "mm",
        "device_class": "precipitation",
        "icon": "mdi:weather-rainy",
        "state_class": True,
    },
    "uVIndexMax": {
        "name": "UV Index",
        "unit": None,
        "device_class": "uv_index",
        "icon": "mdi:weather-sunny-alert",
        "state_class": True,
    },
}

# Portuguese field maps
FIELD_MAP_AIR_PT = {
    "pm25": {
        "name": "PM2.5",
        "unit": "µg/m³",
        "device_class": "pm25",
        "icon": "mdi:air-filter",
        "state_class": True,
    },
    "pm10": {
        "name": "PM10",
        "unit": "µg/m³",
        "device_class": "pm10",
        "icon": "mdi:air-filter",
        "state_class": True,
    },
    "no2": {
        "name": "NO₂",
        "unit": "µg/m³",
        "device_class": "nitrogen_dioxide",
        "icon": "mdi:molecule",
        "state_class": True,
    },
    "o3": {
        "name": "O₃",
        "unit": "µg/m³",
        "device_class": "ozone",
        "icon": "mdi:weather-fog",
        "state_class": True,
    },
    "co": {
        "name": "CO",
        "unit": "µg/m³",
        "device_class": "carbon_monoxide",
        "icon": "mdi:molecule-co",
        "state_class": True,
    },
    "aqi": {
        "name": "AQI",
        "unit": None,
        "device_class": "aqi",
        "icon": "mdi:gauge",
        "state_class": True,
    },
    "main_pollutant": {
        "name": "Poluente Principal",
        "unit": None,
        "icon": "mdi:biohazard",
        "state_class": False,
    },
}

FIELD_MAP_WEATHER_PT = {
    "temperature": {
        "name": "Temperatura",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": "temperature",
        "icon": "mdi:thermometer",
        "state_class": True,
    },
    "relativeHumidity": {
        "name": "Humidade",
        "unit": PERCENTAGE,
        "device_class": "humidity",
        "icon": "mdi:water-percent",
        "state_class": True,
    },
    "windSpeed": {
        "name": "Velocidade do Vento",
        "unit": "km/h",
        "device_class": "wind_speed",
        "icon": "mdi:weather-windy",
        "state_class": True,
    },
    "precipitation": {
        "name": "Precipitação",
        "unit": "mm",
        "device_class": "precipitation",
        "icon": "mdi:weather-rainy",
        "state_class": True,
    },
    "uVIndexMax": {
        "name": "Índice UV",
        "unit": None,
        "device_class": "uv_index",
        "icon": "mdi:weather-sunny-alert",
        "state_class": True,
    },
}


def _get_field_maps(hass: HomeAssistant) -> tuple[dict, dict]:
    """Get the appropriate field maps based on Home Assistant language."""
    language = hass.config.language
    
    if language.startswith("pt"):
        return FIELD_MAP_AIR_PT, FIELD_MAP_WEATHER_PT
    else:
        return FIELD_MAP_AIR_EN, FIELD_MAP_WEATHER_EN


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback):
    """Set up sensors for a config entry using the coordinator."""
    coordinator = hass.data[DOMAIN].get(entry.entry_id, {}).get("coordinator")

    if not coordinator or not coordinator.data:
        _LOGGER.warning("No data available for FIWARE entry %s", entry.entry_id)

    # Get field maps based on Home Assistant language
    field_map_air, field_map_weather = _get_field_maps(hass)

    # Track known unique ids to avoid duplicates when new stations appear
    known_unique_ids: set[str] = set()

    async def _create_entities_from_data():
        """Create FiwareSensor entities for any stations/fields present in coordinator data but not yet created."""
        new_entities: list[SensorEntity] = []

        # airquality
        for ent in coordinator.data.get("airquality", []):
            eid = ent.get("entity_id")
            name = ent.get("name")
            data = ent.get("data", {})
            for field, meta in field_map_air.items():
                if field in data or field in ("aqi", "main_pollutant"):
                    unique_id = f"fiware_{eid}_{field}"
                    if unique_id in known_unique_ids:
                        continue
                    known_unique_ids.add(unique_id)
                    new_entities.append(FiwareSensor(coordinator, eid, name, field, meta, ent))
            # add an overview entity per station (single icon with list of measurements)
            overview_uid = f"fiware_{eid}_overview"
            if overview_uid not in known_unique_ids:
                known_unique_ids.add(overview_uid)
                new_entities.append(FiwareStationOverview(coordinator, eid, name, ent))

        # weather
        for ent in coordinator.data.get("weather", []):
            eid = ent.get("entity_id")
            name = ent.get("name")
            data = ent.get("data", {})
            for field, meta in field_map_weather.items():
                if field in data:
                    unique_id = f"fiware_{eid}_{field}"
                    if unique_id in known_unique_ids:
                        continue
                    known_unique_ids.add(unique_id)
                    new_entities.append(FiwareSensor(coordinator, eid, name, field, meta, ent))
            overview_uid = f"fiware_{eid}_overview"
            if overview_uid not in known_unique_ids:
                known_unique_ids.add(overview_uid)
                new_entities.append(FiwareStationOverview(coordinator, eid, name, ent))

        if new_entities:
            # Log created entities for audit
            try:
                created_info = [f"{ent.unique_id} ({ent.name})" for ent in new_entities]
            except Exception:
                created_info = [str(type(ent)) for ent in new_entities]
            _LOGGER.info("FIWARE: created %d new entities: %s", len(new_entities), ", ".join(created_info))
            async_add_entities(new_entities, update_before_add=False)

    # Initialize known ids and create entities for the first time
    await _create_entities_from_data()

    # Register a listener to create new entities when coordinator updates (new stations appear)
    def _on_coordinator_update() -> None:
        hass.async_create_task(_create_entities_from_data())

    coordinator.async_add_listener(_on_coordinator_update)


class FiwareSensor(CoordinatorEntity, SensorEntity):
    """Representation of a single FIWARE sensor measurement."""
    UNAVAILABLE_AFTER = timedelta(days=1)

    def __init__(self, coordinator, entity_id: str, station_name: str, field: str, meta: dict[str, Any], ent_wrap: dict):
        super().__init__(coordinator)
        self._entity_id = entity_id
        self._station_name = station_name
        self._field = field
        self._meta = meta
        self._ent_wrap = ent_wrap
        self._attr_name = f"{station_name} {meta.get('name')}"
        self._attr_unique_id = f"fiware_{entity_id}_{field}"
        self._attr_native_unit_of_measurement = meta.get("unit")
        self._attr_device_class = meta.get("device_class")
        self._attr_icon = meta.get("icon")
        self._attr_device_info = {
            "identifiers": {(f"fiware", entity_id)},
            "name": station_name,
            "manufacturer": "Porto Digital",
            "model": "FIWARE",
        }
        if meta.get("state_class"):
            self._attr_state_class = SensorStateClass.MEASUREMENT


class FiwareStationOverview(CoordinatorEntity, SensorEntity):
    """Overview sensor representing a station with aggregated attributes."""

    def __init__(self, coordinator, entity_id: str, station_name: str, ent_wrap: dict):
        super().__init__(coordinator)
        self._entity_id = entity_id
        self._station_name = station_name
        self._ent_wrap = ent_wrap
        self._attr_name = f"{station_name} Overview"
        self._attr_unique_id = f"fiware_{entity_id}_overview"
        self._attr_icon = "mdi:weather-station"
        self._attr_should_poll = False

    @property
    def native_value(self):
        # Use last_seen ISO or 'unknown'
        last = self._get_last_seen_iso()
        return last or "unknown"

    @property
    def latitude(self) -> float | None:
        try:
            return float(self._ent_wrap.get("lat")) if self._ent_wrap.get("lat") is not None else None
        except Exception:
            return None

    @property
    def longitude(self) -> float | None:
        try:
            return float(self._ent_wrap.get("lon")) if self._ent_wrap.get("lon") is not None else None
        except Exception:
            return None

    @property
    def extra_state_attributes(self):
        # expose a summary of measurements as attributes
        attrs: dict[str, Any] = {
            "entity_id": self._entity_id,
            "name": self._station_name,
            "last_seen": self._get_last_seen_iso(),
            "latitude": self._ent_wrap.get("lat"),
            "longitude": self._ent_wrap.get("lon"),
        }

        # add measurements from the coordinator's entry
        collections = self.coordinator.data.get(self._ent_wrap.get("kind"), [])
        for e in collections:
            if e.get("entity_id") == self._entity_id:
                data = e.get("data", {}) or {}
                # flatten simple measurements
                for k, v in data.items():
                    try:
                        # v may be a dict with 'value'
                        if isinstance(v, dict) and "value" in v:
                            attrs[k] = v.get("value")
                        else:
                            attrs[k] = v
                    except Exception:
                        continue
                # include computed aqi/main_pollutant
                if e.get("aqi") is not None:
                    attrs["aqi"] = e.get("aqi")
                if e.get("main_pollutant") is not None:
                    attrs["main_pollutant"] = e.get("main_pollutant")
                break

        return attrs

    def _get_last_seen_iso(self) -> str | None:
        # reuse FiwareSensor helper logic by inspecting ent_wrap data
        for key in ("dateObserved", "observedAt", "last_update", "timeObserved"):
            if self._ent_wrap.get(key):
                return self._ent_wrap.get(key)
        return None

    @property
    def native_value(self):
        # Data is kept in the wrapper stored at creation; coordinator keeps entire lists updated
        # Find the current entity in coordinator data
        collections = self.coordinator.data.get(self._ent_wrap.get("kind"), [])
        for e in collections:
            if e.get("entity_id") == self._entity_id:
                data = e.get("data", {})
                # Special computed fields
                if self._field == "aqi":
                    return e.get("aqi")
                if self._field == "main_pollutant":
                    return e.get("main_pollutant")

                if self._field in data:
                    val = data.get(self._field, {}).get("value")
                    if self._field == "windSpeed":
                        try:
                            return round(val * 3.6, 1)
                        except Exception:
                            return val
                    if self._field == "relativeHumidity":
                        try:
                            if val <= 1:
                                return round(val * 100, 1)
                        except Exception:
                            pass
                    return val

        return None

    @property
    def available(self) -> bool:
        """Determine availability based on last seen timestamp.

        If the last observed timestamp for this station is older than
        `UNAVAILABLE_AFTER`, consider the entity unavailable.
        """
        collections = self.coordinator.data.get(self._ent_wrap.get("kind"), [])
        for e in collections:
            if e.get("entity_id") == self._entity_id:
                # Try several possible timestamp locations/keys
                last_seen_iso = None
                for key in ("dateObserved", "observedAt", "last_update", "timeObserved"):
                    if e.get(key):
                        last_seen_iso = e.get(key)
                        break
                data = e.get("data", {}) or {}
                if not last_seen_iso:
                    for key in ("observedAt", "dateObserved", "last_update", "timeObserved"):
                        if data.get(key):
                            last_seen_iso = data.get(key)
                            break

                if last_seen_iso:
                    try:
                        last_seen = parse_datetime(last_seen_iso)
                    except Exception:
                        return self.coordinator.last_update_success
                    if last_seen is None:
                        return self.coordinator.last_update_success
                    # Ensure timezone-aware
                    if last_seen.tzinfo is None:
                        last_seen = last_seen.replace(tzinfo=timezone.utc)
                    return (utcnow() - last_seen) <= self.UNAVAILABLE_AFTER

                # If we have no timestamp, fallback to coordinator status
                return self.coordinator.last_update_success

        # If entity not found in coordinator data, mark unavailable
        return False

    @property
    def extra_state_attributes(self):
        # expose coordinates and dateObserved
        return {
            "entity_id": self._entity_id,
            "raw_id": self._ent_wrap.get("raw_id"),
            "dateObserved": self._ent_wrap.get("dateObserved"),
            "last_seen": self._get_last_seen_iso(),
            "latitude": self._ent_wrap.get("lat"),
            "longitude": self._ent_wrap.get("lon"),
        }

    def _get_last_seen_iso(self) -> str | None:
        """Return the ISO timestamp of the last seen measurement for this entity."""
        collections = self.coordinator.data.get(self._ent_wrap.get("kind"), [])
        for e in collections:
            if e.get("entity_id") == self._entity_id:
                last_seen_iso = None
                for key in ("dateObserved", "observedAt", "last_update", "timeObserved"):
                    if e.get(key):
                        last_seen_iso = e.get(key)
                        break
                data = e.get("data", {}) or {}
                if not last_seen_iso:
                    for key in ("observedAt", "dateObserved", "last_update", "timeObserved"):
                        if data.get(key):
                            last_seen_iso = data.get(key)
                            break
                return last_seen_iso
        return None

