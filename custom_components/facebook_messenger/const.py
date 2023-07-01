"""Constants for facebook_messenger."""

################################
# Do not change! Will be set by release workflow
INTEGRATION_VERSION = "main"  # git tag will be used
MIN_REQUIRED_HA_VERSION = "0.0.0"  # set min required version in hacs.json
################################

NAME = "Facebook Messenger"
DOMAIN = "facebook_messenger"
ATTRIBUTION = "Data provided by Facebook"


WEBHOOK_URL = "/api/facebook_messenger/webhook"

ATTR_TEXT = "text"

SAVE_DELAY = 10
STORAGE_KEY = DOMAIN
STORAGE_VERSION = 1
