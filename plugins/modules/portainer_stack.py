#!/usr/bin/python
# portainer_stack.py - A module to manage Portainer environment stacks.
# Author: Igor Moraru (@bgtor)
# License: GPL-3.0-or-later
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function, annotations

__metaclass__ = type

DOCUMENTATION = r"""
---
module: portainer_stack
short_description: Manage Portainer environment stacks
description:
    - Create, update, delete, start, stop, or redeploy Docker stacks in Portainer.
    - Supports both Docker Swarm and Standalone (Compose) stack types.
    - Supports stack definitions from local files or Git repositories.
    - Provides idempotent operations with check mode and diff support.
    - Automatically detects configuration changes and applies updates only when necessary.
version_added: "1.0.0"
author: Igor Moraru (@bgtor)
options:
    name:
        description:
            - Name of the stack to manage.
            - Required when O(stack_id) is not provided.
            - Used to identify existing stacks in combination with O(endpoint_id) or O(swarm_id).
        type: str
        required: false

    stack_id:
        description:
            - Unique identifier of the stack.
            - Can be used instead of O(name) to directly reference a stack.
            - Useful when the stack ID is already known from previous operations.
        type: int
        required: false

    stack_type:
        description:
            - Type of Docker stack to manage.
            - V(swarm) creates a stack in a Docker Swarm cluster.
            - V(standalone) creates a stack using Docker Compose on a single endpoint.
            - Required when O(state=present).
        type: str
        choices: ['swarm', 'standalone']
        required: false

    stack_source:
        description:
            - Source from which to load the stack definition.
            - V(file) loads the stack from a local file path specified in O(file).
            - V(repository) loads the stack from a Git repository.
            - Required when O(state=present).
        type: str
        choices: ['file', 'repository']
        required: false

    state:
        description:
            - Desired state of the stack.
            - V(present) ensures the stack exists with the specified configuration.
            - V(absent) ensures the stack is deleted.
            - V(redeployed) triggers a redeployment (pulls latest changes for repository stacks).
            - V(started) ensures the stack is running.
            - V(stopped) ensures the stack is stopped.
        type: str
        choices: ['present', 'absent', 'redeployed', 'started', 'stopped']
        default: present

    endpoint_id:
        description:
            - ID of the Portainer endpoint where the stack should be deployed.
            - Required when creating new stacks.
            - Can be used with O(name) to identify existing stacks.
            - Endpoint represents a Docker environment (local, remote, or edge).
        type: int
        required: false

    swarm_id:
        description:
            - Identifier of the Docker Swarm cluster.
            - Required when creating new swarm-type stacks.
            - Can be used with O(name) to identify existing swarm stacks.
            - Only applicable when O(stack_type=swarm).
        type: str
        required: false

    env:
        description:
            - List of environment variables to pass to the stack.
            - Each item should be a dictionary with environment variable configuration.
            - Typically includes C(name) and C(value) keys.
            - Environment variables override values in the compose file.
        type: list
        elements: dict
        required: false

    prune:
        description:
            - Remove services that are no longer defined in the compose file.
            - When V(true), services not in the updated compose file are removed.
            - When V(false) or not set, orphaned services remain running.
            - Only affects update and redeploy operations.
        type: bool
        required: false

    pull_images:
        description:
            - Pull the latest image versions when deploying or updating.
            - When V(true), Portainer pulls images even if they exist locally.
            - Useful for ensuring latest image tags are used.
            - May increase deployment time.
        type: bool
        required: false

    file:
        description:
            - Path to the Docker Compose file on the Ansible control node.
            - Required when O(stack_source=file).
            - File must be valid UTF-8 text (binary files are rejected).
            - File is read and uploaded to Portainer.
            - Path is relative to the playbook or absolute.
        type: path
        required: false

    repository_url:
        description:
            - URL of the Git repository containing the stack definition.
            - Required when O(stack_source=repository) and creating a new stack.
            - Supports HTTPS and SSH protocols.
            - Example C(https://github.com/user/repo.git) or C(git@github.com:user/repo.git).
        type: str
        required: false

    compose_file:
        description:
            - Path to the compose file within the Git repository.
            - Required when O(stack_source=repository) and creating a new stack.
            - Path is relative to the repository root.
            - Example C(docker-compose.yml) or C(deploy/production.yml).
        type: str
        required: false

    refs_name:
        description:
            - Git reference to checkout (branch, tag, or commit SHA).
            - Required when O(stack_source=repository) and creating a new stack.
            - Examples V(main), V(v1.2.3), V(develop), or a commit SHA.
            - Portainer will pull from this reference when deploying/updating.
        type: str
        required: false

    repository_authentication:
        description:
            - Whether the Git repository requires authentication.
            - Required when O(stack_source=repository) and creating a new stack.
            - When V(true), O(repository_username) and O(repository_password) must be provided.
            - When V(false), repository must be publicly accessible.
        type: bool
        required: false

    repository_username:
        description:
            - Username for Git repository authentication.
            - Required when O(repository_authentication=true).
            - Used for HTTPS authentication.
            - For GitHub, can be a personal access token as username with empty password.
        type: str
        required: false

    repository_password:
        description:
            - Password or token for Git repository authentication.
            - Required when O(repository_authentication=true).
            - Supports personal access tokens, deploy keys, or passwords.
            - Value is not logged (C(no_log=true)).
        type: str
        required: false

    update_password:
        description:
            - Force update when only the password has changed.
            - Due to API limitations, password changes cannot be reliably detected.
            - When V(true), the module always marks the task as changed for repository stacks.
            - Set to V(true) after changing repository credentials to force an update.
            - Only applicable to repository-based stacks.
        type: bool
        default: false

    additional_files:
        description:
            - List of additional compose files to merge with the main compose file.
            - Files are relative to the repository root.
            - Applied in order, with later files overriding earlier ones.
            - Example C(['docker-compose.override.yml', 'docker-compose.prod.yml']).
            - Only applicable when O(stack_source=repository).
        type: list
        elements: str
        required: false

    autoupdate:
        description:
            - Auto-update configuration for the stack.
            - Dictionary containing auto-update settings.
            - Enables automatic redeployment when repository changes are detected.
            - Structure depends on Portainer API version.
            - Only applicable when O(stack_source=repository).
        type: dict
        required: false

    tls_skip_verify:
        description:
            - Skip TLS certificate verification when accessing the Git repository.
            - When V(true), self-signed or invalid certificates are accepted.
            - Use with caution as it reduces security.
            - Useful for private Git servers with self-signed certificates.
            - Only applicable when O(stack_source=repository).
        type: bool
        required: false

extends_documentation_fragment:
    - bgtor.portainer.portainer_client

notes:
    - Either O(name) or O(stack_id) must be provided for all operations.
    - For O(state=present), both O(stack_type) and O(stack_source) are required.
    - When creating new standalone stacks, O(endpoint_id) is required.
    - When creating new swarm stacks, both O(endpoint_id) and O(swarm_id) are required.
    - For O(state=started), O(state=stopped), or O(state=absent), the stack can be identified using
      O(stack_id) alone, or O(name) + O(endpoint_id), or O(name) + O(swarm_id).
    - Password changes for repository-based stacks cannot be reliably detected by the API.
      Set O(update_password=true) to force updates when credentials change.
    - The module supports check mode (C(--check)) for previewing changes without applying them.
    - The module supports diff mode (C(--diff)) for showing configuration differences.
    - Stack files must be valid UTF-8 text; binary files are rejected.
    - Environment variables in O(env) override values defined in the compose file.
"""

