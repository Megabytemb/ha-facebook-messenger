"""DataUpdateCoordinator for the Facebook Messenger integration."""
from datetime import timedelta
import logging
import random
import secrets

from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_WEBHOOK_ID
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
)

from .api import Facebook
from .const import (
    CONF_APP_NAME,
    CONF_WEBOOK_VERIFY_TOKEN,
    DOMAIN,
    STORAGE_KEY,
    STORAGE_VERSION,
)

_LOGGER = logging.getLogger(__name__)


def generate_code():
    """Generate a random code consisting of three digits followed by a hyphen and another three digits."""
    code = ""
    for _ in range(3):
        code += str(random.randint(0, 9))
    code += "-"
    for _ in range(3):
        code += str(random.randint(0, 9))
    return code


class FacebookDataUpdateCoordinator(DataUpdateCoordinator):
    """Facebook Data coordinator."""

    config_entry: ConfigEntry

    def __init__(self, hass, fb_api: Facebook):
        """Initialize Facebook Data coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=5),
        )
        self.fb: Facebook = fb_api
        self._store = Store(hass, STORAGE_VERSION, f"{STORAGE_KEY}")
        self.saved_data: dict = None
        self.page_id = None

        if self.config_entry is not None:
            self.page_id = self.config_entry.data["page_id"]

        self.pending_codes = []

        self._app_name = None

    async def async_set_page_token(self):
        """Get a new page access token for our page."""
        if self.page_id is not None:
            page_token = await self.get_page_token()
            self.fb.set_page_token(page_token)

    async def async_get_app_data(self):
        """Get App Data from Storage for fb app."""
        await self.async_load()

        self.saved_data.setdefault("apps", {})
        app_data = self.saved_data["apps"].get(self.fb.client_id, {})

        changed = False

        if app_data.get(CONF_WEBHOOK_ID) is None:
            webhook_id = app_data[CONF_WEBHOOK_ID] = secrets.token_hex(32)
            _LOGGER.debug("Generated webhook_id: %s", webhook_id)
            changed = True

        if app_data.get(CONF_WEBOOK_VERIFY_TOKEN) is None:
            verify_token = app_data[CONF_WEBOOK_VERIFY_TOKEN] = secrets.token_hex(32)
            _LOGGER.debug("Generated verify_token: %s", verify_token)
            changed = True

        if self._app_name is None:
            fb_app_data = await self.fb.app().get_app_info(self.fb.client_id)
            app_data[CONF_APP_NAME] = self._app_name = app_name = fb_app_data["name"]
            _LOGGER.debug("Got facebook app name: %s", app_name)
            changed = True

        if changed is True:
            self.saved_data["apps"][self.fb.client_id] = app_data
            await self._async_save()

        return app_data

    async def get_page_token(self):
        """Retrieve the access token for the Facebook page associated with the provided page ID."""
        pages = await self.fb.user().list_pages()
        page_data = pages.get("data", [])

        for page in page_data:
            if page["id"] == self.page_id:
                return page["access_token"]

        raise ValueError("Page Token unable to be obtained.")

    async def async_load(self) -> None:
        """Load config."""
        if self.saved_data is None:
            if stored := await self._store.async_load():
                self.saved_data = stored

        # If still None, initialise it.
        if self.saved_data is None:
            self.saved_data = {}

    async def _async_save(self) -> None:
        """Save config."""
        await self._store.async_save(self.saved_data)

    async def _async_update_data(self):
        """Fetch data from API endpoint."""
        data = await self.fb.page().get_page(self.page_id)
        return data

    async def handle_webhook_entry(self, object: str, entry: dict):
        """Handle a webhook entry by processing the messaging data and performing actions based on the received messages."""
        _LOGGER.info(entry["messaging"])

        for message in entry["messaging"]:
            text_message = message["message"]["text"]
            if text_message in self.pending_codes:
                psid = message["sender"]["id"]
                page_name = self.data.get("name")

                msg = f"The Facebook PSID for code {text_message} on page {page_name} is: {psid}"

                _LOGGER.info(msg)

                persistent_notification.async_create(
                    self.hass,
                    msg,
                    "Match Facebook ID",
                )

                persistent_notification.async_dismiss(
                    self.hass, notification_id=f"{DOMAIN}_{text_message}"
                )

                self.pending_codes.remove(text_message)

    async def display_matching_id(self):
        """Generate a matching code, add it to the list of pending codes, and display a persistent notification with instructions for matching the Facebook ID."""
        matching_code = generate_code()

        self.pending_codes.append(matching_code)
        page_url = self.data.get("link")
        page_name = self.data.get("name")

        persistent_notification.async_create(
            self.hass,
            (
                f"To match the Facebook ID, navigate to the Facebook page '{page_name}' at {page_url} and message it this code: {matching_code}"
            ),
            "Match Facebook ID",
            notification_id=f"{DOMAIN}_{matching_code}",
        )
