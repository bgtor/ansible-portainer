#!/usr/bin/python
# portainer_tag.py - A module to manage Portainer tags.
# Author: Igor Moraru (@bgtor)
# License: GPL-3.0-or-later
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function, annotations

__metaclass__ = type

DOCUMENTATION = r"""
---
module: portainer_tag
short_description: Manage Portainer tags
description:
    - Create, update or delete tags
version_added: "1.0.0"
author: Igor Moraru (@bgtor)
options:
    name:
        description: Name of the tag
        type: str
    tag_id:
        description: ID of the tag
        type: int
    state:
        description: Desired state of the tag
        type: str
        choices: ['present', 'absent']
        default: present
extends_documentation_fragment:
    - bgtor.portainer.portainer_client
"""

EXAMPLES = r"""
- name: Create a tag
  portainer_tag:
    portainer_url: https://portainer.example.com
    portainer_token: "{{ portainer_api_token }}"
    name: mytag
    state: present

- name: Remove a tag
  portainer_stack:
    portainer_url: https://portainer.example.com
    portainer_token: "{{ portainer_api_token }}"
    name: mytag
    state: absent
"""

RETURN = r"""
tag:
    description: Tag information
    returned: when state is present
    type: dict
    sample: {
        "Id": 1,
        "Name": "mytag",
    }
msg:
    description: Human readable message
    returned: always
    type: str
    sample: "Tag mytag created successfully"
"""

import copy

from typing import Any

from ..module_utils.portainer_fields import PortainerFields as PF
from ..module_utils.portainer_module import PortainerModule


class PortainerTagManager:
    def __init__(self, module: PortainerModule, results: dict[str, Any]):
        self.module = module
        self.crud = self.module.crud
        self.idempotency = module.idempotency

        self.state = module.params["state"]
        self.results = results
        self.check_mode = module.check_mode
        self.diff_mode = module._diff

        self.name = module.params["name"]
        self.tag_id = module.params["tag_id"]

        self.tag = {}
        self.old_tag = {}

    def __call__(self) -> None:
        self.tag = self.get_tag() or {}
        self.old_tag = copy.deepcopy(self.tag)

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

        self.results["tag"] = self.tag or {PF.TAG_NAME: self.name}

        if self.diff_mode:
            self.results["diff"] = self.idempotency.build_diff(
                before_data=self.old_tag,
                after_data=self.results["tag"],
            )

    def ensure_present(self) -> None:
        if self.tag:
            self.results["msg"] = "Tag already exists"
        else:
            if not self.check_mode:
                self.create_tag()

            self.results["changed"] = True
            self.results["msg"] = "Tag created"

    def ensure_absent(self) -> None:
        if self.tag:
            if not self.check_mode:
                self.delete_tag()

            self.results["changed"] = True
            self.results["msg"] = "Tag deleted"

        else:
            self.results["msg"] = "Tag does not exist"

    def get_tag(self) -> dict[str, Any] | None:
        """Get tag by name or id, validating uniqueness."""
        if self.tag_id:
            return self.crud.tag.get_item_by_id(self.tag_id)

        return self.crud.tag.validate_single_item(name=self.name, operation="retrieve")

    def create_tag(self) -> None:

        tag_data = {PF.TAG_NAME: self.name}

        self.tag = self.crud.tag.create_item(self.name, item_data=tag_data)

    def delete_tag(self) -> None:
        """Delete tag by ID."""
        if not self.tag:
            return

        self.crud.tag.delete_item_by_id(self.tag[PF.TAG_ID])


def main():
    argument_spec = PortainerModule.generate_argspec(
        name=dict(type="str"),
        tag_id=dict(type="int"),
        state=dict(type="str", default="present", choices=["present", "absent"]),
    )

    module = PortainerModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[("tag_id", "name")],
    )

    module.run_checks()

    try:
        results = dict(changed=False)

        PortainerTagManager(module, results)()

        module.exit_json(**results)

    except module.client.exc.PortainerApiError as e:
        module.fail_json(
            msg=f"API request failed: {e}",
            status=e.status,
            body=e.body,
        )

    except Exception as e:
        module.fail_json(msg=f"Error managing tag: {str(e)}")


if __name__ == "__main__":
    main()