EXAMPLES = r"""
- name: Create a standalone stack from a local file
  portainer_stack:
    name: myapp
    stack_type: standalone
    stack_source: file
    endpoint_id: 1
    file: /path/to/docker-compose.yml
    env:
      - name: APP_ENV
        value: production
      - name: DEBUG
        value: "false"
    prune: true
    state: present

- name: Create a swarm stack from a Git repository
  portainer_stack:
    name: webapp
    stack_type: swarm
    stack_source: repository
    endpoint_id: 1
    swarm_id: abc123xyz
    repository_url: https://github.com/myorg/myapp.git
    repository_authentication: true
    repository_username: github_user
    repository_password: "{{ github_token }}"
    refs_name: main
    compose_file: docker-compose.yml
    prune: true
    pull_images: true
    env:
      - name: ENVIRONMENT
        value: staging
    state: present

- name: Create a stack from a private repository with self-signed cert
  portainer_stack:
    name: internal-app
    stack_type: standalone
    stack_source: repository
    endpoint_id: 2
    repository_url: https://git.internal.company/infra/app.git
    repository_authentication: true
    repository_username: deploy-user
    repository_password: "{{ vault_deploy_token }}"
    refs_name: release/v2.0
    compose_file: deployments/docker-compose.yml
    tls_skip_verify: true
    state: present

- name: Update an existing stack with new configuration
  portainer_stack:
    name: myapp
    stack_type: standalone
    stack_source: file
    endpoint_id: 1
    file: /path/to/updated-docker-compose.yml
    env:
      - name: APP_ENV
        value: development
      - name: LOG_LEVEL
        value: debug
    prune: true
    pull_images: true
    state: present

- name: Update stack after changing repository password
  portainer_stack:
    name: webapp
    stack_type: swarm
    stack_source: repository
    endpoint_id: 1
    swarm_id: abc123xyz
    repository_url: https://github.com/myorg/myapp.git
    repository_authentication: true
    repository_username: github_user
    repository_password: "{{ new_github_token }}"
    update_password: true
    state: present

- name: Redeploy a repository-based stack to pull latest changes
  portainer_stack:
    stack_id: 5
    state: redeployed

- name: Redeploy stack using name and endpoint
  portainer_stack:
    name: myapp
    endpoint_id: 1
    state: redeployed

- name: Create stack with multiple compose files
  portainer_stack:
    name: complex-app
    stack_type: swarm
    stack_source: repository
    endpoint_id: 1
    swarm_id: swarm123
    repository_url: https://gitlab.com/myorg/infrastructure.git
    repository_authentication: false
    refs_name: v1.2.3
    compose_file: docker-compose.yml
    additional_files:
      - docker-compose.override.yml
      - docker-compose.prod.yml
    state: present

- name: Create self-updating stack with autoupdate
  portainer_stack:
    name: auto-updated-app
    stack_type: standalone
    stack_source: repository
    endpoint_id: 1
    repository_url: https://github.com/myorg/app.git
    repository_authentication: false
    refs_name: main
    compose_file: docker-compose.yml
    autoupdate:
      interval: "5m"
      webhook: "https://webhook.example.com/update"
    state: present

- name: Stop a running stack
  portainer_stack:
    name: myapp
    endpoint_id: 1
    state: stopped

- name: Stop stack using stack_id
  portainer_stack:
    stack_id: 5
    state: stopped

- name: Start a stopped stack
  portainer_stack:
    name: myapp
    endpoint_id: 1
    state: started

- name: Delete a stack
  portainer_stack:
    name: myapp
    endpoint_id: 1
    state: absent

- name: Delete stack using stack_id
  portainer_stack:
    stack_id: 5
    state: absent

- name: Preview stack changes without applying (check mode)
  portainer_stack:
    name: myapp
    stack_type: standalone
    stack_source: file
    endpoint_id: 1
    file: /path/to/docker-compose.yml
    state: present
  check_mode: yes
  diff: yes

- name: Create stack with extensive environment configuration
  portainer_stack:
    name: production-api
    stack_type: standalone
    stack_source: file
    endpoint_id: 1
    file: /opt/stacks/api/docker-compose.yml
    env:
      - name: DATABASE_HOST
        value: postgres.internal
      - name: DATABASE_PORT
        value: "5432"
      - name: DATABASE_NAME
        value: api_prod
      - name: REDIS_HOST
        value: redis.internal
      - name: API_KEY
        value: "{{ vault_api_key }}"
      - name: LOG_LEVEL
        value: info
    prune: true
    pull_images: false
    state: present
"""

