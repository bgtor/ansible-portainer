#!/usr/bin/python
# portainer_config.py - A module to manage Portainer environment configs.
# Author: Igor Moraru (@bgtor)
# License: GPL-3.0-or-later
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function, annotations

__metaclass__ = type

DOCUMENTATION = r"""
---
module: portainer_config
short_description: Manage Portainer environment configs
description:
    - Create, update or delete environment configs
version_added: "1.0.0"
author: Igor Moraru (@bgtor)
options:
    endpoint_id:
        description: Id of the environment that this config is associated with
        type: int
        required: true
    name:
        description: Name of the config
        type: str
    config_id:
        description: ID of the config
        type: int
    file:
        description: File path of the file with the content of the config
        type: path
    content:
        description: Content of the config
        type: str
    b64_encoded:
        description: Flag to indicate that the string content is base64 encoded
        type: bool
        default: false
    force:
        description: Force recreate the config
        type: bool
        default: false
    state:
        description: Desired state of the config
        type: str
        choices: ['present', 'absent']
        default: present
extends_documentation_fragment:
    - bgtor.portainer.portainer_client
"""

EXAMPLES = r"""
- name: Create a config
  portainer_config:
    portainer_url: https://portainer.example.com
    portainer_token: "{{ portainer_api_token }}"
    name: myconfig
    state: present

- name: Remove a config
  portainer_config:
    portainer_url: https://portainer.example.com
    portainer_token: "{{ portainer_api_token }}"
    name: myconfig
    state: absent
"""

RETURN = r"""
config:
    description: config information
    returned: when state is present
    type: dict
    sample: {
        "Id": 1,
        "Name": "myconfig",
        "TagIds": [1, 2]
    }
msg:
    description: Human readable message
    returned: always
    type: str
    sample: "config myconfig created successfully"
"""
import base64
import copy

from typing import Any

from ..module_utils.portainer_fields import PortainerFields as PF
from ..module_utils.portainer_module import PortainerModule


class PortainerConfigManager:
    def __init__(self, module: PortainerModule, results: dict) -> None:
        self.module = module
        self.crud = self.module.crud
        self.idempotency = module.idempotency

        self.results = results
        self.check_mode = module.check_mode
        self.diff_mode = module._diff

        self.name = module.params["name"]
        self.config_id = module.params["config_id"]
        self.file = module.params["file"]
        self.content: str | None = module.params["content"]
        self.b64_encoded = module.params["b64_encoded"]
        self.endpoint_id = module.params["endpoint_id"]
        self.force = module.params["force"]
        self.state = module.params["state"]

        self.config = {}
        self.old_config = {}

    def __call__(self) -> None:
        self.config = self.get_config()
        self.old_config = copy.deepcopy(self.config)

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

        self.results["config"] = self.config or self._get_config_data()

        if self.diff_mode:
            self.results["diff"] = self.idempotency.build_diff(
                before_data=self.old_config, after_data=self.results["config"]
            )

    def ensure_present(self) -> None:
        if self.config:
            changes = self.idempotency.needs_update(
                existing_data=self.config, new_data=self._get_config_data()
            )

            if not changes:
                self.results["msg"] = "Config already exists."
                return

            if not self.force:
                self.module.warn(
                    "The content of the config was not updated. "
                    "In order to recreate the config use force: true."
                )
                self.results["msg"] = "Config already exists. Update skipped."
                return

            if not self.check_mode:
                self.ensure_absent()
                self.config = self.create_config()

            self.results["changed"] = True
            self.results["msg"] = "Config updated."

        else:
            if not self.check_mode:
                self.config = self.create_config()

            self.results["changed"] = True
            self.results["msg"] = "Config created."

    def ensure_absent(self) -> None:
        if self.config:
            if not self.check_mode:
                self.delete_config(config_id=self.config[PF.CONFIG_ID])
                self.config = {}

            self.results["changed"] = True
            self.results["msg"] = "Config deleted"
        else:
            self.results["msg"] = "Config does not exists"

    def _get_config_data(self) -> dict[str, Any]:
        """
        Prepare config data for Portainer API.

        Returns dict with config name and base64-encoded data.
        """
        data = {
            PF.CONFIG_NAME: self.name,
        }

        if not self.content and not self.file:
            return data

        # Get raw config content
        raw_content = self._get_raw_content()

        if not raw_content:
            self.module.fail_json(msg="Couldn't get config data.")

        # Handle base64 encoding
        if self.b64_encoded:
            # Content is already base64 encoded
            data[PF.CONFIG_DATA] = raw_content
        else:
            # Encode content to base64
            data[PF.CONFIG_DATA] = base64.b64encode(raw_content.encode("utf-8")).decode("utf-8")

        return data

    def _get_raw_content(self) -> str | None:
        """
        Get raw config content from either 'content' or 'file' parameter.

        Returns the raw content as a string.
        """
        if self.content:
            return self.content

        elif self.file:
            file_path = self.module.params["file"]
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Validate content is not empty
                if not content:
                    self.module.fail_json(msg=f"File is empty: {file_path}")

                return content

            except FileNotFoundError:
                self.module.fail_json(msg=f"File not found: {file_path}")
            except PermissionError:
                self.module.fail_json(msg=f"Permission denied reading file: {file_path}")
            except UnicodeDecodeError:
                self.module.fail_json(
                    msg=f"File contains binary data and cannot be read as text: {file_path}. "
                    f"This module only supports text-based configs."
                )
            except IOError as e:
                self.module.fail_json(msg=f"Failed to read file {file_path}: {str(e)}")

    def get_config(self):
        """Get config by name or id, validating uniqueness."""
        if self.config_id:
            return self.crud.swarm_config.get_item_by_id(self.config_id)

        return self.crud.swarm_config.validate_single_item(name=self.name, operation="retrieve")

    def create_config(self):

        if not self.check_mode:
            config_data = self._get_config_data()

            return self.crud.swarm_config.create_item(self.name, item_data=config_data)

    def delete_config(self, config_id):
        """Delete config by ID."""

        if not self.check_mode:
            return self.crud.swarm_config.delete_item_by_id(config_id)


def main():
    argument_spec = PortainerModule.generate_argspec(
        endpoint_id=dict(type="int", required=True),
        name=dict(type="str"),
        config_id=dict(type="int"),
        file=dict(type="path"),
        content=dict(type="str", no_log=True),
        b64_encoded=dict(type="bool", default=False),
        state=dict(type="str", default="present", choices=["present", "absent"]),
        force=dict(type="bool", default=False),
    )

    module = PortainerModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        mutually_exclusive=[("file", "content")],
        required_if=[("state", "present", ("file", "content"), True)],
    )

    module.run_checks()

    try:
        results = dict(changed=False)

        PortainerConfigManager(module, results)()

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
        module.fail_json(msg=f"Error managing config: {str(e)}")


if __name__ == "__main__":
    main()
