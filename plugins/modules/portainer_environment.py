#!/usr/bin/python
# portainer_environment.py - A module to manage Portainer environments.
# Author: Igor Moraru (@bgtor)
# License: GPL-3.0-or-later
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function, annotations

__metaclass__ = type

DOCUMENTATION = r"""
---
module: portainer_environment
short_description: Manage Portainer environments
description:
    - Create, update or delete Portainer environments
version_added: "1.0.0"
author: Igor Moraru (@bgtor)
options:
    name:
        description: Name of the environment
        type: str
        default: null
    creation_type:
        description: >-
            Environment(Endpoint) type. Value must be one of: 1 (Local Docker environment),
            2 (Agent environment), 3 (Azure environment), 4 (Edge agent environment) or
            5 (Local Kubernetes Environment)
        type: int
    url:
        description: >-
            URL or IP address of a Docker host (example: docker.mydomain.tld:2375).
            Defaults to local if not specified (Linux: /var/run/docker.sock,
            Windows: //./pipe/docker_engine). Cannot be empty if EndpointCreationType
            is set to 4 (Edge agent environment)
        type: str
    tls:
        description: Require TLS to connect against this environment(endpoint). Must be true if EndpointCreationType is set to 2 (Agent environment)
        type: bool
    edge_check_in_interval:
        description: The check in interval for edge agent (in seconds)
        type: int
    edge_tunnel_server_address:
        description: URL or IP address that will be used to establish a reverse tunnel
        type: str
    endpoint_id:
        description: ID of the environment
        type: int
    group:
        description: Name of group to associate environment with
        type: str
    create_group:
        description: Flag that allows creation of missing group
        type: bool
        default: false
    tags:
        description: Name of tags to associate environment with
        type: list
        elements: str
    create_tags:
        description: Flag that allows creation of missing tags
        type: bool
        default: false
    state:
        description: Desired state of the stack
        type: str
        choices: ['present', 'absent', 'healthy']
        default: present
    timeout:
        description: Timeout in seconds for achieving the desired state. Currently applied only for the 'healthy' state
        type: int
        default: 30
extends_documentation_fragment:
    - bgtor.portainer.portainer_client
"""

EXAMPLES = r"""
- name: Create an environment
  portainer_environment:
    portainer_url: https://portainer.example.com
    portainer_token: "{{ portainer_api_token }}"
    name: myenvironment
    state: present

- name: Remove an environment
  portainer_environment:
    portainer_url: https://portainer.example.com
    portainer_token: "{{ portainer_api_token }}"
    name: myenvironment
    state: absent
"""

RETURN = r"""
environment:
    description: environment information
    returned: when state is present
    type: dict
    sample: {
        "Id": 1,
        "Name": "myenvironment",
        "Status": 1
    }
msg:
    description: Human readable message
    returned: always
    type: str
    sample: "Environment myenvironment created successfully"
"""
import copy

from time import sleep, time
from typing import Any

from ..module_utils.portainer_module import PortainerModule
from ..module_utils.portainer_fields import PortainerFields as PF
from ..module_utils.portainer_client import BodyFormat