RETURN = r"""
changed:
    description: Whether the stack was modified
    type: bool
    returned: always
    sample: true

msg:
    description: Human-readable message describing the operation result
    type: str
    returned: always
    sample: "Stack created."

stack:
    description: Complete stack information including configuration
    type: dict
    returned: always
    contains:
        Id:
            description: Unique identifier of the stack
            type: int
            sample: 5
        Name:
            description: Name of the stack
            type: str
            sample: "myapp"
        EndpointId:
            description: ID of the endpoint where the stack is deployed
            type: int
            sample: 1
        SwarmId:
            description: Swarm cluster ID (for swarm stacks)
            type: str
            sample: "abc123xyz"
        Env:
            description: Environment variables configured for the stack
            type: list
            elements: dict
            sample:
              - name: "APP_ENV"
                value: "production"
              - name: "DEBUG"
                value: "false"
        Status:
            description: Current status of the stack (1=running, 2=stopped)
            type: int
            sample: 1
        Prune:
            description: Whether pruning is enabled
            type: bool
            sample: true
        RepositoryURL:
            description: Git repository URL (for repository-based stacks)
            type: str
            sample: "https://github.com/myorg/myapp.git"
        ComposeFile:
            description: Path to compose file in repository
            type: str
            sample: "docker-compose.yml"
        RepositoryReferenceName:
            description: Git reference being used
            type: str
            sample: "main"
        RepositoryAuthentication:
            description: Whether repository authentication is enabled
            type: bool
            sample: true
        RepositoryUsername:
            description: Username for repository authentication
            type: str
            sample: "deploy-user"
        AdditionalFiles:
            description: Additional compose files being merged
            type: list
            elements: str
            sample: ["docker-compose.override.yml"]
        TLSSkipVerify:
            description: Whether TLS verification is skipped
            type: bool
            sample: false
        AutoUpdate:
            description: Auto-update configuration
            type: dict
            sample: {"interval": "5m"}

diff:
    description: Differences between old and new stack configuration
    type: dict
    returned: when diff mode is enabled and changes are detected
    contains:
        before:
            description: Previous stack configuration
            type: dict
            sample: {"Env": [{"name": "APP_ENV", "value": "development"}]}
        after:
            description: New stack configuration
            type: dict
            sample: {"Env": [{"name": "APP_ENV", "value": "production"}]}
"""

import json

from typing import Literal, TYPE_CHECKING, ClassVar
from dataclasses import dataclass, field

from ..module_utils.portainer_fields import PortainerFields as PF
from ..module_utils.portainer_module import PortainerModule
from ..module_utils.portainer_client import BodyFormat


if TYPE_CHECKING:
    from ..module_utils.portainer_crud import StackCRUD


class StackStatus:
    RUNNING = 1
    STOPPED = 2


@dataclass
class Stack:
    id: int | None = None
    name: str | None = None
    env: list[dict] | None = None
    prune: bool | None = None
    pull_images: bool | None = None
    additional_files: list[str] | None = None
    autoupdate: dict | None = None
    compose_file: str | None = None
    rep_authentication: bool | None = None
    rep_password: str | None = None
    rep_refs_name: str | None = None
    rep_url: str | None = None
    rep_username: str | None = None
    swarm_id: str | None = None
    endpoint_id: int | None = None
    tls_skip_verify: bool | None = None
    status: int | None = None

    # Note: Both PF.STACK_SWARM_ID and PF.STACK_SWARM_ID_FORM_DATA map to "swarm_id",
    # and both PF.STACK_ENDPOINT_ID and PF.STACK_ENDPOINT_ID_QUERY map to "endpoint_id".
    # This duplication is intentional to support different API parameter formats (JSON and form-data)
    # and ensure consistent attribute mapping regardless of context.

    fields_mapping: ClassVar[dict] = {
        PF.STACK_ID: "id",
        PF.STACK_NAME: "name",
        PF.STACK_ENV: "env",
        PF.STACK_PRUNE: "prune",
        PF.STACK_PULL_IMAGES: "pull_images",
        PF.STACK_ADDITIONAL_FILES: "additional_files",
        PF.STACK_AUTOUPDATE: "autoupdate",
        PF.STACK_COMPOSE_FILE: "compose_file",
        PF.STACK_REPOSITORY_AUTHENTICATION: "rep_authentication",
        PF.STACK_REPOSITORY_PASSWORD: "rep_password",
        PF.STACK_REPOSITORY_REFERENCE_NAME: "rep_refs_name",
        PF.STACK_REPOSITORY_URL: "rep_url",
        PF.STACK_REPOSITORY_USERNAME: "rep_username",
        PF.STACK_SWARM_ID: "swarm_id",
        PF.STACK_SWARM_ID_FORM_DATA: "swarm_id",
        PF.STACK_ENDPOINT_ID: "endpoint_id",
        PF.STACK_ENDPOINT_ID_QUERY: "endpoint_id",
        PF.STACK_TLS_SKIP_VERIFY: "tls_skip_verify",
        PF.STACK_STATUS: "status",
    }

    private_fields: ClassVar[list[str]] = [PF.STACK_REPOSITORY_PASSWORD]

    def update_from_dict(self, data: dict) -> None:
        for k, v in data.items():
            if k in self.fields_mapping:
                setattr(self, self.fields_mapping[k], v)

    def to_dict(self) -> dict:
        data = {}
        for k, v in self.fields_mapping.items():
            value = getattr(self, v)
            if value is None:
                continue
            if k in self.private_fields:
                data[k] = "***"
                continue
            data[k] = value
        return data


