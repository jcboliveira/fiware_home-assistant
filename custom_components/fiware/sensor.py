"""Sensor platform for FIWARE integration."""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.core import HomeAssistant

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)


FIELD_MAP_AIR = {
    "pm25": {"name": "PM2.5", "unit": "µg/m³"},
    "pm10": {"name": "PM10", "unit": "µg/m³"},
    "no2": {"name": "NO₂", "unit": "µg/m³"},
    "o3": {"name": "O₃", "unit": "µg/m³"},
    "co": {"name": "CO", "unit": "µg/m³"},
    "aqi": {"name": "AQI", "unit": None},
    "main_pollutant": {"name": "Main Pollutant", "unit": None},
}

FIELD_MAP_WEATHER = {
    "temperature": {"name": "Temperature", "unit": UnitOfTemperature.CELSIUS},
    "relativeHumidity": {"name": "Humidity", "unit": PERCENTAGE},
    "windSpeed": {"name": "Wind Speed", "unit": "km/h"},
    "precipitation": {"name": "Precipitation", "unit": "mm"},
    "uVIndexMax": {"name": "UV Index", "unit": None},
}


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback):
    """Set up sensors for a config entry using the coordinator."""
    coordinator = hass.data[DOMAIN].get(entry.entry_id, {}).get("coordinator")

    if not coordinator or not coordinator.data:
        _LOGGER.warning("No data available for FIWARE entry %s", entry.entry_id)

    entities: list[SensorEntity] = []

    # Create entities from coordinator data structure (airquality)
    for ent in coordinator.data.get("airquality", []):
        eid = ent.get("entity_id")
        name = ent.get("name")
        data = ent.get("data", {})
        # Add pollutant sensors
        for field, meta in FIELD_MAP_AIR.items():
            if field in data or field in ("aqi", "main_pollutant"):
                entities.append(FiwareSensor(coordinator, eid, name, field, meta, ent))

    # weather
    for ent in coordinator.data.get("weather", []):
        eid = ent.get("entity_id")
        name = ent.get("name")
        data = ent.get("data", {})
        for field, meta in FIELD_MAP_WEATHER.items():
            if field in data:
                entities.append(FiwareSensor(coordinator, eid, name, field, meta, ent))

    if entities:
        async_add_entities(entities, update_before_add=False)


class FiwareSensor(CoordinatorEntity, SensorEntity):
    """Representation of a single FIWARE sensor measurement."""

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
        self._attr_device_info = {
            "identifiers": {(f"fiware", entity_id)},
            "name": station_name,
            "manufacturer": "Porto Digital",
            "model": "FIWARE",
        }

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
    def extra_state_attributes(self):
        # expose coordinates and dateObserved
        return {
            "entity_id": self._entity_id,
            "raw_id": self._ent_wrap.get("raw_id"),
            "dateObserved": self._ent_wrap.get("dateObserved"),
            "latitude": self._ent_wrap.get("lat"),
            "longitude": self._ent_wrap.get("lon"),
        }

