class ModuleDocFragment(object):

    DOCUMENTATION = r"""
    options:
        portainer_url:
            description: URL of the Portainer instance
            required: true
            type: str
        portainer_token:
            description: Portainer API access token
            required: true
            type: str
        timeout:
            description: Timeout for API requests
            type: int
            default: 30
        validate_certs:
            description: Validate SSL certificates
            type: bool
            default: true
    """
