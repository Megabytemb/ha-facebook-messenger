"""Facebok Messenger Button module."""
from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import FacebookDataUpdateCoordinator
from .entity import FacebookEntity


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """Set up the Tesla selects by config_entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = [FacebookMatchASID(hass, coordinator)]

    async_add_entities(entities, update_before_add=True)


class FacebookMatchASID(FacebookEntity, ButtonEntity):
    """Start the flow of identifying the Facebook ASID."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: FacebookDataUpdateCoordinator,
    ) -> None:
        """Initialize horn entity."""
        super().__init__(hass, coordinator)
        self.key = "matchASID"
        self._attr_icon = "mdi:bullhorn"
        self._attr_name = "Link Facebook Account"

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.coordinator.display_matching_id()
