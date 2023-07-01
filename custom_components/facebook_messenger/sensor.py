"""Sensor platform for facebook_messenger."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, NAME
from .scheduler import Scheduler

ENTITY_DESCRIPTIONS = (
    SensorEntityDescription(
        key="actionsCount",
        name="Actions count",
        icon="mdi:format-quote-close",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_devices: AddEntitiesCallback
):
    """Set up the sensor platform."""
    scheduler = hass.data[DOMAIN]["scheduler"]

    async_add_devices(
        ActionsCountSensor(
            config_entry=entry,
            entity_description=entity_description,
            scheduler=scheduler,
        )
        for entity_description in ENTITY_DESCRIPTIONS
    )


class ActionsCountSensor(SensorEntity):
    """facebook_messenger Sensor class."""

    def __init__(
        self,
        config_entry: ConfigEntry,
        entity_description: SensorEntityDescription,
        scheduler: Scheduler,
    ) -> None:
        """Initialize the sensor class."""
        self.entity_description = entity_description
        self._config_entry = config_entry
        self._name = NAME
        self._attr_unique_id = f"{config_entry.entry_id}-sensor"
        self._scheduler: Scheduler = scheduler

    @property
    def native_value(self) -> str:
        """Return the native value of the sensor."""
        return len(self._scheduler.scheduled_actions)
