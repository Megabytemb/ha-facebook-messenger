"""Facebook Messenger platform for notify component."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.notify import (
    ATTR_DATA,
    ATTR_TARGET,
    BaseNotificationService,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import ATTR_TEXT, DOMAIN
from .coordinator import FacebookDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_get_service(
    hass: HomeAssistant,
    config: ConfigType,
    discovery_info: DiscoveryInfoType | None = None,
) -> FacebookNotificationService | None:
    """Get the Pushover notification service."""
    if discovery_info is None:
        return None

    coordinator: FacebookDataUpdateCoordinator = hass.data[DOMAIN][
        discovery_info["entry_id"]
    ]
    return FacebookNotificationService(hass, coordinator)


class FacebookNotificationService(BaseNotificationService):
    """Implement the notification service for Pushover."""

    def __init__(
        self, hass: HomeAssistant, coordinator: FacebookDataUpdateCoordinator
    ) -> None:
        """Initialize the service."""
        self._hass = hass
        self.coordinator = coordinator

    async def async_send_message(self, message: str = "", **kwargs: Any) -> None:
        """Send a message via Facebook Messenger."""
        body = {ATTR_TEXT: message}
        targets = kwargs.get(ATTR_TARGET)

        if data := kwargs.get(ATTR_DATA):
            body.update(data)

        page_id = self.coordinator.page_id

        for target in targets:
            recipient = {"id": target}
            await self.coordinator.fb.page().send_message(page_id, recipient, body)
