#!/usr/bin/python
# portainer_environment_info.py - A module to get info about a Portainer environments.
# Author: Igor Moraru (@bgtor)
# License: GPL-3.0-or-later
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function, annotations

__metaclass__ = type

DOCUMENTATION = r"""
---
module: portainer_environment_info
short_description: Gets Portainer environment info
description:
    - Retrieve info about a Portainer environment(s)
version_added: "1.0.0"
author: Igor Moraru (@bgtor)
options:
    name:
        description: Name of the environment
        type: str
    endpoint_id:
        description: The ID of the environment
        type: int
    groups:
        description: Name of the groups to filter environments by
        type: list
        elements: str
    tags:
        description: List of tag names to filter environments by
        type: list
        elements: str
extends_documentation_fragment:
    - bgtor.portainer.portainer_client
"""

EXAMPLES = r"""
- name: Get information about environment by its ID
  portainer_environment_info:
    portainer_url: https://portainer.example.com
    portainer_token: "{{ portainer_api_token }}"
    endpoint_id: 1

- name: Get information about environment by its group and tags
  portainer_environment_info:
    portainer_url: https://portainer.example.com
    portainer_token: "{{ portainer_api_token }}"
    groups:
        - dev_group
    tags:
        - tag1
        - tag2
"""

RETURN = r"""
results:
    description: Environment information
    returned: always
    type: dict
    sample: [{
        "Id": 1,
        "Name": "myendpoint",
        "Status": 1
    }]
msg:
    description: Human readable message
    returned: always
    type: str
"""

from typing import TYPE_CHECKING

from ..module_utils.portainer_module import PortainerModule

if TYPE_CHECKING:
    from ..module_utils.portainer_crud import BaseCRUD


class PortainerEnvironmentInfoManager:
    def __init__(self, module: PortainerModule):
        self.module = module
        self.crud = module.crud

        self.endpoint_id = module.params["endpoint_id"]
        self.name = module.params["name"]
        self.groups = module.params["groups"]
        self.tags = module.params["tags"]

    def get_environments(self):

        if self.endpoint_id:
            return [self.crud.environment.get_item_by_id(self.endpoint_id)]

        group_ids = self._get_group_ids() if self.groups else []
        tag_ids = self._get_tag_ids() if self.tags else []

        return self.crud.environment.get_filtered_endpoints(
            name=self.name, group_ids=group_ids, tag_ids=tag_ids
        )

    def _get_group_ids(self):
        return self._resolve_names(names=self.groups, crud=self.crud.group)

    def _get_tag_ids(self):
        return self._resolve_names(names=self.tags, crud=self.crud.tag)

    def _resolve_names(self, names: list[str], crud: BaseCRUD):
        ids = [crud.resolve_name_to_id(name=name) for name in names]
        return [id for id in ids if id is not None]


def main():
    argument_spec = PortainerModule.generate_argspec(
        endpoint_id=dict(type="int", default=None),
        name=dict(type="str", default=None),
        groups=dict(type="list", elements="str"),
        tags=dict(type="list", elements="str"),
    )

    module = PortainerModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        mutually_exclusive=[
            ["endpoint_id", "name"],
            ["endpoint_id", "groups"],
            ["endpoint_id", "tags"],
        ],
        required_one_of=[["name", "endpoint_id", "groups", "tags"]],
    )

    module.run_checks()

    environments = []
    msg = ""

    try:
        manager = PortainerEnvironmentInfoManager(module)

        environments = manager.get_environments()

        msg = "Environments successfully retrieved!"

    except module.client.exc.PortainerApiError as e:
        module.fail_json(
            msg=f"API Request Error: {e}",
            status=e.status,
            body=e.body,
            url=e.url,
            method=e.method,
            data=e.data,
        )

    except Exception as e:
        module.fail_json(msg=f"Error getting environment info: {str(e)}")

    module.exit_json(**{"changed": False, "msg": msg, "results": environments})


if __name__ == "__main__":
    main()
