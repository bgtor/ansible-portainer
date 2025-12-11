# -*- coding: utf-8 -*-
# Author: Igor Moraru (@bgtor)
# License: GPL-3.0-or-later
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest
import json


from plugins.modules.portainer_environment_info import main
from plugins.module_utils.portainer_fields import PortainerFields as PF
from plugins.module_utils.portainer_client import RequestMethod
from tests.unit.plugins.conftest import MockMakeRequest


pytestmark = pytest.mark.usefixtures("patch_ansible_module", "mock_make_request")


@pytest.mark.parametrize(
    "patch_ansible_module",
    [{"name": "test-environment"}],
    indirect=True,
)
def test_get_environment_info_success(
    mock_make_request: MockMakeRequest, capfd: pytest.CaptureFixture
):
    calls = mock_make_request(
        {
            "/system/status": {"data": {}, "status": 200},
            f"{RequestMethod.GET} /endpoints": {
                "data": [{PF.ENDPOINT_ID: 1, PF.ENDPOINT_NAME: "test-environment"}],
                "status": 200,
            },
        },
    )
    with pytest.raises(SystemExit) as e:
        main()

    assert e.value.code == 0

    out, err = capfd.readouterr()
    result = json.loads(out)

    assert len(calls) == 2
    assert calls[1].params
    assert calls[1].params["Name"] == "test-environment"

    assert result["changed"] is False
    assert result["results"][0][PF.ENDPOINT_ID] == 1
    assert result["results"][0][PF.ENDPOINT_NAME] == "test-environment"


@pytest.mark.parametrize(
    "patch_ansible_module",
    [{"name": "test-environment"}],
    indirect=True,
)
def test_get_environment_info_empty(
    mock_make_request: MockMakeRequest, capfd: pytest.CaptureFixture
):
    calls = mock_make_request(
        {
            "/system/status": {"data": {}, "status": 200},
            f"{RequestMethod.GET} /endpoints": {
                "data": [],
                "status": 200,
            },
        },
    )
    with pytest.raises(SystemExit) as e:
        main()

    assert e.value.code == 0

    out, err = capfd.readouterr()
    result = json.loads(out)

    assert len(calls) == 2
    assert calls[1].params
    assert calls[1].params["Name"] == "test-environment"

    assert result["changed"] is False
    assert len(result["results"]) == 0