@dataclass
class StackConfig:
    """Configuration for different stack types and sources."""

    create_keys: list = field(default_factory=list)
    update_keys: list = field(default_factory=list)
    redeploy_keys: list = field(default_factory=list)
    create_body_format: BodyFormat = BodyFormat.JSON
    needs_swarm_id: bool = False
    skip_fields_from_changes: list[str] = field(default_factory=list)
    required_one_of: list[tuple] = field(default_factory=list)

    def __post_init__(self) -> None:
        base_skip = ["ResourceControl", "UpdateDate", "UpdatedBy"]

        # Add STACK_FILE to skip for file-based stacks
        if PF.STACK_FILE in self.create_keys:
            base_skip.append(PF.STACK_FILE)

        # Merge with any user-provided skip fields
        self.skip_fields_from_changes = list(set(base_skip + self.skip_fields_from_changes))

    @classmethod
    def for_stack(
        cls, stack_type: str | None = None, stack_source: str | None = None
    ) -> StackConfig:
        # Common keys
        COMMON_ENV_KEYS = [PF.STACK_ENV, PF.STACK_PRUNE]
        COMMON_REPO_KEYS = [
            PF.STACK_AUTOUPDATE,
            PF.STACK_REPOSITORY_AUTHENTICATION,
            PF.STACK_REPOSITORY_PASSWORD,
            PF.STACK_REPOSITORY_REFERENCE_NAME,
            PF.STACK_REPOSITORY_USERNAME,
            PF.STACK_TLS_SKIP_VERIFY,
        ]

        # Build configs based on type + source
        if stack_source == "file":
            base_create = [PF.STACK_NAME, PF.STACK_ENV, PF.STACK_FILE]
            base_update = [
                PF.STACK_ENV,
                PF.STACK_PRUNE,
                PF.STACK_PULL_IMAGES,
                PF.STACK_FILE_CONTENT,
            ]

            if stack_type == "swarm":
                base_create.append(PF.STACK_SWARM_ID_FORM_DATA)

            return cls(
                create_keys=base_create,
                update_keys=base_update,
                redeploy_keys=[],
                create_body_format=BodyFormat.FORM_DATA,
                needs_swarm_id=(stack_type == "swarm"),
            )

        elif stack_source == "repository":
            base_create = [
                PF.STACK_NAME,
                PF.STACK_ADDITIONAL_FILES,
                PF.STACK_COMPOSE_FILE,
                PF.STACK_REPOSITORY_URL,
                *COMMON_ENV_KEYS,
                *COMMON_REPO_KEYS,
            ]

            base_update = list(
                set(base_create)
                - set(
                    [
                        PF.STACK_NAME,
                        PF.STACK_REPOSITORY_URL,
                        PF.STACK_COMPOSE_FILE,
                        PF.STACK_ADDITIONAL_FILES,
                        PF.STACK_SWARM_ID,
                    ]
                )
            ) + [
                PF.STACK_REPOSITORY_AUTHORIZATION_TYPE,
            ]

            base_redeploy = base_update + [PF.STACK_PULL_IMAGES]

            if stack_type == "swarm":
                base_create.append(PF.STACK_SWARM_ID)

            return cls(
                create_keys=base_create,
                update_keys=base_update,
                redeploy_keys=base_redeploy,
                create_body_format=BodyFormat.JSON,
                needs_swarm_id=(stack_type == "swarm"),
                # Excluding password from changes since we cannot reliably check when it changes
                # This is harmless because we are sending all stack data when changes are detected
                skip_fields_from_changes=[PF.STACK_REPOSITORY_PASSWORD],
            )
        # For started, stopped and absent operations we need only the stack_id.
        # We can get it either from module args, or from API with a name + endpoint_id
        # or name + swarm_id combination
        elif stack_type is None and stack_source is None:
            return cls(
                required_one_of=[
                    ("stack_id",),
                    ("name", "endpoint_id"),
                    ("name", "swarm_id"),
                ],
            )
        else:
            raise ValueError(f"Unsupported stack configuration: {stack_type} + {stack_source}")


