#!/usr/bin/python
# portainer_network.py - A module to manage Portainer environment networks.
# Author: Igor Moraru (@bgtor)
# License: GPL-3.0-or-later
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function, annotations

__metaclass__ = type

DOCUMENTATION = r"""
---
module: portainer_network
short_description: Manage Portainer environment networks
description:
    - Create, update or delete environment networks
version_added: "1.0.0"
author: Igor Moraru (@bgtor)
options:
    endpoint_id:
        description: Id of the environment that this network is associated with
        type: int
        required: true
    name:
        description: Name of the network
        type: str
    network_id:
        description: ID of the network
        type: int
    driver:
        description: Network driver to use
        type: str
        default: bridge
        choices: ['bridge', 'overlay']
    scope:
        description: Network scope
        type: str
        choices: ['swarm', 'global', 'local']
        default: null
    attachable:
        description: Either the network is attachable
        type: bool
        default: null
    internal:
        description: Restrict external access to the network.
        type: bool
        default: null
    ingress:
        description: Ingress network is the network which provides the routing-mesh in swarm mode
        type: bool
        default: null
    state:
        description: Desired state of the network
        type: str
        choices: ['present', 'absent']
        default: present
    force:
        description: Either to force recreate the network
        type: bool
        default: false
extends_documentation_fragment:
    - bgtor.portainer.portainer_client
"""

EXAMPLES = r"""
- name: Create a network
  portainer_network:
    portainer_url: https://portainer.example.com
    portainer_token: "{{ portainer_api_token }}"
    name: mynetwork
    state: present

- name: Remove a network
  portainer_network:
    portainer_url: https://portainer.example.com
    portainer_token: "{{ portainer_api_token }}"
    name: mynetwork
    state: absent
"""

RETURN = r"""
network:
    description: network information
    returned: when state is present
    type: dict
    sample: {
        "Id": 1,
        "Name": "mynetwork",
    }
msg:
    description: Human readable message
    returned: always
    type: str
    sample: "network mynetwork created successfully"
"""

import copy

from typing import Any

from ..module_utils.portainer_fields import PortainerFields as PF
from ..module_utils.portainer_module import PortainerModule


class PortainerNetworkManager:
    def __init__(self, module: PortainerModule, results: dict):
        self.module = module
        self.crud = self.module.crud
        self.idempotency = module.idempotency

        self.results = results
        self.check_mode = module.check_mode
        self.diff_mode = module._diff

        self.name = module.params["name"]
        self.network_id = module.params["network_id"]
        self.endpoint_id = module.params["endpoint_id"]
        self.driver = module.params["driver"]
        self.state = module.params["state"]
        self.force = module.params["force"]
        self.scope = module.params["scope"]
        self.internal = module.params["internal"]
        self.attachable = module.params["attachable"]
        self.ingress = module.params["ingress"]

        self.network = {}
        self.old_network = {}

    def __call__(self) -> None:
        self.network = self.get_network() or {}
        self.old_network = copy.deepcopy(self.network)

        states_mapping = {
            "present": self.ensure_present,
            "absent": self.ensure_absent,
        }

        state_function = states_mapping.get(self.state)

        if state_function is None:
            self.module.fail_json(
                msg=f"Internal error: state '{self.state}' is not mapped. "
                f"This is a bug in the module - please report it."
            )

        state_function()

        self.results["network"] = self.network or self._get_network_data()

        if self.diff_mode:
            self.results["diff"] = self.idempotency.build_diff(
                before_data=self.old_network,
                after_data=self.results["network"],
            )

    def ensure_present(self) -> None:
        if self.network:
            changes = self.idempotency.needs_update(
                existing_data=self.network, new_data=self._get_network_data()
            )
            if not changes:
                self.results["msg"] = "Network already exists."
                return

            if not self.force:
                self.module.warn(
                    "The content of the network was not updated. "
                    "In order to recreate the network use force: true."
                )
                self.results["msg"] = (
                    "The content of the network was not updated. "
                    "In order to recreate the network use force: true."
                )
                return

            if not self.check_mode:
                self.ensure_absent()
                self.create_network()

            self.results["changed"] = True
            self.results["msg"] = "Network updated."

        else:
            if not self.check_mode:
                self.create_network()

            self.results["changed"] = True
            self.results["msg"] = "Network created."

    def ensure_absent(self) -> None:
        if self.network:
            if not self.check_mode:
                self.delete_network()

            self.results["changed"] = True
            self.results["msg"] = "Network deleted"
        else:
            self.results["msg"] = "Network does not exists"

    def _get_network_data(self) -> dict[str, Any]:
        """
        Prepare network data for Portainer API.

        Returns dict with network name and base64-encoded data.
        """
        data = {
            PF.NETWORK_NAME: self.name,
            PF.NETWORK_DRIVER: self.driver,
            PF.NETWORK_INTERNAL: self.internal,
            PF.NETWORK_ATTACHABLE: self.attachable,
            PF.NETWORK_SCOPE: self.scope,
            PF.NETWORK_INGRESS: self.ingress,
        }

        return {k: v for k, v in data.items() if v is not None}

    def get_network(self) -> dict[str, Any] | None:
        """Get network by name or id, validating uniqueness."""
        if self.network_id:
            return self.crud.docker_network.get_item_by_id(self.network_id)

        return self.crud.docker_network.validate_single_item(name=self.name, operation="retrieve")

    def create_network(self) -> None:

        network_data = self._get_network_data()

        self.network = self.crud.docker_network.create_item(self.name, item_data=network_data)

    def delete_network(self) -> None:

        if not self.network:
            return None

        network_id = self.network[PF.NETWORK_ID]

        self.crud.docker_network.delete_item_by_id(network_id)


def main():
    argument_spec = PortainerModule.generate_argspec(
        endpoint_id=dict(type="int", required=True),
        name=dict(type="str"),
        network_id=dict(type="int"),
        driver=dict(type="str", choices=["bridge", "overlay"], default="bridge"),
        scope=dict(type="str", choices=["swarm", "global", "local"], default=None),
        attachable=dict(type="bool", default=None),
        internal=dict(type="bool", default=None),
        ingress=dict(type="bool", default=None),
        state=dict(type="str", default="present", choices=["present", "absent"]),
        force=dict(type="bool", default=False),
    )

    module = PortainerModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    module.run_checks()

    try:
        results = dict(changed=False)

        PortainerNetworkManager(module, results)()
        module.exit_json(**results)

    except module.client.exc.PortainerApiError as e:
        module.fail_json(
            msg=f"API request failed: {e}",
            status=e.status,
            body=e.body,
            url=e.url,
            method=e.method,
        )

    except Exception as e:
        module.fail_json(msg=f"Error managing networks: {str(e)}")


if __name__ == "__main__":
    main()
