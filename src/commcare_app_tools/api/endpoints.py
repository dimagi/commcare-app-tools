"""CommCare HQ API endpoint path constants.

These are the path components after /a/{domain}/ for domain-scoped endpoints,
or absolute paths for global endpoints.
"""

# Application management
APP_LIST = "api/application/v1/"
APP_DETAIL = "api/application/v1/{app_id}/"

# Case management
CASE_LIST_V2 = "api/case/v2/"
CASE_DETAIL_V2 = "api/case/v2/{case_id}/"
CASE_BULK_FETCH = "api/case/v2/bulk-fetch/"
CASE_BY_EXTERNAL_ID = "api/case/v2/ext/{external_id}/"
CASE_ATTACHMENT = "api/case/attachment/{case_id}/{attachment_id}"

# Form management
FORM_LIST = "api/form/v1/"
FORM_DETAIL = "api/form/v1/{form_id}/"
FORM_ATTACHMENT = "api/form/attachment/{instance_id}/{attachment_id}"

# User management
USER_LIST = "api/user/v1/"
USER_DETAIL = "api/user/v1/{user_id}/"
WEB_USER_LIST = "api/web_user/v1/"
WEB_USER_DETAIL = "api/web_user/v1/{user_id}/"

# Location management
LOCATION_LIST = "api/location/v2/"
LOCATION_DETAIL = "api/location/v2/{location_id}/"
LOCATION_TYPE_LIST = "api/location_type/v1/"

# Lookup tables (fixtures)
LOOKUP_TABLE_LIST = "api/lookup_table/v1/"
LOOKUP_TABLE_DETAIL = "api/lookup_table/v1/{table_id}/"
LOOKUP_TABLE_ITEM_LIST = "api/lookup_table_item/v2/"
LOOKUP_TABLE_ITEM_DETAIL = "api/lookup_table_item/v2/{item_id}/"

# Reports
REPORT_CONFIG_LIST = "api/simple_report_configuration/v1/"
REPORT_DATA = "api/configurable_report_data/v1/{report_id}/"
UCR_DATA = "api/ucr/v1/"

# Domain / identity (user-scoped, not domain-scoped)
IDENTITY = "/api/identity/v1/"
USER_DOMAINS = "/api/user_domains/v1/"

# Messaging
MESSAGING_EVENTS = "api/messaging-event/v1/"

# OData
ODATA_CASES = "api/odata/cases/v1/"
ODATA_FORMS = "api/odata/forms/v1/"
