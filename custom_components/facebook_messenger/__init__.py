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
from .webhook import async_setup_webhook, async_unload_webhook

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.BUTTON,
]


async def async_setup(hass: HomeAssistant, config) -> bool:
    """Initialize the webhook component."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["platform_config"] = config.get(DOMAIN, {})

    return True


# https://developers.home-assistant.io/docs/config_entries_index/#setting-up-an-entry
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up this integration using UI."""
    implementation = (
        await config_entry_oauth2_flow.async_get_config_entry_implementation(
            hass, entry
        )
    )

    token = entry.data["token"]
    client_session = aiohttp_client.async_get_clientsession(hass)

    facebook = Facebook(
        client_session=client_session,
        oauth_implementation=implementation,
        token=token,
    )

    coordinator = hass.data[DOMAIN][entry.entry_id] = FacebookDataUpdateCoordinator(
        hass, facebook
    )

    await coordinator.async_set_page_token()

    app_info = await coordinator.async_get_app_data()
    try:
        await async_setup_webhook(hass, app_info)
    except ValueError as exc:
        if str(exc) == "Handler is already defined!":
            _LOGGER.debug(
                "Webhook Handler was already defined. Likely have "
                "multiple pages using the same Facebook App "
                "(or we're fresh off a Config setup)."
            )
        else:
            raise exc

    await coordinator.async_config_entry_first_refresh()

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
    coordinator = hass.data[DOMAIN][entry.entry_id]
    app_info = await coordinator.async_get_app_data()
    async_unload_webhook(hass, app_info)

    if unloaded := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
