# -*- coding: utf-8 -*-
# Author: Igor Moraru (@bgtor)
# License: GPL-3.0-or-later
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest
import json

from plugins.modules.portainer_stack import main
from plugins.module_utils.portainer_fields import PortainerFields as PF
from plugins.module_utils.portainer_client import RequestMethod
from tests.unit.plugins.conftest import MockMakeRequest


pytestmark = pytest.mark.usefixtures("patch_ansible_module", "mock_make_request")


@pytest.mark.parametrize(
    "patch_ansible_module",
    [
        {
            "stack_id": 5,
            "state": "redeployed",
        }
    ],
    indirect=True,
)
def test_redeploy_nonexistent_stack(
    mock_make_request: MockMakeRequest, capfd: pytest.CaptureFixture
):
    calls = mock_make_request(
        {
            "/system/status": {"data": {}, "status": 200},
            f"{RequestMethod.GET} /stacks/5": {"data": {}, "status": 204},
        }
    )

    with pytest.raises(SystemExit) as e:
        main()

    assert e.value.code != 0

    out, err = capfd.readouterr()
    result = json.loads(out)

    assert "Cannot redeploy an inexistent stack." in result.get("msg", "")
    assert len(calls) >= 2


@pytest.mark.parametrize(
    "patch_ansible_module",
    [
        {
            "name": "webapp",
            "stack_type": "swarm",
            "stack_source": "repository",
            "endpoint_id": 1,
            "swarm_id": "swarm123",
            "repository_url": "https://github.com/org/repo.git",
            "repository_authentication": True,
            "repository_username": "deploy-user",
            "repository_password": "new-secret",
            "refs_name": "main",
            "compose_file": "docker-compose.yml",
            "update_password": True,
        }
    ],
    indirect=True,
)
def test_update_password_for_repository_forces_update(
    mock_make_request: MockMakeRequest, capfd: pytest.CaptureFixture
):
    existing_stack = {
        PF.STACK_ID: 5,
        PF.STACK_NAME: "webapp",
        PF.STACK_ENDPOINT_ID: 1,
        PF.STACK_SWARM_ID: "swarm123",
        PF.STACK_REPOSITORY_URL: "https://github.com/org/repo.git",
        PF.STACK_REPOSITORY_USERNAME: "deploy-user",
        PF.STACK_REPOSITORY_REFERENCE_NAME: "main",
        PF.STACK_COMPOSE_FILE: "docker-compose.yml",
        # password present but will be masked in to_dict
        PF.STACK_REPOSITORY_PASSWORD: "old-secret",
    }

    mock_make_request(
        {
            "/system/status": {"data": {}, "status": 200},
            f"{RequestMethod.GET} /stacks": {"data": [existing_stack], "status": 200},
            f"{RequestMethod.POST} /stacks/5/git": {
                "data": {**existing_stack, PF.STACK_REPOSITORY_PASSWORD: "***"},
                "status": 200,
            },
        }
    )

    with pytest.raises(SystemExit) as e:
        main()

    assert e.value.code == 0

    out, err = capfd.readouterr()
    result = json.loads(out)

    assert result["changed"] is True
    assert "Stack updated" in result.get("msg", "") or "Stack updated." in result.get("msg", "")
    assert result["stack"][PF.STACK_ID] == 5


@pytest.mark.parametrize(
    "patch_ansible_module",
    [
        {
            "name": "binary-stack",
            "stack_type": "standalone",
            "stack_source": "file",
            "endpoint_id": 1,
            "file": "/tmp/test-binary-compose.yml",
        }
    ],
    indirect=True,
)
def test_file_stack_with_binary_content_fails(
    mock_make_request: MockMakeRequest, patch_ansible_module, capfd: pytest.CaptureFixture
):
    # Create a temporary binary file at the configured path
    path = patch_ansible_module["file"]
    with open(path, "wb") as f:
        f.write(b"\x00\x01\x02\x03\x04")

    mock_make_request(
        {
            "/system/status": {"data": {}, "status": 200},
            f"{RequestMethod.GET} /stacks": {"data": [], "status": 200},
        }
    )

    with pytest.raises(SystemExit) as e:
        main()

    assert e.value.code != 0

    out, err = capfd.readouterr()
    result = json.loads(out)

    assert "Stack file contains binary data" in result.get("msg", "")


@pytest.mark.parametrize(
    "patch_ansible_module",
    [
        {
            "name": "myapp",
            "state": "started",
            "endpoint_id": 1,
        }
    ],
    indirect=True,
)
def test_start_already_running_stack(
    mock_make_request: MockMakeRequest, capfd: pytest.CaptureFixture
):
    existing_stack = {
        PF.STACK_ID: 7,
        PF.STACK_NAME: "myapp",
        PF.STACK_ENDPOINT_ID: 1,
        PF.STACK_STATUS: 1,  # running
    }

    mock_make_request(
        {
            "/system/status": {"data": {}, "status": 200},
            f"{RequestMethod.GET} /stacks": {"data": [existing_stack], "status": 200},
            f"{RequestMethod.GET} /stacks/7": {"data": existing_stack, "status": 200},
        }
    )

    with pytest.raises(SystemExit) as e:
        main()

    assert e.value.code == 0

    out, err = capfd.readouterr()
    result = json.loads(out)

    assert result["changed"] is False
    assert "already running" in result.get("msg", "")
