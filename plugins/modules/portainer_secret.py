#!/usr/bin/python
# portainer_secret.py - A module to manage Portainer environment secrets.
# Author: Igor Moraru (@bgtor)
# License: GPL-3.0-or-later
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function, annotations

__metaclass__ = type

DOCUMENTATION = r"""
---
module: portainer_secret
short_description: Manage Portainer environment secrets
description:
    - Create, update or delete environment secrets
version_added: "1.0.0"
author: Igor Moraru (@bgtor)
options:
    endpoint_id:
        description: Id of the environment that this secret is associated with
        type: int
        required: true
    name:
        description: Name of the secret
        type: str
    secret_id:
        description: ID of the secret
        type: int
    file:
        description: File path of the file with the content of the secret
        type: path
    content:
        description: Content of the secret
        type: str
    b64_encoded:
        description: Flag to indicate that the string content is base64 encoded
        type: bool
        default: false
    force:
        description: Force recreate the secret
        type: bool
        default: false
    state:
        description: Desired state of the secret
        type: str
        choices: ['present', 'absent']
        default: present
extends_documentation_fragment:
    - bgtor.portainer.portainer_client
"""

EXAMPLES = r"""
- name: Create a secret
  portainer_secret:
    portainer_url: https://portainer.example.com
    portainer_token: "{{ portainer_api_token }}"
    name: mysecret
    state: present

- name: Remove a secret
  portainer_secret:
    portainer_url: https://portainer.example.com
    portainer_token: "{{ portainer_api_token }}"
    name: mysecret
    state: absent
"""

RETURN = r"""
secret:
    description: secret information
    returned: when state is present
    type: dict
    sample: {
        "Id": 1,
        "Name": "mysecret",
        "TagIds": [1, 2]
    }
msg:
    description: Human readable message
    returned: always
    type: str
    sample: "secret mysecret created successfully"
"""

import copy
import base64

from typing import Any

from ..module_utils.portainer_fields import PortainerFields as PF
from ..module_utils.portainer_module import PortainerModule


class PortainerSecretManager:
    def __init__(self, module: PortainerModule, results: dict):
        self.module = module
        self.crud = self.module.crud
        self.idempotency = module.idempotency

        self.results = results
        self.check_mode = module.check_mode
        self.diff_mode = module._diff

        self.state = module.params["state"]
        self.name = module.params["name"]
        self.secret_id = module.params["secret_id"]
        self.file = module.params["file"]
        self.content: str | None = module.params["content"]
        self.b64_encoded = module.params["b64_encoded"]
        self.endpoint_id = module.params["endpoint_id"]
        self.force = module.params["force"]

        self.secret = {}
        self.old_secret = {}

    def __call__(self) -> None:

        self.secret = self.get_secret() or {}
        self.old_secret = copy.deepcopy(self.secret)

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

        self.results["secret"] = self.secret or self._get_secret_data()

        if self.diff_mode:
            self.results["diff"] = self.idempotency.build_diff(
                before_data=self.old_secret,
                after_data=self.results["secret"],
            )

    def ensure_present(self) -> None:
        if self.secret:
            if not self.force:
                self.module.warn(
                    "The content of the secret was not updated. "
                    "In order to recreate the secret use force: true."
                )
                self.results["msg"] = (
                    "The content of the secret was not updated. "
                    "In order to recreate the secret use force: true."
                )
                return

            if not self.check_mode:
                self.ensure_absent()
                self.create_secret()

            self.results["changed"] = True
            self.results["msg"] = "Secret updated."

        else:
            if not self.check_mode:
                self.create_secret()

            self.results["changed"] = True
            self.results["msg"] = "Secret created."

    def ensure_absent(self) -> None:
        if self.secret:
            if not self.check_mode:
                self.delete_secret()

            self.results["changed"] = True
            self.results["msg"] = "Secret deleted"
        else:
            self.results["msg"] = "Secret does not exists"

    def _get_secret_data(self) -> dict[str, Any]:
        """
        Prepare secret data for Portainer API.

        Returns dict with secret name and base64-encoded data.
        """
        data = {
            PF.SECRET_NAME: self.name,
        }

        if not self.content and not self.file:
            return data

        # Get raw secret content
        raw_content = self._get_raw_content()

        if not raw_content:
            self.module.fail_json(msg="Couldn't get secret data.")

        # Handle base64 encoding
        if self.b64_encoded:
            # Content is already base64 encoded
            data[PF.SECRET_DATA] = raw_content
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
            try:
                with open(self.file, "r", encoding="utf-8") as f:
                    content = f.read()

                # Validate content is not empty
                if not content:
                    self.module.fail_json(msg=f"File is empty: {self.file}")

                return content

            except FileNotFoundError:
                self.module.fail_json(msg=f"File not found: {self.file}")
            except PermissionError:
                self.module.fail_json(msg=f"Permission denied reading file: {self.file}")
            except UnicodeDecodeError:
                self.module.fail_json(
                    msg=f"File contains binary data and cannot be read as text: {self.file}. "
                    f"This module only supports text-based configs."
                )
            except IOError as e:
                self.module.fail_json(msg=f"Failed to read file {self.file}: {str(e)}")

    def get_secret(self) -> dict[str, Any] | None:
        """Get secret by name or id, validating uniqueness."""
        if self.secret_id:
            return self.crud.swarm_secret.get_item_by_id(self.secret_id)

        return self.crud.swarm_secret.validate_single_item(name=self.name, operation="retrieve")

    def create_secret(self) -> None:

        secret_data = self._get_secret_data()

        self.secret = self.crud.swarm_secret.create_item(self.name, item_data=secret_data)

    def delete_secret(self) -> None:

        if not self.secret:
            return None

        secret_id = self.secret[PF.SECRET_ID]

        self.crud.swarm_secret.delete_item_by_id(secret_id)


def main():
    argument_spec = PortainerModule.generate_argspec(
        endpoint_id=dict(type="int", required=True),
        name=dict(type="str"),
        secret_id=dict(type="int"),
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

        PortainerSecretManager(module, results)()
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
        module.fail_json(msg=f"Error managing secrets: {str(e)}")


if __name__ == "__main__":
    main()
