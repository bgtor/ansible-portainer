"""
Portainer API Field Reference
Generated from API responses and verified through testing.

Use this as the source of truth for field names.
"""


class PortainerFields:
    """Verified field names from Portainer API responses"""

    # Endpoint Groups
    GROUP_ID = "Id"
    GROUP_NAME = "Name"
    GROUP_DESCRIPTION = "Description"
    GROUP_TAG_IDS = "TagIDs"
    GROUP_ASSOCIATED_ENDPOINTS = "AssociatedEndpoints"

    # Tags
    TAG_ID = "ID"
    TAG_NAME = "Name"
    TAG_ENDPOINTS = "Endpoints"

    # Endpoints
    ENDPOINT_ID = "Id"
    ENDPOINT_NAME = "Name"
    ENDPOINT_NAME_QUERY = "name"
    ENDPOINT_HEARTBEAT = "Heartbeat"
    ENDPOINT_GROUP_ID = "GroupId"
    ENDPOINT_GROUP_ID_FORM_DATA = "GroupID"
    ENDPOINT_GROUP_IDS = "GroupIds"
    ENDPOINT_TAG_IDS = "TagIds"
    ENDPOINT_GROUP_IDS_QUERY = "groupIds"
    ENDPOINT_TAG_IDS_QUERY = "tagIds"
    ENDPOINT_CREATION_TYPE = "EndpointCreationType"
    ENDPOINT_URL = "URL"
    ENDPOINT_EDGE_CHECKIN_INTERVAL = "EdgeCheckinInterval"
    ENDPOINT_EDGE_TUNNEL_SERVER_ADDRESS = "EdgeTunnelServerAddress"
    ENDPOINT_TLS_CONFIG = "TLSConfig"
    ENDPOINT_TLS = "TLS"
    ENDPOINT_TLS_CA_CERT = "TLSCACert"
    ENDPOINT_TLS_CERT = "TLSCert"
    ENDPOINT_TLS_KEY = "TLSKey"
    ENDPOINT_TLS_SKIP_VERIFY = "TLSSkipVerify"
    ENDPOINT_EXCLUDE_SNAPSHOT = "excludeSnapshots"
    ENDPOINT_EXCLUDE_SNAPSHOT_RAW = "excludeSnapshotRaw"
    ENDPOINT_TYPE = "Type"
    ENDPOINT_SWARM = "Swarm"

    # Stacks
    STACK_ID = "Id"
    STACK_NAME = "Name"
    STACK_ENDPOINT_ID = "EndpointId"
    STACK_ENDPOINT_ID_QUERY = "endpointId"
    STACK_ADDITIONAL_FILES = "AdditionalFiles"
    STACK_AUTOUPDATE = "AutoUpdate"
    STACK_COMPOSE_FILE = "ComposeFile"
    STACK_ENV = "Env"
    STACK_ENV_FORM_DATA = "env"
    STACK_PRUNE = "Prune"
    STACK_PULL_IMAGES = "PullImage"
    STACK_FROM_APP_TEMPLATE = "FromAppTemplate"
    STACK_REPOSITORY_AUTHENTICATION = "RepositoryAuthentication"
    STACK_REPOSITORY_AUTHORIZATION_TYPE = "RepositoryAuthorizationType"
    STACK_REPOSITORY_PASSWORD = "RepositoryPassword"
    STACK_REPOSITORY_REFERENCE_NAME = "RepositoryReferenceName"
    STACK_REPOSITORY_URL = "RepositoryURL"
    STACK_REPOSITORY_USERNAME = "RepositoryUsername"
    STACK_SWARM_ID = "SwarmId"
    STACK_SWARM_ID_FORM_DATA = "SwarmID"
    STACK_TLS_SKIP_VERIFY = "TlsskipVerify"
    STACK_FILE = "file"
    STACK_FILE_CONTENT = "StackFileContent"
    STACK_STATUS = "Status"
    STACK_GIT_CONFIGS = "GitConfig"
    STACK_GIT_CONFIGS_AUTHENTICATION = "Authentication"
    STACK_GIT_CONFIGS_AUTH_TYPE = "Authentication.AuthorizationType"
    STACK_GIT_CONFIGS_USERNAME = "Authentication.Username"
    STACK_GIT_CONFIGS_REFS_NAME = "ReferenceName"
    STACK_GIT_CONFIGS_TLS_SKIP_VERIFY = "TLSSkipVerify"

    # Configs
    CONFIG_ID = "ID"
    CONFIG_NAME = "Name"
    CONFIG_DATA = "Data"

    # Secrets
    SECRET_ID = "ID"
    SECRET_NAME = "Name"
    SECRET_DATA = "Data"

    # Networks
    NETWORK_ID = "Id"
    NETWORK_NAME = "Name"
    NETWORK_DRIVER = "Driver"
    NETWORK_SCOPE = "Scope"
    NETWORK_INTERNAL = "Internal"
    NETWORK_ATTACHABLE = "Attachable"
    NETWORK_INGRESS = "Ingress"
