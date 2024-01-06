"""Constants for facebook_messenger."""

################################
# Do not change! Will be set by release workflow
INTEGRATION_VERSION = "1.1.0"  # x-release-please-version
################################

NAME = "Facebook Messenger"
DOMAIN = "facebook_messenger"
ATTRIBUTION = "Data provided by Facebook"


WEBHOOK_URL = "/api/facebook_messenger/webhook"
WEBHOOK_ID = "facebook_messenger_webhook"

CONF_CLOUDHOOK_URL = "cloudhook_url"

ATTR_TEXT = "text"

SAVE_DELAY = 10
STORAGE_KEY = DOMAIN
STORAGE_VERSION = 1

CONF_WEBOOK_VERIFY_TOKEN = "verify_token"
CONF_APP_NAME = "app_name"
