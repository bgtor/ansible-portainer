# -*- coding: utf-8 -*-
# Author: Igor Moraru (@bgtor)
# License: GPL-3.0-or-later
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function, annotations

__metaclass__ = type

import pytest
import json

from plugins.module_utils.portainer_fields import PortainerFields as PF
from plugins.modules.portainer_tag import main
from plugins.module_utils.portainer_client import RequestMethod
from tests.unit.plugins.conftest import MockMakeRequest


pytestmark = pytest.mark.usefixtures("patch_ansible_module", "mock_make_request")


@pytest.mark.parametrize(
    "patch_ansible_module",
    [{"name": "test_tag", "state": "present"}],
    indirect=True,
)
def test_tag_create_success(mock_make_request: MockMakeRequest, capfd: pytest.CaptureFixture):
    mock_make_request(
        {
            "/system/status": {"data": {}, "status": 200},
            f"{RequestMethod.GET} /tags": {"data": [], "status": 200},
            f"{RequestMethod.POST} /tags": {
                "data": {PF.TAG_ID: 1, PF.TAG_NAME: "test_tag"},
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
    assert result["tag"][PF.TAG_ID] == 1
    assert result["tag"][PF.TAG_NAME] == "test_tag"


@pytest.mark.parametrize(
    "patch_ansible_module",
    [{"name": "test_tag", "state": "present"}],
    indirect=True,
)
def test_tag_already_exists_no_change(
    mock_make_request: MockMakeRequest, capfd: pytest.CaptureFixture
):
    """Integration: group exists and matches desired state"""

    mock_make_request(
        {
            "/system/status": {"data": {}, "status": 200},
            f"{RequestMethod.GET} /tags": {
                "data": [{PF.TAG_ID: 1, PF.TAG_NAME: "test_tag"}],
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
    assert result["tag"][PF.TAG_ID] == 1


@pytest.mark.parametrize(
    "patch_ansible_module",
    [{"name": "test_tag", "state": "present"}],
    indirect=True,
)
def test_duplicate_tags_fails_with_message(
    mock_make_request: MockMakeRequest, capfd: pytest.CaptureFixture
):
    """Integration: proper error when duplicates exist"""

    mock_make_request(
        {
            "/system/status": {"data": {}, "status": 200},
            f"{RequestMethod.GET} /tags": {
                "data": [
                    {PF.TAG_ID: 1, PF.TAG_NAME: "test_tag"},
                    {PF.TAG_ID: 2, PF.TAG_NAME: "test_tag"},
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
    assert "Multiple tags found" in result["msg"]
    assert result["duplicate_ids"] == [1, 2]


@pytest.mark.parametrize(
    "patch_ansible_module",
    [{"name": "test_tag", "state": "absent"}],
    indirect=True,
)
def test_delete_existing_tag(mock_make_request: MockMakeRequest, capfd: pytest.CaptureFixture):

    mock_make_request(
        {
            "/system/status": {"data": {}, "status": 200},
            f"{RequestMethod.GET} /tags": {
                "data": [
                    {PF.TAG_ID: 1, PF.TAG_NAME: "test_tag"},
                ],
                "status": 200,
            },
            f"{RequestMethod.DELETE} /tags/1": {
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
    assert "Tag deleted" in result["msg"]
