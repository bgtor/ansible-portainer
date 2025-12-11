# -*- coding: utf-8 -*-
# Author: Igor Moraru (@bgtor)
# License: GPL-3.0-or-later
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function, annotations

__metaclass__ = type

import pytest
import json

from plugins.module_utils.portainer_fields import PortainerFields as PF
from plugins.modules.portainer_secret import main
from plugins.module_utils.portainer_client import RequestMethod
from tests.unit.plugins.conftest import MockMakeRequest


pytestmark = pytest.mark.usefixtures("patch_ansible_module", "mock_make_request")


@pytest.mark.parametrize(
    "patch_ansible_module",
    [
        {
            "name": "test_secret",
            "content": "Secret data",
            "state": "present",
            "endpoint_id": 1,
        }
    ],
    indirect=True,
)
def test_secret_create_success(mock_make_request: MockMakeRequest, capfd: pytest.CaptureFixture):
    mock_make_request(
        {
            "/system/status": {"data": {}, "status": 200},
            f"{RequestMethod.GET} /endpoints/1/docker/secrets": {"data": [], "status": 200},
            f"{RequestMethod.POST} /endpoints/1/docker/secrets/create": {
                "data": {
                    PF.SECRET_ID: 1,
                    PF.SECRET_NAME: "test_secret",
                    PF.SECRET_DATA: "Secret data",
                },
                "status": 201,
            },
        },
    )
    with pytest.raises(SystemExit) as e:
        main()

    assert e.value.code == 0

    out, err = capfd.readouterr()
    result = json.loads(out)

    assert result["changed"] is True
    assert result["secret"][PF.SECRET_ID] == 1
    assert result["secret"][PF.SECRET_NAME] == "test_secret"


@pytest.mark.parametrize(
    "patch_ansible_module",
    [
        {
            "name": "test_secret",
            "content": "Secret data updated",
            "state": "present",
            "endpoint_id": 1,
            "force": True,
        }
    ],
    indirect=True,
)
def test_update_existing_secret(mock_make_request: MockMakeRequest, capfd: pytest.CaptureFixture):

    calls = mock_make_request(
        {
            "/system/status": {"data": {}, "status": 200},
            f"{RequestMethod.GET} /endpoints/1/docker/secrets": {
                "data": [
                    {
                        PF.SECRET_ID: 1,
                        PF.SECRET_NAME: "test_secret",
                        PF.SECRET_DATA: "Secret data",
                    }
                ],
                "status": 200,
            },
            f"{RequestMethod.DELETE} /endpoints/1/docker/secrets/1": {
                "data": {},
                "status": 204,
            },
            f"{RequestMethod.POST} /endpoints/1/docker/secrets/create": {
                "data": {
                    PF.SECRET_ID: 2,
                    PF.SECRET_NAME: "test_secret",
                    PF.SECRET_DATA: "Secret data updated",
                },
                "status": 201,
            },
        },
    )
    with pytest.raises(SystemExit) as e:
        main()

    assert e.value.code == 0

    assert len(calls) == 4
    calls.assert_called_with(method=RequestMethod.DELETE, endpoint="/endpoints/1/docker/secrets/1")

    out, err = capfd.readouterr()
    result = json.loads(out)

    assert "Secret updated" in result["msg"]
    assert result["changed"] is True


@pytest.mark.parametrize(
    "patch_ansible_module",
    [
        {
            "name": "test_secret",
            "content": "Secret data",
            "state": "present",
            "endpoint_id": 1,
        }
    ],
    indirect=True,
)
def test_secret_already_exists_no_change(
    mock_make_request: MockMakeRequest, capfd: pytest.CaptureFixture
):
    mock_make_request(
        {
            "/system/status": {"data": {}, "status": 200},
            f"{RequestMethod.GET} /endpoints/1/docker/secrets": {
                "data": [
                    {
                        PF.SECRET_ID: 1,
                        PF.SECRET_NAME: "test_secret",
                        PF.SECRET_DATA: "Secret data",
                    }
                ],
                "status": 200,
            },
        }
    )

    with pytest.raises(SystemExit) as exc:
        main()

    assert exc.value.code == 0

    out, err = capfd.readouterr()
    result = json.loads(out)

    assert result["changed"] is False
    assert result["secret"][PF.SECRET_ID] == 1


@pytest.mark.parametrize(
    "patch_ansible_module",
    [
        {
            "name": "test_secret",
            "content": "Secret data",
            "state": "present",
            "endpoint_id": 1,
        }
    ],
    indirect=True,
)
def test_duplicate_configs_fails_with_message(
    mock_make_request: MockMakeRequest, capfd: pytest.CaptureFixture
):
    mock_make_request(
        {
            "/system/status": {"data": {}, "status": 200},
            f"{RequestMethod.GET} /endpoints/1/docker/secrets": {
                "data": [
                    {
                        PF.SECRET_ID: 1,
                        PF.SECRET_NAME: "test_secret",
                        PF.SECRET_DATA: "Secret data",
                    },
                    {
                        PF.SECRET_ID: 2,
                        PF.SECRET_NAME: "test_secret",
                        PF.SECRET_DATA: "Secret data",
                    },
                ],
                "status": 200,
            },
        }
    )

    with pytest.raises(SystemExit) as exc:
        main()

    assert exc.value.code != 0

    out, err = capfd.readouterr()
    result = json.loads(out)

    assert result["failed"] is True
    assert "Multiple swarm secrets found" in result["msg"]
    assert result["duplicate_ids"] == [1, 2]


@pytest.mark.parametrize(
    "patch_ansible_module",
    [
        {
            "name": "test_secret",
            "state": "absent",
            "endpoint_id": 1,
        }
    ],
    indirect=True,
)
def test_delete_existing_secret(mock_make_request: MockMakeRequest, capfd: pytest.CaptureFixture):

    mock_make_request(
        {
            "/system/status": {"data": {}, "status": 200},
            f"{RequestMethod.GET} /endpoints/1/docker/secrets": {
                "data": [
                    {
                        PF.SECRET_ID: 1,
                        PF.SECRET_NAME: "test_secret",
                        PF.SECRET_DATA: "Secret data",
                    },
                ],
                "status": 200,
            },
            f"{RequestMethod.DELETE} /endpoints/1/docker/secrets/1": {
                "data": {},
                "status": 204,
            },
        }
    )

    with pytest.raises(SystemExit) as exc:
        main()

    assert exc.value.code == 0

    out, err = capfd.readouterr()
    result = json.loads(out)

    assert result["changed"] is True
    assert "Secret deleted" in result["msg"]
