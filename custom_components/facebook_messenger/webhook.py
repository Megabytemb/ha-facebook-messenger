"""Webhook Module."""
import hashlib
import hmac
import logging

from aiohttp.web import Request, Response

from homeassistant.components import cloud, webhook
from homeassistant.const import CONF_WEBHOOK_ID
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.network import NoURLAvailableError, get_url

from .const import CONF_APP_NAME, CONF_WEBOOK_VERIFY_TOKEN, DOMAIN
from .coordinator import FacebookDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


@callback
async def async_get_webhook_url(hass: HomeAssistant, webhook_id: str):
    """Retrieve the URL for a webhook.

    Args:
        hass: Home Assistant instance.
        webhook_id: Identifier for the webhook.

    Returns:
        str: URL of the webhook.

    Raises:
        ValueError: If an externally available Webhook URL cannot be determined.
    """

    try:
        webhook_url = await cloud.async_create_cloudhook(hass, webhook_id)
        return webhook_url
    except (cloud.CloudNotConnected, cloud.CloudNotAvailable) as exc:
        _LOGGER.info("Cloud Hooks not available: %s", str(exc))

    webhook_path = webhook.async_generate_path(webhook_id)
    try:
        hass_url = get_url(
            hass,
            allow_cloud=False,
            allow_external=True,
            allow_ip=False,
            require_ssl=True,
            prefer_external=True,
        )
    except NoURLAvailableError as exc:
        raise ValueError(
            "Cannot determine an externally available Webhook URL."
        ) from exc

    webhook_url = f"{hass_url}{webhook_path}"

    return webhook_url


def async_unload_webhook(hass: HomeAssistant, app_info: dict):
    """Unload webhook based entry."""
    webhook.async_unregister(hass, app_info[CONF_WEBHOOK_ID])


@callback
async def async_setup_webhook(hass: HomeAssistant, app_info: dict) -> str:
    """Initialize a webhook based on the configuration entry.

    Args:
        hass: Home Assistant instance.
        app_info: app_info dict from coordinator.

    Returns:
        str: URL of the registered webhook.
    """

    webhook_url = await async_get_webhook_url(hass, app_info[CONF_WEBHOOK_ID])

    webhook_handler = WebhookHandler(verify_token=app_info[CONF_WEBOOK_VERIFY_TOKEN])

    webhook.async_register(
        hass,
        DOMAIN,
        app_info[CONF_APP_NAME],
        app_info[CONF_WEBHOOK_ID],
        webhook_handler,
        allowed_methods=["GET", "POST"],
        local_only=False,
    )

    return webhook_url


class WebhookHandler:
    """Handles incoming webhooks."""

    def __init__(self, *, verify_token: str = None):
        """Initialize the webhook handler."""
        self.verify_token = verify_token

    async def __call__(self, hass: HomeAssistant, webhook_id: str, request: Request):
        """Handle incoming webhooks."""
        _LOGGER.debug("Received Facebook Messenger webhook")

        if request.method.upper() == "GET":
            return await self.handle_get(hass, request)
        elif request.method.upper() == "POST":
            return await self.handle_post(hass, request)
        else:
            return Response(status=403)

    async def handle_get(self, hass: HomeAssistant, request: Request) -> Response:
        """Handle GET request."""
        mode = request.query.get("hub.mode")
        token = request.query.get("hub.verify_token")
        challenge = request.query.get("hub.challenge")

        if not mode or not token:
            return Response(status=400)

        if mode == "subscribe" and token == self.verify_token:
            _LOGGER.info("WEBHOOK_VERIFIED")
            return Response(text=challenge, status=200)

        return Response(status=403)

    async def handle_post(self, hass: HomeAssistant, request: Request) -> Response:
        """Handle POST request."""

        data: dict = await request.json()
        _LOGGER.debug(data)

        verfied = False

        object_type = data.get("object")

        for entry in data.get("entry", []):
            page_id = entry["id"]
            coordinator = find_coordinator_for_page(hass, page_id)

            if coordinator is None:
                continue

            if verfied is False:
                client_secret = coordinator.fb.client_secret

                await verify_request_signature(request, client_secret)
                verfied = True

            if verfied is True:
                hass.async_create_task(
                    coordinator.handle_webhook_entry(object_type, entry)
                )
            else:
                return Response(status=401)

        return Response(status=200)


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