class StackValidator:
    """
    Validates arguments and requirements for stack operations in Portainer.

    This class checks for required parameters and configuration combinations
    when creating, updating, or managing stacks, ensuring that all necessary
    fields are provided based on stack type and source.
    """

    def __init__(
        self,
        module: PortainerModule,
        state_manager: StackStateManager,
        config: StackConfig,
    ) -> None:
        self.module = module
        self.state_manager = state_manager
        self.config = config

    def validate_args(self) -> None:
        self._validate_new_stack_requirements()
        self._validate_stack_source_requirements()
        self._validate_config_requirements()

    def _maybe_stack_exists(self) -> bool:
        """Check if we have enough info to identify an existing stack."""
        has_id = self.state_manager.stack_id is not None
        has_name = self.state_manager.name is not None
        has_endpoint = self.state_manager.endpoint_id is not None
        has_swarm = self.state_manager.swarm_id is not None

        if self.state_manager.stack_type == "swarm":
            return has_id or (has_name and (has_endpoint or has_swarm))
        elif self.state_manager.stack_type == "standalone":
            return has_id or (has_name and has_endpoint)

        return False

    def _validate_new_stack_requirements(self) -> None:
        """Validate requirements for creating new stacks."""

        # Only validate when creating new stacks
        if self.state_manager.state != "present" or self._maybe_stack_exists():
            return

        # Standalone stacks need endpoint_id
        if self.state_manager.stack_type == "standalone":
            if self.state_manager.endpoint_id is None:
                self.module.fail_json(
                    msg="Provide 'endpoint_id' when creating new standalone stacks."
                )

        # Swarm stacks need both endpoint_id and swarm_id
        if self.state_manager.stack_type == "swarm":
            missing = []
            if self.state_manager.endpoint_id is None:
                missing.append("endpoint_id")
            if self.state_manager.swarm_id is None:
                missing.append("swarm_id")

            if missing:
                self.module.fail_json(
                    msg=f"Provide {' and '.join(missing)} when creating new swarm stacks."
                )

    def _validate_stack_source_requirements(self) -> None:
        """Validate requirements based on stack source."""

        if self.state_manager.state != "present":
            return

        # File-based stacks need a file
        if self.state_manager.stack_source == "file":
            if self.state_manager.file is None:
                self.module.fail_json(msg="Provide 'file' for file-based stacks.")

        # Repository-based stacks need repository details
        if self.state_manager.stack_source == "repository":
            # Only validate for new stacks
            if not self._maybe_stack_exists():
                required = {
                    "repository_url": self.state_manager.repository_url,
                    "compose_file": self.state_manager.compose_file,
                    "refs_name": self.state_manager.refs_name,
                    "repository_authentication": self.state_manager.repository_authentication,
                }

                missing = [k for k, v in required.items() if v is None]
                if missing:
                    self.module.fail_json(
                        msg=f"Provide {', '.join(missing)} for repository-based stacks."
                    )

            # If authentication is enabled, need credentials
            if self.state_manager.repository_authentication:
                if (
                    not self.state_manager.repository_username
                    or not self.state_manager.repository_password
                ):
                    self.module.fail_json(
                        msg="Provide 'repository_username' and 'repository_password' when repository_authentication is True."
                    )

    def _validate_config_requirements(self) -> None:
        if self.config.required_one_of:
            fulfilled = False

            for args in self.config.required_one_of:
                if all(getattr(self.state_manager, arg, None) is not None for arg in args):
                    fulfilled = True
                    break

            if not fulfilled:
                self.module.fail_json(
                    msg="Provide one of the required field combinations: "
                    f"{' or '.join([' + '.join(args) for args in self.config.required_one_of])}"
                )


