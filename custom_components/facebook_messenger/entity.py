"""BlueprintEntity class."""
from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN, INTEGRATION_VERSION, NAME
from .coordinator import FacebookDataUpdateCoordinator


class FacebookEntity(CoordinatorEntity):
    """BlueprintEntity class."""

    _attr_attribution = ATTRIBUTION
    key: str

    def __init__(
        self, hass: HomeAssistant, coordinator: FacebookDataUpdateCoordinator
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self.type = None
        self.hass = hass

    @property
    def unique_id(self) -> str | None:
        """Generate Unique ID."""
        return f"{self.coordinator.config_entry.entry_id}_{self.key}"

    @property
    def device_info(self) -> DeviceInfo | None:
        """Return common device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.unique_id)},
            name=NAME,
            model=INTEGRATION_VERSION,
            manufacturer=NAME,
            entry_type=DeviceEntryType.SERVICE,
        )
