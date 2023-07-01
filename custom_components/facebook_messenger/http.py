"""Http view for the Facebook integration."""

import hashlib
import hmac
import logging

from aiohttp.web import Request, Response

from homeassistant.components.http.view import HomeAssistantView
from homeassistant.core import HomeAssistant

from .const import DOMAIN, WEBHOOK_URL
from .coordinator import FacebookDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def verify_request_signature(request, app_secret):
    """Verify the request signature by comparing it with the expected signature generated using the provided app secret."""
    signature = request.headers.get("x-hub-signature-256")

    if not signature:
        _LOGGER.warning("Couldn't find 'x-hub-signature-256' in headers.")
        return

    signature = signature.split("=")[1]
    payload = await request.read()
    expected_signature = hmac.new(
        app_secret.encode("utf-8"), payload, hashlib.sha256
    ).hexdigest()

    if signature != expected_signature:
        _LOGGER.warning("Failed to validate signature")
    else:
        _LOGGER.debug("Signature validated")


def find_coordinator_for_page(
    hass: HomeAssistant, page_id: str
) -> FacebookDataUpdateCoordinator | None:
    """Find the coordinator associated with a specific page ID in HomeAssistant data."""
    for config_entry in hass.data[DOMAIN]:
        coordinator: FacebookDataUpdateCoordinator = hass.data[DOMAIN][config_entry]

        if not isinstance(coordinator, FacebookDataUpdateCoordinator):
            continue

        if coordinator.page_id == page_id:
            return coordinator

    return None


class FacebookWebhookView(HomeAssistantView):
    """Handle OAuth finish callback requests."""

    requires_auth = False
    url = WEBHOOK_URL
    name = "api:facebook:webhook"

    async def get(self, request: Request) -> str:
        """Finish OAuth callback request."""
        hass: HomeAssistant = request.app["hass"]
        well_known_data = hass.data[DOMAIN][".well-known"]

        mode = request.query.get("hub.mode")
        token = request.query.get("hub.verify_token")
        challenge = request.query.get("hub.challenge")

        if not mode or not token:
            return Response(status=400)

        if mode == "subscribe" and token == well_known_data["verify_token"]:
            _LOGGER.info("WEBHOOK_VERIFIED")
            return Response(text=challenge, status=200)

        return Response(status=403)

    async def post(self, request: Request) -> str:
        """Finish OAuth callback request."""
        hass: HomeAssistant = request.app["hass"]
        # entry = hass.data[DOMAIN][entry_id]["entry"]
        # app_secret = hass.data[DOMAIN][entry_id]["app_secret"]

        data: dict = await request.json()

        verfied = False

        # await verify_request_signature(request, app_secret)

        _LOGGER.debug("Webhook Received.")
        _LOGGER.debug(data)

        object_type = data.get("object")

        for entry in data.get("entry", []):
            page_id = entry["id"]
            coordinator = find_coordinator_for_page(hass, page_id)

            if coordinator is None:
                continue

            if verfied is False:
                client_secret = (
                    coordinator.fb.oauth_session.implementation.client_secret
                )

                await verify_request_signature(request, client_secret)
                verfied = True

            if verfied is True:
                hass.async_create_task(
                    coordinator.handle_webhook_entry(object_type, entry)
                )

        return Response(status=200)