class StackDataBuilder:
    """
    Provides methods to retrieve and prepare stack data for CRUD operations in Portainer.

    This class is responsible for preparing data for stack creation,
    update, and redeployment actions, and safely reading stack files from disk. It acts as
    an interface between the stack state manager and the underlying CRUD operations, ensuring
    that all required data is available and correctly formatted for API requests.
    """

    def __init__(
        self,
        module: PortainerModule,
        state_manager: StackStateManager,
        config: StackConfig,
    ) -> None:
        self.module = module
        self.crud = module.crud
        self.config = config
        self.state_manager = state_manager

        self._file_content_cache = None

    def _get_lazy_data(self) -> dict:
        data = {
            PF.STACK_NAME: self.state_manager.name,
            PF.STACK_ENV: self.state_manager.env,
            PF.STACK_PRUNE: self.state_manager.prune,
            PF.STACK_PULL_IMAGES: self.state_manager.pull_images,
            PF.STACK_ADDITIONAL_FILES: self.state_manager.additional_files,
            PF.STACK_AUTOUPDATE: self.state_manager.autoupdate,
            PF.STACK_COMPOSE_FILE: self.state_manager.compose_file,
            PF.STACK_REPOSITORY_AUTHENTICATION: self.state_manager.repository_authentication,
            PF.STACK_REPOSITORY_PASSWORD: self.state_manager.repository_password,
            PF.STACK_REPOSITORY_REFERENCE_NAME: self.state_manager.refs_name,
            PF.STACK_REPOSITORY_URL: self.state_manager.repository_url,
            PF.STACK_REPOSITORY_USERNAME: self.state_manager.repository_username,
            PF.STACK_SWARM_ID: self.state_manager.swarm_id,
            PF.STACK_SWARM_ID_FORM_DATA: self.state_manager.swarm_id,
            PF.STACK_TLS_SKIP_VERIFY: self.state_manager.tls_skip_verify,
        }

        lazy_data = {
            PF.STACK_FILE: self._get_stack_file,
            PF.STACK_FILE_CONTENT: self._get_stack_file_content,
        }

        return {**data, **lazy_data}

    def _get_data_for_action(
        self,
        action: str,
        exclude_keys: list[str] | None = None,
        only_keys: list[str] | None = None,
    ) -> dict:
        action_keys = {
            "create": self.config.create_keys,
            "update": self.config.update_keys,
            "redeploy": self.config.redeploy_keys,
        }

        only_keys = list(set((only_keys or []) + action_keys[action]))
        return self._get_merged_data(exclude_keys=exclude_keys, only_keys=only_keys)

    def get_create_data(self, **kwargs) -> dict:
        return self._get_data_for_action("create", **kwargs)

    def get_update_data(self, **kwargs) -> dict:
        return self._get_data_for_action("update", **kwargs)

    def get_redeploy_data(self, **kwargs) -> dict:
        return self._get_data_for_action("redeploy", **kwargs)

    def _get_merged_data(
        self,
        exclude_keys: list[str] | None = None,
        only_keys: list[str] | None = None,
    ) -> dict:
        exclude_keys = exclude_keys or []
        only_keys = only_keys or []

        lazy_data = self._get_lazy_data()

        def _filter_keys(
            _data: dict,
        ):
            _data = {k: v for k, v in _data.items() if k not in exclude_keys}

            if only_keys:
                _data = {k: v for k, v in _data.items() if k in only_keys}

            return _data

        filtered_lazy_data = _filter_keys(lazy_data)

        data = {k: (v() if callable(v) else v) for k, v in filtered_lazy_data.items()}
        data = {k: v for k, v in data.items() if v is not None}

        # Merge with existing configs
        data = {
            **_filter_keys(
                self.state_manager.old_stack.to_dict(),
            ),
            **data,
        }

        return data

    def _get_stack_file(self) -> tuple | None:
        content = self._read_file_once()

        if content:
            return ("file", content, "application/x-yaml")

        return None

    def _get_stack_file_content(self) -> str | None:
        content = self._read_file_once()
        if content:
            try:
                return content.decode("utf-8")
            except UnicodeDecodeError:
                self.module.fail_json(
                    msg=f"Stack file contains binary data: {self.state_manager.file}"
                )
        return None

    def _read_file_once(self):
        if self._file_content_cache is None and self.state_manager.file:
            self._file_content_cache = self._read_file_safely(self.state_manager.file, "stack file")
        return self._file_content_cache

    def _read_file_safely(self, filepath: str, description: str = "file") -> bytes:
        try:
            with open(filepath, "rb") as f:
                content = f.read()

            # Validate content
            if not content:
                self.module.fail_json(msg=f"{description.capitalize()} is empty: {filepath}")

            # Validate it's text
            self.module.validate_text_content(content, description, filepath=filepath)

            return content

        except FileNotFoundError:
            self.module.fail_json(msg=f"{description.capitalize()} not found: {filepath}")
        except PermissionError:
            self.module.fail_json(msg=f"Permission denied reading {description}: {filepath}")
        except IOError as e:
            self.module.fail_json(msg=f"Failed to read {description} {filepath}: {str(e)}")


class StackStateManager:
    """
    Manages the state and parameters of a Portainer stack during Ansible module execution.

    This class tracks stack attributes, updates state based on API responses, and stores previous stack data
    to support operations such as create, update, and delete.
    """

    def __init__(self, module: PortainerModule, config: StackConfig) -> None:
        self.module = module
        self.config = config

        self.name = module.params["name"]
        self.stack_id = module.params["stack_id"]
        self.state: Literal["present", "absent", "redeployed", "started", "stopped"] = (
            module.params["state"]
        )
        self.stack_type = module.params["stack_type"]
        self.stack_source = module.params["stack_source"]
        self.endpoint_id = module.params["endpoint_id"]
        self.swarm_id = module.params["swarm_id"]
        self.prune = module.params["prune"]
        self.pull_images = module.params["pull_images"]
        self.env = module.params["env"]
        self.additional_files = module.params["additional_files"]
        self.autoupdate = module.params["autoupdate"]
        self.compose_file = module.params["compose_file"]
        self.repository_authentication = module.params["repository_authentication"]
        self.repository_password = module.params["repository_password"]
        self.update_password = module.params["update_password"]
        self.refs_name = module.params["refs_name"]
        self.repository_url = module.params["repository_url"]
        self.repository_username = module.params["repository_username"]
        self.tls_skip_verify = module.params["tls_skip_verify"]
        self.file = module.params["file"]

        self.stack: Stack = Stack()
        self.old_stack: Stack = Stack()

    def update_state(self, stack_data: dict | None = None) -> None:
        if isinstance(stack_data, dict):
            self.stack.update_from_dict(stack_data)

        if self.stack.id:

            if self.endpoint_id is None:
                self.endpoint_id = self.stack.endpoint_id
            if self.swarm_id is None:
                self.swarm_id = self.stack.swarm_id
            if self.name is None:
                self.name = self.stack.name
            if self.stack_id is None:
                self.stack_id = self.stack.id

    def set_old_stack(self, old_stack_data: dict) -> None:
        self.old_stack.update_from_dict(old_stack_data)