class PortainerEnvironmentManager:

    create_only_keys = [
        PF.ENDPOINT_CREATION_TYPE,
        PF.ENDPOINT_EDGE_TUNNEL_SERVER_ADDRESS,
    ]

    def __init__(self, module: PortainerModule, results: dict[str, Any]):
        self.module = module
        self.crud = module.crud
        self.idempotency = module.idempotency

        self.results = results
        self.state = module.params["state"]
        self.check_mode = module.check_mode
        self.diff_mode = module._diff

        self.name = module.params["name"]
        self.endpoint_id = module.params["endpoint_id"]
        self.creation_type = module.params["creation_type"]
        self.url = module.params["url"]
        self.tls = module.params["tls"]
        self.edge_check_in_interval = module.params["edge_check_in_interval"]
        self.edge_tunnel_server_address = module.params["edge_tunnel_server_address"]
        self.timeout = module.params["timeout"]
        self.group = self.module.params["group"]
        self.tags = self.module.params["tags"]
        self.create_group = self.module.params["create_group"]
        self.create_tags = self.module.params["create_tags"]

        self.group_id = None
        self.tag_ids = set()

        self.environment = {}
        self.old_environment = {}

    def __call__(self) -> None:
        self._get_group_id()
        self._get_tag_ids()

        self.environment = self.get_environment() or {}
        self.old_environment = copy.deepcopy(self.environment)

        states_mapping = {
            "present": self.ensure_present,
            "absent": self.ensure_absent,
            "healthy": self.ensure_healthy,
        }

        state_function = states_mapping.get(self.state)

        if state_function is None:
            self.module.fail_json(
                msg=f"Internal error: state '{self.state}' is not mapped. "
                f"This is a bug in the module - please report it."
            )

        state_function()

        self.results["environment"] = self.environment or self._get_environment_data()

        if self.diff_mode:
            self.results["diff"] = self.idempotency.build_diff(
                before_data=self.old_environment,
                after_data=self.results["environment"],
            )

    def ensure_present(self) -> None:
        if self.environment:

            changes = self.needs_update()
            if not changes:
                self.results["msg"] = "Environment already exists with correct configuration"
                return

            if not self.check_mode:
                self.update_environment()

            self.results["changed"] = True
            self.results["msg"] = f"Environment updated: {', '.join(changes.keys())}"

        else:
            if not self.check_mode:
                self.create_environment()

            self.results["changed"] = True
            self.results["msg"] = "Environment created"

    def ensure_absent(self) -> None:
        if self.environment:
            if not self.check_mode:
                self.delete_environment()

            self.results["changed"] = True
            self.results["msg"] = f"Environment {self.module.params['name']} deleted"

        else:
            self.results["msg"] = f"Environment {self.module.params['name']} does not exist"

    def ensure_healthy(self) -> None:
        if self.environment:
            if not self.check_mode:
                self.wait_for_heartbeat()
            self.results["msg"] = f"Environment {self.module.params['name']} is healthy"

        else:
            self.module.fail_json(
                msg=f"Environment {self.module.params['name']} does not exist",
            )

    def _get_group_id(self) -> None:
        if not self.group:
            return

        self.group_id = self.crud.group.resolve_name_to_id(
            name=self.group, create_flag="create_group"
        )

    def _get_tag_ids(self) -> None:

        if not self.tags:
            return

        for tag_name in self.tags:
            tag_id = self.crud.tag.resolve_name_to_id(name=tag_name, create_flag="create_tags")
            self.tag_ids.add(tag_id)

    def get_environment(self) -> dict[str, Any] | None:
        if self.endpoint_id:
            return self.crud.environment.get_item_by_id(self.endpoint_id)

        return self.crud.environment.validate_single_item(name=self.name, operation="retrieve")

    def _get_environment_data(self, exclude_keys: list[str] | None = None):
        exclude_keys = [] if exclude_keys is None else exclude_keys

        data = {
            PF.ENDPOINT_NAME: self.name,
            PF.ENDPOINT_CREATION_TYPE: self.creation_type,
            PF.ENDPOINT_URL: self.url,
            PF.ENDPOINT_TLS: self.tls,
            PF.ENDPOINT_EDGE_CHECKIN_INTERVAL: self.edge_check_in_interval,
            PF.ENDPOINT_EDGE_TUNNEL_SERVER_ADDRESS: self.edge_tunnel_server_address,
            PF.ENDPOINT_GROUP_ID: self.group_id,
            PF.ENDPOINT_TAG_IDS: list(self.tag_ids),
        }
        new_data = {k: v for k, v in data.items() if v is not None and k not in exclude_keys}

        merged = {**self.old_environment, **new_data}

        return {k: v for k, v in merged.items() if v is not None and k not in exclude_keys}

    def create_environment(self) -> None:

        self.environment = self.crud.environment.create_item(
            name=self.name, item_data=self._get_environment_data(), body_format=BodyFormat.FORM_DATA
        )

    def update_environment(self) -> None:

        if not self.environment:
            return

        self.environment = self.crud.environment.update_item(
            item_id=self.environment[PF.ENDPOINT_ID], changes=self._get_environment_data()
        )

    def delete_environment(self) -> None:
        if not self.environment:
            return

        self.crud.environment.delete_item(item_id=self.environment[PF.ENDPOINT_ID])

    def wait_for_heartbeat(self) -> bool:
        if not self.environment:
            return False

        start = time()
        while True:
            environment = self.crud.environment.get_item_by_id(self.environment[PF.ENDPOINT_ID])

            if environment.get(PF.ENDPOINT_HEARTBEAT):
                return True

            sleep(5)

            if (time() - start) > self.timeout:
                break

        self.module.fail_json(
            msg=f"Environment {environment[PF.ENDPOINT_NAME]} failed to achieve a healthy status."
        )

    def needs_update(self) -> dict[str, Any]:
        """Check if existing environment needs updates."""

        if not self.environment:
            return {}

        exclude_keys = [*self.create_only_keys]

        if not self.environment.get(PF.ENDPOINT_HEARTBEAT):
            self.module.warn(
                f"Portainer environment {self.environment[PF.ENDPOINT_NAME]} is not yet activated. "
                + "Some keys related to edge Agent will not be updated."
            )
            exclude_keys.append(PF.ENDPOINT_URL)
            exclude_keys.append(PF.ENDPOINT_TLS)

        new_data = self._get_environment_data(exclude_keys=exclude_keys)

        return self.idempotency.needs_update(existing_data=self.environment, new_data=new_data)


def main():
    argument_spec = PortainerModule.generate_argspec(
        endpoint_id=dict(type="int", default=None),
        name=dict(type="str", default=None),
        group=dict(type="str", default=None),
        create_group=dict(type="bool", default=False),
        tags=dict(type="list", elements="str", default=None),
        create_tags=dict(type="bool", default=False),
        state=dict(type="str", default="present", choices=["present", "absent", "healthy"]),
        timeout=dict(type="int", default=30),
        creation_type=dict(type="int", default=None),
        url=dict(type="str", default=None),
        tls=dict(type="bool"),
        edge_check_in_interval=dict(type="int", default=None),
        edge_tunnel_server_address=dict(type="str", default=None),
    )

    module = PortainerModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_if=[
            ("creation_type", 4, ("url",)),
        ],
        required_one_of=[("endpoint_id", "name")],
    )

    module.run_checks()

    try:

        results = dict(changed=False)

        PortainerEnvironmentManager(module, results)()

        module.exit_json(**results)

    except module.client.exc.PortainerApiError as e:
        module.fail_json(
            msg=f"API request failed: {e}",
            status=e.status,
            body=e.body,
        )

    except Exception as e:
        module.fail_json(msg=f"Error managing environment: {str(e)}")


if __name__ == "__main__":
    main()
