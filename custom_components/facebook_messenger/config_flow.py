"""Config flow to configure the Facebook Messenger integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    CONN_CLASS_CLOUD_POLL,
    ConfigEntry,
)
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_entry_oauth2_flow, network
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)
from homeassistant.util import uuid as uuid_util

from . import FacebookWebhookView
from .api import Facebook
from .const import DOMAIN, WEBHOOK_URL

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
        self.fb = Facebook(
            async_get_clientsession(self.hass),
            user_token=self._data["token"]["access_token"],
        )

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

            self._data["page_id"] = page["id"]
            self._data["page_name"] = page["name"]
            self._data["page_token"] = page["access_token"]
            return await self.async_step_webhook_info()

        pages = await self.fb.user().list_pages()
        page_data = self._data["page_data"] = pages.get("data", [])

        # if len(page_data) == 1:
        #     page = page_data[0]
        #     self._data["page_id"] = page["id"]
        #     self._data["page_name"] = page["name"]
        #     self._data["page_token"] = page["access_token"]
        #     return await self.async_step_webhook_info()

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

        self.hass.data.setdefault(DOMAIN, {})
        self.hass.data[DOMAIN].setdefault(".well-known", {})
        if (
            verify_token := self.hass.data[DOMAIN][".well-known"].get("verify_token")
        ) is None:
            verify_token = uuid_util.random_uuid_hex()
            self.hass.data[DOMAIN][".well-known"]["verify_token"] = verify_token

        self._data["verify_token"] = verify_token
        _LOGGER.debug(f"Generated verify_token: {verify_token}")

        self.hass.http.register_view(FacebookWebhookView)
        _LOGGER.debug(f"Registered Webhook view")

        try:
            external_url = network.get_url(
                self.hass,
                allow_internal=False,
                allow_ip=False,
                require_ssl=True,
                require_standard_port=False,
            )
        except network.NoURLAvailableError:
            return self.async_abort(reason="no_external_url")

        webhook_url = f"{external_url}{WEBHOOK_URL}"

        _LOGGER.debug(f"setting up Webhook URL: {webhook_url}")

        app_token = f"{self.flow_impl.client_id}|{self.flow_impl.client_secret}"
        app_id = self.flow_impl.client_id

        # set app App level Webhook
        resp = await self.fb.app(app_token).setup_subscription(
            app_id, webhook_url, verify_token
        )
        _LOGGER.info(resp)

        page_token = self._data["page_token"]

        resp = await self.fb.page(page_token).setup_page_subscription(
            self._data["page_id"]
        )
        _LOGGER.info(resp)

        await self.async_set_unique_id(self._data["page_id"])
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=self._data["page_name"],
            data=self._data,
        )
