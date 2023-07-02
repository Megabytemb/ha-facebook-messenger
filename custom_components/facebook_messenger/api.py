"""Facebook API Module."""
import hashlib
import hmac
import time

import aiohttp

from homeassistant.helpers.config_entry_oauth2_flow import (
    AbstractOAuth2Implementation,
)

BASE_API = "https://graph.facebook.com/v17.0"


def generate_appsecret_proof(app_secret, access_token):
    """Generate a HMAC SHA-256 hash of the access token using the app secret.

    Generate a HMAC SHA-256 hash of the access token using the app secret as the key,
    and return it along with the current timestamp.
    """

    # Get the current timestamp as an integer
    timestamp = int(time.time())

    # oddly, sometimes we seem to be ahead of facebook? so we'll knock a couple seconds off
    timestamp = timestamp - 5

    # Prepare the message to be hashed
    message = access_token + "|" + str(timestamp)

    # Create a new HMAC object with the app_secret as the key and SHA-256 as the digest algorithm
    h = hmac.new(
        bytes(app_secret, "utf-8"),
        msg=bytes(message, "utf-8"),
        digestmod=hashlib.sha256,
    )

    # Return the hexadecimal digest of the HMAC object
    return h.hexdigest(), timestamp


class Facebook:
    """Facebook API Class."""

    def __init__(
        self,
        client_session: aiohttp.ClientSession,
        oauth_implementation: AbstractOAuth2Implementation,
        token: dict,
    ) -> None:
        """Init Facebook API."""
        self.oauth_implementation = oauth_implementation
        self.client_session = client_session
        self._token = token
        self._access_token = None
        self._page_token = None
        self._last_access_token_type = None

        self._user_token = self._token["access_token"]

    def _reset_token(self):
        """Reset access token after each use."""
        self._access_token = None

    @property
    def client_id(self) -> str:
        """Shortut to app client ID."""
        return self.oauth_implementation.client_id

    @property
    def client_secret(self) -> str:
        """Shortut to app client secret."""
        return self.oauth_implementation.client_secret

    def user(self, token: str = None):
        """Set the User Token."""
        if token is None:
            token = self._user_token

        self._access_token = token
        self._last_access_token_type = "user"
        return self

    def app(self, token: str = None):
        """Set the App Token."""
        if token is None:
            token = f"{self.client_id}|{self.client_secret}"

        self._access_token = token
        self._last_access_token_type = "app"
        return self

    def page(self, token: str = None):
        """Set the Page Token."""
        if token is None:
            token = self._page_token

        if token is None:
            raise ValueError("Page token not supplied, nor set via set_page_token")

        self._access_token = token
        self._last_access_token_type = "page"
        return self

    async def _get(self, url, *, params=None, **kwargs):
        """Perform a GET request to the specified url with optional parameters."""
        access_token = await self.get_access_token()

        if params is None:
            params = {}
        params["access_token"] = access_token

        appsecret_proof, appsecret_time = await self.async_get_app_secret_proof()
        params["appsecret_proof"] = appsecret_proof
        params["appsecret_time"] = appsecret_time

        resp = await self.client_session.get(url, params=params, **kwargs)
        resp.raise_for_status()

        self._reset_token()

        return resp

    async def _post(self, url, *, data=None, json=None, params=None, **kwargs):
        """Perform a POST request to the specified url with optional payload and parameters."""
        access_token = await self.get_access_token()

        if params is None:
            params = {}
        params["access_token"] = access_token

        appsecret_proof, appsecret_time = await self.async_get_app_secret_proof()
        params["appsecret_proof"] = appsecret_proof
        params["appsecret_time"] = appsecret_time

        resp = await self.client_session.post(
            url, data=data, json=json, params=params, **kwargs
        )
        resp.raise_for_status()

        self._reset_token()

        return resp

    async def async_get_app_secret_proof(self) -> tuple[str, str]:
        """Retrieve the access token and generate its HMAC SHA-256 hash using the app secret.

        This method retrieves the current access token, generates a HMAC SHA-256 hash
        of the access token using the app secret as the key, and returns it along
        with the current timestamp.
        """
        access_token = await self.get_access_token()
        appsecret_proof, timestamp = generate_appsecret_proof(
            self.client_secret, access_token
        )

        return appsecret_proof, timestamp

    def set_page_token(self, page_token):
        """Set the value of the page token."""
        self._page_token = page_token

    async def get_access_token(self):
        """Get the currently set access token."""
        if self._access_token is None:
            raise ValueError(
                "Access token not set. Use the 'user()', 'app()', or 'page()' methods to set the access token."
            )
        return self._access_token

    async def list_pages(self):
        """Retrieve a list of pages associated with the user's account."""
        url = BASE_API + "/me/accounts"
        resp = await self._get(url)

        return await resp.json()

    async def get_page(self, page_id: str):
        """Retrieve a list of pages associated with the user's account."""
        url = BASE_API + f"/{page_id}"
        params = {"fields": "link,name,id,app_id,followers_count"}

        resp = await self._get(url, params=params)

        return await resp.json()

    async def get_app_info(self, app_id: str):
        """Get information about a Facebook app.."""
        url = BASE_API + f"/{app_id}"
        params = {"fields": "link,name,id,photo_url,weekly_active_users"}

        resp = await self._get(url, params=params)

        return await resp.json()

    async def setup_page_subscription(self, page_id: str):
        """Set up a subscription to receive messages from a specific Facebook page."""
        url = BASE_API + f"/{page_id}/subscribed_apps"

        params = {"subscribed_fields": "messages"}
        resp = await self._post(url, params=params)

        return await resp.json()

    async def send_message(self, page_id: str, recipient: str, body_message: any):
        """Set up a subscription to receive messages from a specific Facebook page."""
        url = BASE_API + f"/{page_id}/messages"

        body = {
            "recipient": recipient,
            "message": body_message,
            "messaging_type": "MESSAGE_TAG",
            "tag": "ACCOUNT_UPDATE",
        }

        resp = await self._post(url, json=body)

        return await resp.json()

    async def setup_subscription(
        self, app_id: str, callback_url: str, verify_token: str
    ):
        """Set up a subscription to receive messages from the specified app with a callback url and verification token."""
        url = BASE_API + f"/{app_id}/subscriptions"

        body = {
            "object": "page",
            "callback_url": callback_url,
            "fields": ["messages"],
            "include_values": True,
            "verify_token": verify_token,
        }

        resp = await self._post(url, json=body)

        return await resp.json()

    async def get_ids_for_apps(self, user_psid: str):
        """Get User ASID for a given page.

        Given a user ID for a bot in Messenger, retrieve the IDs for apps owned by the same business
        """

        url = BASE_API + f"/{user_psid}/ids_for_apps"

        resp = await self._get(url)

        return await resp.json()

    async def get_ids_for_pages(self, user_asid: str, page_id: str = None):
        """Get User PSID for a given page.

        Given a user ID for an app, retrieve the IDs for bots in Messenger owned by the same business
        """
        url = BASE_API + f"/{user_asid}/ids_for_pages"

        params = {}
        if page_id:
            params["page"] = page_id

        resp = await self._get(url, params=params)

        return await resp.json()
