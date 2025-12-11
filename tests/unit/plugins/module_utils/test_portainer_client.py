# -*- coding: utf-8 -*-
# Author: Igor Moraru (@bgtor)
# License: GPL-3.0-or-later
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function, annotations

__metaclass__ = type

import pytest

from plugins.module_utils.portainer_client import PortainerClient
from tests.unit.plugins.conftest import MockMakeRequest, PortainerModuleFixture

pytestmark = pytest.mark.usefixtures("patch_ansible_module", "mock_make_request")


def test_client_initialization(portainer_module: PortainerModuleFixture):
    """Test that client initializes correctly"""

    module = portainer_module()

    client = PortainerClient(module)

    assert client.portainer_url == "https://portainer.example.com"
    assert client.portainer_token == "secret-token"
    assert client.headers["X-API-Key"] == "secret-token"
    assert client.headers["Content-Type"] == "application/json"


@pytest.mark.parametrize(
    "patch_ansible_module",
    [{"portainer_url": "https://portainer.example.com/"}],
    indirect=True,
)
def test_url_trailing_slash_removed(portainer_module: PortainerModuleFixture):
    """Test that trailing slash is removed from URL"""

    module = portainer_module()

    client = PortainerClient(module)

    assert client.portainer_url == "https://portainer.example.com"


def test_client_ping_error(
    mock_make_request: MockMakeRequest, portainer_module: PortainerModuleFixture
):
    mock_make_request(
        {
            "/system/status": {"data": {}, "status": 500},
        }
    )

    module = portainer_module()

    client = PortainerClient(module)

    with pytest.raises(SystemExit) as e:
        client.ping()

    assert e.value.code == 1


def test_client_make_request(
    mock_make_request: MockMakeRequest, portainer_module: PortainerModuleFixture
):

    mock_make_request(
        {
            "/endpoints": {"data": {"msg": "Successful response"}, "status": 200},
        }
    )

    module = portainer_module()

    client = PortainerClient(module)

    response = client.get("/endpoints")

    assert response["msg"] == "Successful response"
