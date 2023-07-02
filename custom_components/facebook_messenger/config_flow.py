"""Config flow to configure the Facebook Messenger integration."""
from __future__ import annotations

import logging
from typing import Any

from aiohttp import ClientResponseError
import voluptuous as vol

from homeassistant.config_entries import (
    CONN_CLASS_CLOUD_POLL,
    ConfigEntry,
)
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .api import Facebook
from .const import (
    CONF_WEBOOK_VERIFY_TOKEN,
    DOMAIN,
)
from .coordinator import FacebookDataUpdateCoordinator
from .webhook import async_setup_webhook

_LOGGER = logging.getLogger(__name__)


class FacebookMessengerConfigFlow(
    config_entry_oauth2_flow.AbstractOAuth2FlowHandler, domain=DOMAIN
):
    """Config flow for Facebook Messenger."""

    VERSION = 1
    DOMAIN = DOMAIN
    CONNECTION_CLASS = CONN_CLASS_CLOUD_POLL
    reauth_entry: ConfigEntry | None = None

    @property
    def logger(self):
        """Return logger."""
        return _LOGGER

    async def async_oauth_create_entry(
        self, data: dict[str, Any] | None = None
    ) -> FlowResult:
        """Complete OAuth setup and finish pubsub or finish."""

        if self.reauth_entry:
            self.hass.config_entries.async_update_entry(
                self.reauth_entry, data={**self.reauth_entry.data, **data}
            )
            await self.hass.config_entries.async_reload(self.reauth_entry.entry_id)
            return self.async_abort(reason="reauth_successful")

        self._data = data

        implementation = self.flow_impl
        client_session = async_get_clientsession(self.hass)

        fb = Facebook(
            client_session=client_session,
            oauth_implementation=implementation,
            token=self._data["token"],
        )

        self.coordinator = FacebookDataUpdateCoordinator(self.hass, fb)

        return await self.async_step_select_page()

    async def async_step_reauth(self, user_input=None):
        """Perform reauth upon an API authentication error."""
        self.reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        """Dialog that informs the user that reauth is required."""
        if user_input is None:
            return self.async_show_form(
                step_id="reauth_confirm",
                data_schema=vol.Schema({}),
            )
        return await self.async_step_user()

    async def async_step_select_page(self, user_input=None):
        """Get Calendar ID from User."""
        _LOGGER.debug("fn:async_step_select_page")
        if user_input is not None:
            page_index = user_input["page_index"]
            _LOGGER.debug(f"Facebook Index: {page_index}")
            page = self._data["page_data"][int(page_index)]

            await self.async_set_unique_id(page["id"])
            self._abort_if_unique_id_configured()

            self._data["page_id"] = page["id"]
            self._data["page_name"] = page["name"]
            self._data["page_token"] = page["access_token"]
            return await self.async_step_webhook_info()

        pages = await self.coordinator.fb.user().list_pages()
        page_data = self._data["page_data"] = pages.get("data", [])

        select_options = []

        for index, page in enumerate(page_data):
            select_options.append(
                SelectOptionDict(value=str(index), label=page["name"])
            )

        return self.async_show_form(
            step_id="select_page",
            data_schema=vol.Schema(
                {
                    vol.Required("page_index"): SelectSelector(
                        SelectSelectorConfig(
                            options=select_options, mode=SelectSelectorMode.DROPDOWN
                        )
                    ),
                }
            ),
        )

    async def async_step_webhook_info(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle discovery confirmation."""
        _LOGGER.debug("fn:async_step_webhook_info")

        app_info = await self.coordinator.async_get_app_data()
        webhook_url, created_cloudhook = await async_setup_webhook(self.hass, app_info)
        app_id = self.coordinator.fb.client_id

        if created_cloudhook is True:
            await self.coordinator.save_cloud_webhook_url(webhook_url)

        _LOGGER.debug(f"setting up Webhook URL: {webhook_url}")
        try:
            resp = await self.coordinator.fb.app().setup_subscription(
                app_id, webhook_url, app_info[CONF_WEBOOK_VERIFY_TOKEN]
            )
            _LOGGER.info(resp)
        except ClientResponseError as exc:
            _LOGGER.critical("Failed to setup Webhook: %s", str(exc))
            await self.async_abort(reason="webhook_setup_failed")

        self.coordinator.fb.set_page_token(self._data["page_token"])

        try:
            resp = await self.coordinator.fb.page().setup_page_subscription(
                self._data["page_id"]
            )
            _LOGGER.info(resp)
        except ClientResponseError as exc:
            _LOGGER.critical("Failed to subscribe Page to Webhook: %s", str(exc))
            await self.async_abort(reason="webhook_page_setup_failed")

        return self.async_create_entry(
            title=self._data["page_name"],
            data=self._data,
        )
