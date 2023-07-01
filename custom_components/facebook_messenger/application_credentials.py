"""Application Credentials module."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.application_credentials import (
    AuthImplementation,
    AuthorizationServer,
    ClientCredential,
)
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

FACEBOOK_TOKEN_URI = "https://graph.facebook.com/v17.0/oauth/access_token"
FACEBOOK_AUTH_URI = "https://www.facebook.com/v17.0/dialog/oauth"


class FacebookOAuth2Implementation(AuthImplementation):
    """Local OAuth2 implementation for Geocaching."""

    def __init__(
        self,
        hass: HomeAssistant,
        auth_domain: str,
        credential: ClientCredential,
    ) -> None:
        """Local Geocaching Oauth Implementation."""
        super().__init__(
            hass=hass,
            auth_domain=auth_domain,
            credential=credential,
            authorization_server=AuthorizationServer(
                authorize_url=FACEBOOK_AUTH_URI,
                token_url=FACEBOOK_TOKEN_URI,
            ),
        )

    @property
    def extra_authorize_data(self) -> dict:
        """Extra data that needs to be appended to the authorize url."""
        scopes = ["pages_messaging", "pages_manage_metadata", "email"]
        return {
            "scope": " ".join(scopes),
        }

    async def async_resolve_external_data(self, external_data: Any) -> dict:
        """Initialize local Geocaching API auth implementation."""
        token = await self._token_request(
            {
                "grant_type": "authorization_code",
                "code": external_data["code"],
                "redirect_uri": external_data["state"]["redirect_uri"],
            }
        )

        if "expires_in" not in token:
            token["expires_in"] = 315360000  # ten years

        return token


async def async_get_auth_implementation(
    hass: HomeAssistant, auth_domain: str, credential: ClientCredential
) -> AuthImplementation:
    """Return auth implementation."""
    return FacebookOAuth2Implementation(hass, auth_domain, credential)
