from __future__ import annotations

import copy

from typing import Any, overload, Literal
from ansible.module_utils.basic import AnsibleModule

from .portainer_client import PortainerClient
from .portainer_crud import PortainerCRUD


class IdempotencyManager:

    def __init__(self, module: PortainerModule):
        self.module = module
        # pass

    def needs_update(
        self,
        existing_data: dict[str, Any],
        new_data: dict[str, Any],
        skip_fields: list[str] | None = None,
    ) -> dict[str, Any]:
        """Check if existing object needs updates."""
        changes = {}
        skip_fields = skip_fields or []

        for k, v in new_data.items():
            if k in skip_fields:
                continue
            if v != existing_data.get(k):
                changes[k] = v

        return {k: v for k, v in changes.items() if v is not None}

    def build_diff(
        self,
        before_data: dict | None = None,
        after_data: dict | None = None,
        skip_fields: list | None = None,
    ):
        """Generate unified diff format."""
        before = self._sanitize_for_diff(before_data, skip_fields=skip_fields)

        _after_data = copy.deepcopy(before_data or {})
        _after_data.update(after_data or {})

        after = self._sanitize_for_diff(_after_data, skip_fields=skip_fields)

        return {
            "before": before,
            "after": after,
        }

    def _sanitize_for_diff(
        self, data: dict | None = None, skip_fields: list[str] | None = None
    ) -> dict:

        if not data:
            return {}

        skip_fields = skip_fields or []

        sanitized = copy.deepcopy(data)

        for k in skip_fields:
            sanitized.pop(k, None)

        return sanitized


class PortainerModule(AnsibleModule):
    def __init__(self, *args, **kwargs):

        super(PortainerModule, self).__init__(*args, **kwargs)

        self.client = PortainerClient(self)
        self.crud = PortainerCRUD(self)
        self.idempotency = IdempotencyManager(self)

    @classmethod
    def generate_argspec(cls, **kwargs):
        spec = PortainerClient.ARGSPEC.copy()
        spec.update(**kwargs)

        return spec

    def run_checks(self):
        if not self.check_mode:
            self.client.ping()

    @overload
    def validate_text_content(
        self,
        content: bytes,
        description: str | None = None,
        filepath: str | None = None,
        *,
        fail_on_error: Literal[True] = True,
    ) -> None: ...

    @overload
    def validate_text_content(
        self,
        content: bytes,
        description: str | None = None,
        filepath: str | None = None,
        *,
        fail_on_error: Literal[False],
    ) -> tuple[bool, str | None]: ...

    def validate_text_content(
        self,
        content: bytes,
        description: str | None = None,
        filepath: str | None = None,
        fail_on_error: bool = True,
    ) -> Any:
        """
        Validate that content is text, not binary.

        Args:
            content: bytes to validate
            description: human-readable description of the content (e.g., "configuration file")
            filepath: path to the file (for error messages)
            fail_on_error: if True, call fail_json on validation failure
                          if False, return (is_valid, error_message) tuple

        Returns:
            If fail_on_error=True: None (or exits via fail_json)
            If fail_on_error=False: (bool, str) - (is_valid, error_message)
        """
        # Validate UTF-8 encoding
        try:
            content.decode("utf-8")
        except UnicodeDecodeError:
            error_msg = self._build_error_message("invalid UTF-8 encoding", description, filepath)
            if fail_on_error:
                self.fail_json(msg=error_msg)
            return (False, error_msg)

        # Check for null bytes
        if b"\x00" in content:
            error_msg = self._build_error_message("null bytes detected", description, filepath)
            if fail_on_error:
                self.fail_json(msg=error_msg)
            return (False, error_msg)

        # Optional: Check for excessive control characters
        if len(content) > 0:
            control_chars = sum(1 for b in content if b < 0x20 and b not in (0x09, 0x0A, 0x0D))
            if control_chars / len(content) > 0.30:
                error_msg = self._build_error_message(
                    "excessive control characters", description, filepath
                )
                if fail_on_error:
                    self.fail_json(msg=error_msg)
                return (False, error_msg)

        if fail_on_error:
            return None
        return (True, None)

    def _build_error_message(self, reason, description, filepath):
        """Build a consistent error message"""
        parts = []
        if description:
            parts.append(description.capitalize())
        else:
            parts.append("Content")

        parts.append(f"contains binary data ({reason})")

        if filepath:
            parts.append(f": {filepath}")

        return " ".join(parts)