class StackRepository:
    """
    StackRepository provides high-level operations for managing Portainer stacks.

    This class acts as a repository layer, orchestrating CRUD operations, state management,
    and data building for stack entities in Portainer. It delegates low-level actions to
    injected dependencies and maintains stack state consistency.
    """

    def __init__(
        self,
        crud: StackCRUD,
        state_manager: StackStateManager,
        data_builder: StackDataBuilder,
        config: StackConfig,
    ):
        self.crud = crud
        self.state_manager = state_manager
        self.data_builder = data_builder
        self.config = config

    def get_stack(self) -> dict | None:
        if self.state_manager.stack_id:
            return self.crud.get_item_by_id(self.state_manager.stack_id)

        if not self.state_manager.name:
            return

        params = {}
        if self.state_manager.swarm_id:
            params["filters"] = json.dumps({PF.STACK_SWARM_ID: self.state_manager.swarm_id})

        local_filters = {}
        if self.state_manager.endpoint_id:
            local_filters[PF.STACK_ENDPOINT_ID] = self.state_manager.endpoint_id

        return self.crud.validate_single_item(
            name=self.state_manager.name,
            operation="retrieve",
            params=params,
            filters=local_filters,
        )

    def create_stack(self) -> None:

        if not self.state_manager.name:
            return

        data = self.data_builder.get_create_data()

        # Convert Env data to json for form-data payloads
        if self.config.create_body_format == BodyFormat.FORM_DATA:
            data[PF.STACK_ENV] = json.dumps(data[PF.STACK_ENV])

        stack_data = self.crud.create_item(
            self.state_manager.name,
            item_data=data,
            body_format=self.config.create_body_format,
            params=self._get_endpoint_params(),
        )

        self.state_manager.update_state(stack_data)

    def update_stack(self) -> None:

        if not self.state_manager.stack.id:
            return

        stack_data = self.crud.update_item(
            self.state_manager.stack.id,
            changes=self.data_builder.get_update_data(),
            params=self._get_endpoint_params(),
        )

        self.state_manager.update_state(stack_data)

    def redeploy_stack(self) -> None:

        if not self.state_manager.stack.id:
            return

        stack_data = self.crud.redeploy(
            self.state_manager.stack.id,
            data=self.data_builder.get_redeploy_data(),
            params=self._get_endpoint_params(),
        )

        self.state_manager.update_state(stack_data)

    def delete_stack(self) -> None:

        if not self.state_manager.stack.id:
            return

        self.crud.delete_item_by_id(
            self.state_manager.stack.id,
            params=self._get_endpoint_params(),
        )

    def start_stack(self) -> None:

        if not self.state_manager.stack.id or not self.state_manager.endpoint_id:
            return

        self.crud.start_stack(
            stack_id=self.state_manager.stack.id,
            endpoint_id=self.state_manager.endpoint_id,
        )

    def stop_stack(self) -> None:
        if not self.state_manager.stack.id or not self.state_manager.endpoint_id:
            return

        self.crud.stop_stack(
            stack_id=self.state_manager.stack.id,
            endpoint_id=self.state_manager.endpoint_id,
        )

    def _get_endpoint_params(self) -> dict:
        return {PF.STACK_ENDPOINT_ID_QUERY: self.state_manager.endpoint_id}


