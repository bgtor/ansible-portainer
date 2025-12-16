# -*- coding: utf-8 -*-
# Author: Igor Moraru (@bgtor)
# License: GPL-3.0-or-later
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function, annotations

__metaclass__ = type

import pytest

from plugins.module_utils.portainer_module import IdempotencyManager
from tests.unit.plugins.conftest import PortainerModuleFixture

pytestmark = pytest.mark.usefixtures("patch_ansible_module", "portainer_module")


def test_build_diffs_handles_none_data(portainer_module: PortainerModuleFixture):

    module = portainer_module()

    idem = IdempotencyManager(module)

    before_data = None
    after_data = None

    diff = idem.build_diff(before_data=before_data, after_data=after_data)

    assert diff.get("before") is not None
    assert isinstance(diff["before"], dict)

    assert diff.get("after") is not None
    assert isinstance(diff["after"], dict)
