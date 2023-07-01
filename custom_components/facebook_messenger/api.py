"""Facebook API Module."""
import aiohttp

from homeassistant.helpers.config_entry_oauth2_flow import OAuth2Session

BASE_API = "https://graph.facebook.com/v17.0"


class Facebook:
    """Facebook API Class."""

    def __init__(
        self,
        client_session: aiohttp.ClientSession,
        oauth_session: OAuth2Session = None,
        page_token: str = None,
        user_token: str = None,
    ) -> None:
        """Init Facebook API."""
        self.oauth_session = oauth_session
        self.client_session = client_session
        self._access_token = None
        self._page_token = page_token
        self._user_token = user_token

        if self._user_token is None and oauth_session is not None:
            self._user_token = self.oauth_session.token["access_token"]

    def _reset_token(self):
        """Reset access token after each use."""
        self._access_token = None

    def user(self, token: str = None):
        """Set the User Token."""
        if token is None:
            token = self._user_token

        self._access_token = token
        return self

    def app(self, token: str = None):
        """Set the App Token."""
        if token is None:
            client_id = self.oauth_session.implementation.client_id
            client_secret = self.oauth_session.implementation.client_secret
            token = f"{client_id}|{client_secret}"

        self._access_token = token
        return self

    def page(self, token: str = None):
        """Set the Page Token."""
        if token is None:
            token = self._page_token

        if token is None:
            raise ValueError("Page token not supplied, nor set via set_page_token")

        self._access_token = token
        return self

    async def _get(self, url, *, params=None, **kwargs):
        """Perform a GET request to the specified URL with optional parameters."""
        access_token = await self.get_access_token()

        if params is None:
            params = {}
        params["access_token"] = access_token

        resp = await self.client_session.get(url, params=params, **kwargs)
        resp.raise_for_status()

        self._reset_token()

        return resp

    async def _post(self, url, *, data=None, json=None, params=None, **kwargs):
        """Perform a POST request to the specified URL with optional payload and parameters."""
        access_token = await self.get_access_token()

        if params is None:
            params = {}
        params["access_token"] = access_token

        resp = await self.client_session.post(
            url, data=data, json=json, params=params, **kwargs
        )
        resp.raise_for_status()

        self._reset_token()

        return resp

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
        URL = BASE_API + "/me/accounts"
        resp = await self._get(URL)

        return await resp.json()

    async def get_page(self, page_id: str):
        """Retrieve a list of pages associated with the user's account."""
        URL = BASE_API + f"/{page_id}"
        params = {"fields": "link,name,id,app_id,followers_count"}

        resp = await self._get(URL, params=params)

        return await resp.json()

    async def setup_page_subscription(self, page_id: str):
        """Set up a subscription to receive messages from a specific Facebook page."""
        URL = BASE_API + f"/{page_id}/subscribed_apps"

        params = {"subscribed_fields": "messages"}
        resp = await self._post(URL, params=params)

        return await resp.json()

    async def send_message(self, page_id: str, recipient: str, body_message: any):
        """Set up a subscription to receive messages from a specific Facebook page."""
        URL = BASE_API + f"/{page_id}/messages"

        body = {
            "recipient": recipient,
            "message": body_message,
            "messaging_type": "MESSAGE_TAG",
            "tag": "ACCOUNT_UPDATE",
        }

        resp = await self._post(URL, json=body)

        return await resp.json()

    async def setup_subscription(
        self, app_id: str, callback_url: str, verify_token: str
    ):
        """Set up a subscription to receive messages from the specified app with a callback URL and verification token."""
        URL = BASE_API + f"/{app_id}/subscriptions"

        body = {
            "object": "page",
            "callback_url": callback_url,
            "fields": ["messages"],
            "include_values": True,
            "verify_token": verify_token,
        }

        resp = await self._post(URL, json=body)

        return await resp.json()