class StackManager:
    """
    Handles the orchestration of stack operations in Portainer, including creation, update, redeployment, start, stop, and deletion,
    by coordinating validation, state management, data sourcing, and CRUD actions within the Ansible module context.
    """

    def __init__(
        self,
        module: PortainerModule,
        results: dict,
        config: StackConfig,
        state_manager: StackStateManager,
        validator: StackValidator,
        data_builder: StackDataBuilder,
        repository: StackRepository,
    ) -> None:

        self.state_manager = state_manager
        self.validator = validator
        self.data_builder = data_builder
        self.config = config
        self.repository = repository

        self.module = module
        self.idempotency = module.idempotency

        self.results = results
        self.check_mode = module.check_mode
        self.diff_mode = module._diff

    @classmethod
    def for_stack(
        cls, module: PortainerModule, results: dict, stack_type: str, stack_source: str
    ) -> StackManager:

        stack_config = StackConfig.for_stack(stack_type=stack_type, stack_source=stack_source)
        state_manager = StackStateManager(module, config=stack_config)

        stack_validator = StackValidator(module, state_manager=state_manager, config=stack_config)
        data_builder = StackDataBuilder(module, state_manager=state_manager, config=stack_config)
        repository = StackRepository(
            crud=module.crud.stack,
            state_manager=state_manager,
            data_builder=data_builder,
            config=stack_config,
        )

        return cls(
            module,
            results,
            config=stack_config,
            state_manager=state_manager,
            data_builder=data_builder,
            validator=stack_validator,
            repository=repository,
        )

    @property
    def stack(self):
        return self.state_manager.stack

    @property
    def old_stack(self):
        return self.state_manager.old_stack

    @property
    def state(self):
        return self.state_manager.state

    def run(self) -> None:

        self.validator.validate_args()

        stack_data = self.repository.get_stack()

        # Getting stack details from existing stack to allow
        # delete/update operations without requiring them
        if stack_data:
            self.state_manager.update_state(stack_data)
            self.state_manager.set_old_stack(stack_data)

        states_mapping = {
            "present": self.ensure_present,
            "absent": self.ensure_absent,
            "redeployed": self.ensure_redeployed,
            "started": self.ensure_started,
            "stopped": self.ensure_stopped,
        }

        state_function = states_mapping.get(self.state)

        if state_function is None:
            self.module.fail_json(
                msg=f"Internal error: state '{self.state}' is not mapped. "
                f"This is a bug in the module - please report it."
            )

        state_function()

        self.module.warn(f"New Stack: {self.stack}")

        self.results["stack"] = self.stack.to_dict()

        if not self.results["stack"]:
            self.results["stack"] = {
                PF.STACK_ID: self.state_manager.stack_id,
                PF.STACK_ENDPOINT_ID: self.state_manager.endpoint_id,
                PF.STACK_SWARM_ID: self.state_manager.swarm_id,
                **self.data_builder.get_create_data(),
            }

        if self.module._diff:
            self.results["diff"] = self.idempotency.build_diff(
                before_data=self.old_stack.to_dict(),
                after_data=self.results["stack"],
                skip_fields=self.config.skip_fields_from_changes,
            )

    def ensure_present(self) -> None:
        if self.stack.id:
            changed, changes = self.needs_update()

            if not changed:
                self.results["msg"] = "Stack already exists with correct configuration."
                return

            if not self.check_mode:
                self.repository.update_stack()
            else:
                self.state_manager.update_state(changes)

            self.results["changed"] = True
            self.results["msg"] = "Stack updated."

        else:
            if not self.check_mode:
                self.repository.create_stack()

            self.results["changed"] = True
            self.results["msg"] = "Stack created."

    def ensure_absent(self) -> None:
        if self.stack.id:
            if not self.check_mode:
                self.repository.delete_stack()

            self.results["changed"] = True
            self.results["msg"] = "Stack deleted"

        else:
            self.results["msg"] = "Stack does not exist"

    def ensure_redeployed(self) -> None:
        if self.stack.id:

            if not self.check_mode:
                if self.state_manager.stack_source == "repository":
                    self.repository.redeploy_stack()
                else:
                    self.repository.update_stack()

            self.results["changed"] = True
            self.results["msg"] = "Stack redeployed."

        else:
            self.module.fail_json(msg="Cannot redeploy an inexistent stack.")

    def ensure_started(self) -> None:
        if not self.stack.id:
            self.module.fail_json(msg="Cannot start a non-existent stack.")

        if self.stack.status == StackStatus.RUNNING:
            self.results["msg"] = "Stack is already running"
            self.results["changed"] = False
            return

        if not self.check_mode:
            self.repository.start_stack()

        self.results["msg"] = "Stack started"
        self.results["changed"] = True

    def ensure_stopped(self) -> None:
        if not self.stack.id:
            self.module.fail_json(msg="Cannot stop a non-existent stack.")

        if self.stack.status == StackStatus.STOPPED:
            self.results["msg"] = "Stack is not running"
            self.results["changed"] = False
            return

        if not self.check_mode:
            self.repository.stop_stack()

        self.results["msg"] = "Stack stopped"
        self.results["changed"] = True

    def needs_update(
        self, old_data: dict | None = None, new_data: dict | None = None
    ) -> tuple[bool, dict]:

        old_data = old_data or self.old_stack.to_dict()
        new_data = new_data or self.data_builder.get_update_data()

        is_repository = self.state_manager.stack_source == "repository"

        changes = self.idempotency.needs_update(
            existing_data=old_data,
            new_data=new_data,
            skip_fields=self.config.skip_fields_from_changes,
        )

        if is_repository and self.state_manager.update_password:
            # Always marking task as changed and sending an update
            # when update_password for repository stacks is true
            return True, changes

        return bool(changes), changes


def main():

    argument_spec = PortainerModule.generate_argspec(
        name=dict(type="str"),
        stack_id=dict(type="int"),
        stack_type=dict(
            type="str",
            choices=[
                # "kubernetes", # I will not support kubernetes for now. Out of my expertise and needs.
                "swarm",
                "standalone",
            ],
        ),
        stack_source=dict(type="str", choices=["file", "repository"]),
        state=dict(
            type="str",
            default="present",
            choices=["present", "absent", "redeployed", "stopped", "started"],
        ),
        swarm_id=dict(type="str"),
        env=dict(type="list", elements="dict"),
        endpoint_id=dict(type="int"),
        prune=dict(type="bool", default=None),
        pull_images=dict(type="bool", default=None),
        #
        # Swarm Stack Repository args
        #
        additional_files=dict(type="list", elements="str", default=None),
        autoupdate=dict(type="dict", default=None),
        compose_file=dict(type="str", default=None),
        repository_authentication=dict(type="bool", default=None),
        repository_password=dict(type="str", no_log=True, default=None),
        update_password=dict(type="bool", default=False, no_log=True),
        refs_name=dict(type="str", default=None),
        repository_url=dict(type="str", default=None),
        repository_username=dict(type="str", default=None),
        tls_skip_verify=dict(type="bool", default=None),
        #
        # Swarm Stack File args
        #
        file=dict(type="path"),
    )

    module = PortainerModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_if=[
            ("state", "present", ("stack_source", "stack_type")),
            ("state", "present", ("stack_id", "name"), True),
        ],
    )

    module.run_checks()

    try:
        results = dict(changed=False)

        stack_type = module.params["stack_type"]
        stack_source = module.params["stack_source"]

        manager = StackManager.for_stack(
            module, results, stack_type=stack_type, stack_source=stack_source
        )
        manager.run()

        module.exit_json(**results)

    except module.client.exc.PortainerApiError as e:
        module.fail_json(
            msg=f"API request failed: {e}",
            status=e.status,
            body=e.body,
            url=e.url,
            method=e.method,
            data=e.data,
        )

    except Exception as e:
        module.fail_json(msg=f"Error managing stacks: {str(e)}")


if __name__ == "__main__":
    main()
