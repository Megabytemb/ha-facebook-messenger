"""Custom integration to integrate facebook_messenger with Home Assistant.

For more details about this integration, please refer to
https://github.com/Megabytemb/ha-facebook-messenger
"""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import aiohttp_client, config_entry_oauth2_flow, discovery

from .api import Facebook
from .const import DOMAIN
from .coordinator import FacebookDataUpdateCoordinator
from .http import FacebookWebhookView

logger = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.BUTTON,
]


async def async_setup(hass: HomeAssistant, config) -> bool:
    """Initialize the webhook component."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(".well-known", {})
    hass.data[DOMAIN]["platform_config"] = config.get(DOMAIN, {})

    hass.http.register_view(FacebookWebhookView)
    return True


# https://developers.home-assistant.io/docs/config_entries_index/#setting-up-an-entry
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up this integration using UI."""

    hass.data[DOMAIN][".well-known"]["verify_token"] = entry.data["verify_token"]

    implementation = (
        await config_entry_oauth2_flow.async_get_config_entry_implementation(
            hass, entry
        )
    )

    oauth_session = config_entry_oauth2_flow.OAuth2Session(hass, entry, implementation)
    client_session = aiohttp_client.async_get_clientsession(hass)
    page_token = entry.data["page_token"]

    facebook = Facebook(
        oauth_session=oauth_session,
        client_session=client_session,
        page_token=page_token,
    )

    coordinator = FacebookDataUpdateCoordinator(hass, facebook)

    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    hass.async_create_task(
        discovery.async_load_platform(
            hass,
            Platform.NOTIFY,
            DOMAIN,
            {
                "entry_id": entry.entry_id,
                CONF_NAME: f"{DOMAIN}_{entry.data['page_name']}",
            },
            hass.data[DOMAIN]["platform_config"],
        )
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
    if unloaded := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
