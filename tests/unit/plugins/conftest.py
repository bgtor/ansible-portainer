from __future__ import annotations

import json
import pytest

from unittest import mock
from typing import Any, Callable, TypedDict, Union
from dataclasses import dataclass, field

from ansible.module_utils.common.text.converters import to_bytes
from ansible.module_utils.common._collections_compat import MutableMapping
from plugins.module_utils.portainer_module import PortainerModule
from plugins.module_utils.portainer_client import PortainerClient, RequestMethod


def portainer_default_options():
    return {
        "portainer_url": "https://portainer.example.com",
        "portainer_token": "secret-token",
    }


@pytest.fixture
def module_warn():
    return mock.MagicMock()


@pytest.fixture
def patch_ansible_module(request):
    """Fixture to patch Ansible module arguments"""
    args: dict[str, Any] = portainer_default_options()

    if hasattr(request, "param") and isinstance(request.param, MutableMapping):
        args.update(request.param)
    else:
        pass

    # Ensure required Ansible internals are set
    if "ANSIBLE_MODULE_ARGS" not in args:
        args = {"ANSIBLE_MODULE_ARGS": args}

    args["ANSIBLE_MODULE_ARGS"].setdefault("_ansible_remote_tmp", "/tmp")
    args["ANSIBLE_MODULE_ARGS"].setdefault("_ansible_keep_remote_files", False)

    # Try to use official testing utility first
    try:
        from ansible.module_utils.testing import patch_module_args

        with patch_module_args(args["ANSIBLE_MODULE_ARGS"]):
            yield args["ANSIBLE_MODULE_ARGS"]
    except ImportError:
        # Fallback for older Ansible versions
        with mock.patch("ansible.module_utils.basic._ANSIBLE_ARGS", to_bytes(json.dumps(args))):
            yield args["ANSIBLE_MODULE_ARGS"]


PortainerModuleFixture = Callable[..., PortainerModule]


@pytest.fixture
def portainer_module() -> PortainerModuleFixture:
    """Create a PortainerModule instance"""

    def _create(**kwargs):
        return PortainerModule(
            argument_spec=PortainerModule.generate_argspec(**kwargs),
            supports_check_mode=True,
        )

    return _create


class EndpointResponse(TypedDict):
    data: list | dict
    status: int


@dataclass
class CallLog:
    method: RequestMethod
    endpoint: str
    params: dict | None = None
    data: dict | None = None


@dataclass
class CallLogs:
    logs: list[CallLog] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.logs)

    def __getitem__(self, index):
        return self.logs[index]

    def append(self, log: CallLog):
        self.logs.append(log)

    def assert_called_with(
        self,
        method: RequestMethod | None = None,
        endpoint: str | None = None,
        params: dict | None = None,
        data: dict | None = None,
    ):
        called = []
        for log in self.logs:
            if method and log.method != method:
                continue
            if endpoint and log.endpoint != endpoint:
                continue
            if params and log.params and not (params.items() <= log.params.items()):
                continue
            if data and log.data and not (data.items() <= log.data.items()):
                continue

            called.append(log)

        if not called:
            raise AssertionError("Endpoint was not called with provided arguments.")

        return called


EndpointResponses = Union[list[EndpointResponse], EndpointResponse]
MockMakeRequest = Callable[[dict[str, EndpointResponses]], CallLogs]


@pytest.fixture
def mock_make_request(monkeypatch) -> MockMakeRequest:

    def _mock_request(endpoint_responses):
        """
        Mock PortainerClient._make_request with flexible endpoint matching.

        Args:
            endpoint_responses: Dict mapping endpoints to responses.
                - Keys can be "METHOD /endpoint" or just "/endpoint"
                - Values can be:
                    * Single dict: Returns same response for ALL calls (reusable)
                    * List of dicts: Returns responses in sequence (exhaustible)
                - Each response dict should have 'data' and optionally 'status' keys

        Examples:
            # Single response - reused for all calls
            {
                "GET /endpoint_groups": {"data": [{"Id": 1}], "status": 200}
            }

            # Multiple sequential responses
            {
                "POST /endpoint_groups": [
                    {"data": {"Id": 1}, "status": 201},
                    {"data": {"Id": 2}, "status": 201},
                ]
            }

            # Mixed - ping reused, groups sequential
            {
                "/system/status": {"data": {}, "status": 200},  # Reused
                "GET /endpoint_groups": [                        # Sequential
                    {"data": [], "status": 200},
                    {"data": [{"Id": 1}], "status": 200}
                ]
            }
        """
        call_logs = CallLogs()

        response_queues = {}
        for key, responses in endpoint_responses.items():
            is_list = isinstance(responses, list)
            response_queues[key] = {
                "response_queue": responses if is_list else [responses],
                "multiple": is_list,
                "call_count": 0,
            }

        def _mock_make_request(
            self,
            method: RequestMethod,
            endpoint: str,
            *args,
            params: dict[str, Any] | None = None,
            data: dict[str, Any] | None = None,
            return_info: bool = False,
            **kwargs,
        ):

            call_logs.append(CallLog(method=method, endpoint=endpoint, params=params, data=data))

            # Try exact match first (with method), then fallback to endpoint-only
            key = f"{method} {endpoint}"
            if key not in response_queues:
                key = endpoint

            if key not in response_queues:
                raise KeyError(
                    f"No mock response defined for '{method} {endpoint}'. "
                    f"Available: {list(response_queues.keys())}"
                )

            queue_info = response_queues[key]
            call_count = queue_info["call_count"]
            response_queue = queue_info["response_queue"]
            multiple = queue_info["multiple"]

            # Check if we've exhausted the response queue (only for sequential responses)
            if multiple and call_count >= len(response_queue):
                raise IndexError(
                    f"Mock for '{key}' called {call_count + 1} time(s) "
                    f"but only {len(response_queue)} response(s) defined. "
                    f"Hint: Use a single dict (not a list) if the response should be reused."
                )

            # Sequential: use next response; Reusable: always use first response
            response = response_queue[call_count] if multiple else response_queue[0]
            queue_info["call_count"] += 1

            if return_info:
                return {"status": response.get("status", 200), "msg": "OK"}

            return response.get("data", {})

        monkeypatch.setattr(PortainerClient, "_make_request", _mock_make_request)
        return call_logs

    return _mock_request
