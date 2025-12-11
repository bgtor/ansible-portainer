#!/usr/bin/python
# portainer_group.py - A module to manage Portainer environment groups.
# Author: Igor Moraru (@bgtor)
# License: GPL-3.0-or-later
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function, annotations

__metaclass__ = type

DOCUMENTATION = r"""
---
module: portainer_group
short_description: Manage Portainer environment groups
description:
    - Create, update or delete environment groups
version_added: "1.0.0"
author: Igor Moraru (@bgtor)
options:
    name:
        description: Name of the group
        type: str
    group_id:
        description: ID of the group
        type: int
    tag_ids:
        description: IDs of group tags
        type: list
        elements: int
    tags:
        description: Tag names to be assigned to group
        type: list
        elements: str
    create_tags:
        description: Flag to allow auto-creating inexistent tags
        type: bool
        default: false
    description:
        description: Description of the group
        type: str
    state:
        description: Desired state of the group
        type: str
        choices: ['present', 'absent']
        default: present
extends_documentation_fragment:
    - bgtor.portainer.portainer_client
"""

EXAMPLES = r"""
- name: Create a group
  portainer_group:
    portainer_url: https://portainer.example.com
    portainer_token: "{{ portainer_api_token }}"
    name: mygroup
    state: present

- name: Remove a group
  portainer_group:
    portainer_url: https://portainer.example.com
    portainer_token: "{{ portainer_api_token }}"
    name: mygroup
    state: absent
"""

RETURN = r"""
group:
    description: Group information
    returned: when state is present
    type: dict
    sample: {
        "Id": 1,
        "Name": "mygroup",
        "TagIds": [1, 2]
    }
msg:
    description: Human readable message
    returned: always
    type: str
    sample: "Group mygroup created successfully"
"""

import copy

from typing import Any

from ..module_utils.portainer_fields import PortainerFields as PF
from ..module_utils.portainer_module import PortainerModule


class PortainerGroupManager:
    def __init__(self, module: PortainerModule, results: dict):
        self.module = module
        self.crud = self.module.crud
        self.idempotency = module.idempotency

        self.state = self.module.params["state"]
        self.results = results
        self.diff_mode = self.module._diff
        self.check_mode = self.module.check_mode

        self.name = module.params["name"]
        self.group_id = module.params["group_id"]
        self.tag_ids = module.params["tag_ids"]
        self.tags = module.params["tags"]
        self.create_tags = module.params["create_tags"]
        self.description = module.params["description"]

        if self.tags and not self.tag_ids:
            self.tag_ids = self._resolve_tags()

        self.group = {}
        self.old_group = {}

    def __call__(self) -> None:
        self.group = self.get_group() or {}
        self.old_group = copy.deepcopy(self.group)

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

        self.results["group"] = self.group or self._get_group_data()

        if self.diff_mode:
            self.results["diff"] = self.idempotency.build_diff(
                before_data=self.old_group,
                after_data=self.results["group"],
            )

    def ensure_present(self) -> None:
        if self.group:
            changes = self.needs_update()
            if changes:
                if not self.check_mode:
                    self.update_group()

                self.results["changed"] = True
                self.results["msg"] = f"Group updated: {', '.join(changes.keys())}"
            else:
                self.results["msg"] = "Group already exists with correct configuration"
        else:
            if not self.check_mode:
                self.create_group()

            self.results["changed"] = True
            self.results["msg"] = "Group created"

    def ensure_absent(self) -> None:
        if self.group:
            if not self.check_mode:
                self.delete_group()

            self.results["changed"] = True
            self.results["msg"] = "Group deleted"

        else:
            self.results["msg"] = "Group does not exist"

    def _get_group_data(self) -> dict[str, Any]:

        data = {
            **(self.old_group or {}),
            PF.GROUP_NAME: self.name,
            PF.GROUP_DESCRIPTION: self.description,
            PF.GROUP_TAG_IDS: self.tag_ids,
        }

        return {k: v for k, v in data.items() if v is not None}

    def _resolve_tags(self) -> list[int]:
        """Convert tag names to tag IDs, creating tags if needed"""
        resolved_ids = []

        for tag_name in self.tags:
            tag_id = self.crud.tag.resolve_name_to_id(name=tag_name, create_flag="create_tags")

            resolved_ids.append(tag_id)

        return resolved_ids

    def get_group(self) -> dict[str, Any] | None:
        """Get group by name or id, validating uniqueness."""
        if self.group_id:
            return self.crud.group.get_item_by_id(self.group_id)

        return self.crud.group.validate_single_item(name=self.name, operation="retrieve")

    def create_group(self) -> None:

        group_data = self._get_group_data()

        self.group = self.crud.group.create_item(self.name, item_data=group_data)

    def update_group(self) -> None:
        """Update existing group by ID."""
        if not self.group:
            return

        self.group = self.crud.group.update_item(
            self.group[PF.GROUP_ID], changes=self._get_group_data()
        )

    def delete_group(self) -> None:
        """Delete group by ID."""
        if not self.group:
            return

        self.crud.group.delete_item_by_id(item_id=self.group[PF.GROUP_ID])

    def needs_update(self) -> dict[str, Any]:
        """Check if existing group needs updates."""
        if not self.old_group:
            return {}

        new_data = self._get_group_data()

        return self.idempotency.needs_update(existing_data=self.old_group, new_data=new_data)


def main():
    argument_spec = PortainerModule.generate_argspec(
        name=dict(type="str"),
        group_id=dict(type="int"),
        description=dict(type="str"),
        state=dict(type="str", default="present", choices=["present", "absent"]),
        tags=dict(type="list", elements="str", default=None),
        tag_ids=dict(type="list", elements="int", default=None),
        create_tags=dict(type="bool", default=False),
    )

    module = PortainerModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        mutually_exclusive=[("tags", "tag_ids")],
        required_if=[("create_tags", True, ("tags",))],
        required_one_of=[("group_id", "name")],
    )

    module.run_checks()

    try:
        results = dict(changed=False)

        PortainerGroupManager(module, results)()

        module.exit_json(**results)

    except module.client.exc.PortainerApiError as e:
        module.fail_json(
            msg=f"API request failed: {e}",
            status=e.status,
            body=e.body,
        )

    except Exception as e:
        module.fail_json(msg=f"Error managing group: {str(e)}")


if __name__ == "__main__":
    main()
