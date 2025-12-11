# -*- coding: utf-8 -*-
# Author: Igor Moraru (@bgtor)
# License: GPL-3.0-or-later
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest
import json


from plugins.modules.portainer_environment import main
from plugins.module_utils.portainer_fields import PortainerFields as PF
from plugins.module_utils.portainer_client import RequestMethod
from tests.unit.plugins.conftest import MockMakeRequest


pytestmark = pytest.mark.usefixtures("patch_ansible_module", "mock_make_request")


@pytest.mark.parametrize(
    "patch_ansible_module",
    [
        {
            "name": "test-environment",
            "creation_type": 4,
            "url": "https://portainer.example.com",
            "edge_tunnel_server_address": "https://portainer.example.com:8000",
        }
    ],
    indirect=True,
)
def test_create_environment_success(
    mock_make_request: MockMakeRequest, capfd: pytest.CaptureFixture
):
    calls = mock_make_request(
        {
            "/system/status": {"data": {}, "status": 200},
            f"{RequestMethod.GET} /endpoints": {
                "data": [],
                "status": 200,
            },
            f"{RequestMethod.POST} /endpoints": {
                "data": {
                    PF.ENDPOINT_ID: 1,
                    PF.ENDPOINT_NAME: "test-environment",
                    PF.ENDPOINT_CREATION_TYPE: 4,
                    PF.ENDPOINT_URL: "https://portainer.example.com",
                    PF.ENDPOINT_EDGE_TUNNEL_SERVER_ADDRESS: "https://portainer.example.com:8000",
                },
                "status": 200,
            },
        },
    )
    with pytest.raises(SystemExit) as e:
        main()

    assert e.value.code == 0

    out, err = capfd.readouterr()
    result = json.loads(out)

    assert len(calls) == 3

    assert result["changed"] is True
    assert result["environment"][PF.ENDPOINT_ID] == 1
    assert result["environment"][PF.ENDPOINT_NAME] == "test-environment"


@pytest.mark.parametrize(
    "patch_ansible_module",
    [
        {
            "name": "test-environment",
            "creation_type": 4,
            "url": "https://portainer.example.com",
            "edge_tunnel_server_address": "https://portainer.example.com:8000",
        }
    ],
    indirect=True,
)
def test_update_existing_environment(
    mock_make_request: MockMakeRequest, capfd: pytest.CaptureFixture
):
    calls = mock_make_request(
        {
            "/system/status": {"data": {}, "status": 200},
            f"{RequestMethod.GET} /endpoints": {
                "data": [
                    {
                        PF.ENDPOINT_ID: 1,
                        PF.ENDPOINT_NAME: "test-environment",
                    }
                ],
                "status": 200,
            },
            f"{RequestMethod.PUT} /endpoints/1": {
                "data": {
                    PF.ENDPOINT_ID: 1,
                    PF.ENDPOINT_NAME: "test-environment",
                    PF.ENDPOINT_CREATION_TYPE: 4,
                    PF.ENDPOINT_URL: "https://portainer.example.com",
                    PF.ENDPOINT_EDGE_TUNNEL_SERVER_ADDRESS: "https://portainer.example.com:8000",
                },
                "status": 200,
            },
        },
    )
    with pytest.raises(SystemExit) as e:
        main()

    assert e.value.code == 0

    out, err = capfd.readouterr()
    result = json.loads(out)

    assert len(calls) == 3

    assert result["changed"] is True
    assert "Environment updated" in result["msg"]
    assert result["environment"][PF.ENDPOINT_ID] == 1
    assert result["environment"][PF.ENDPOINT_NAME] == "test-environment"


@pytest.mark.parametrize(
    "patch_ansible_module",
    [
        {
            "name": "test-environment",
            "state": "absent",
        }
    ],
    indirect=True,
)
def test_delete_existing_environment(
    mock_make_request: MockMakeRequest, capfd: pytest.CaptureFixture
):
    calls = mock_make_request(
        {
            "/system/status": {"data": {}, "status": 200},
            f"{RequestMethod.GET} /endpoints": {
                "data": [
                    {
                        PF.ENDPOINT_ID: 1,
                        PF.ENDPOINT_NAME: "test-environment",
                    }
                ],
                "status": 200,
            },
            f"{RequestMethod.DELETE} /endpoints/1": {
                "data": {},
                "status": 204,
            },
        },
    )
    with pytest.raises(SystemExit) as e:
        main()

    assert e.value.code == 0

    out, err = capfd.readouterr()
    result = json.loads(out)

    assert len(calls) == 3

    assert result["changed"] is True
    assert "Environment test-environment deleted" in result["msg"]
    assert result["environment"][PF.ENDPOINT_ID] == 1
    assert result["environment"][PF.ENDPOINT_NAME] == "test-environment"


@pytest.mark.parametrize(
    "patch_ansible_module",
    [
        {
            "name": "test-environment",
            "state": "healthy",
        }
    ],
    indirect=True,
)
def test_environment_becomes_active(
    mock_make_request: MockMakeRequest, capfd: pytest.CaptureFixture
):
    calls = mock_make_request(
        {
            "/system/status": {"data": {}, "status": 200},
            f"{RequestMethod.GET} /endpoints": {
                "data": [
                    {
                        PF.ENDPOINT_ID: 1,
                        PF.ENDPOINT_NAME: "test-environment",
                        PF.ENDPOINT_HEARTBEAT: False,
                    }
                ],
                "status": 200,
            },
            f"{RequestMethod.GET} /endpoints/1": [
                {
                    "data": {
                        PF.ENDPOINT_ID: 1,
                        PF.ENDPOINT_NAME: "test-environment",
                        PF.ENDPOINT_HEARTBEAT: False,
                    },
                    "status": 200,
                },
                {
                    "data": {
                        PF.ENDPOINT_ID: 1,
                        PF.ENDPOINT_NAME: "test-environment",
                        PF.ENDPOINT_HEARTBEAT: False,
                    },
                    "status": 200,
                },
                {
                    "data": {
                        PF.ENDPOINT_ID: 1,
                        PF.ENDPOINT_NAME: "test-environment",
                        PF.ENDPOINT_HEARTBEAT: True,
                    },
                    "status": 200,
                },
            ],
        },
    )
    with pytest.raises(SystemExit) as e:
        main()

    assert e.value.code == 0

    out, err = capfd.readouterr()
    result = json.loads(out)

    assert len(calls) == 5

    assert result["changed"] is False
    assert "Environment test-environment is healthy" in result["msg"]
    assert result["environment"][PF.ENDPOINT_ID] == 1
    assert result["environment"][PF.ENDPOINT_NAME] == "test-environment"
