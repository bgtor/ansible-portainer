from __future__ import annotations

import json

from functools import lru_cache, reduce
from typing import TYPE_CHECKING, TypeVar, Any, Callable, Generator, cast
from contextlib import contextmanager

from .portainer_fields import PortainerFields as PF
from .portainer_client import BodyFormat


if TYPE_CHECKING:
    from .portainer_module import PortainerModule


class PortainerCRUDException(Exception):
    pass


class ItemNotExists(PortainerCRUDException):
    pass


class MultipleItemsReturned(PortainerCRUDException):
    def __init__(self, message, item_ids: list[int]):
        super().__init__(message)
        self.item_ids = item_ids


def get_nested(d, path, default=None):
    try:
        return reduce(lambda x, key: x[key], path.split("."), d)
    except (KeyError, TypeError):
        return default


T = TypeVar("T", dict, list)


class BaseCRUD:

    def __init__(
        self,
        module: PortainerModule,
        endpoint: str,
        name_field: str,
        id_field: str,
        resource_name: str,
    ) -> None:
        self.module = module

        self.resource_name = resource_name
        self._endpoint = endpoint
        self.name_field = name_field
        self.id_field = id_field

    def _get_delete_endpoint(self, id: int) -> str:
        return f"{self.endpoint}/{id}"

    def _get_create_endpoint(self) -> str:
        return self.endpoint

    def _get_update_endpoint(self, id: int) -> str:
        return f"{self.endpoint}/{id}"

    @property
    def _update_method(self) -> Callable:
        return self.module.client.put

    @property
    def endpoint(self) -> str:
        return self._endpoint

    def get_item_by_name(
        self, name: str, params: dict | None = None, filters: dict | None = None
    ) -> dict[str, Any]:
        if not name:
            raise ValueError("Name should not be empty")

        all_items = self.list_items(params=params)

        items = [item for item in all_items if item.get(self.name_field) == name]

        if filters:
            for k, v in filters.items():
                items = [item for item in items if item.get(k) == v]

        if len(items) == 0:
            raise ItemNotExists(f"Item '{name}' does not exist.")
        elif len(items) == 1:
            return items[0]
        else:
            raise MultipleItemsReturned("Multiple items found", [g[self.id_field] for g in items])

    def get_item_by_id(self, item_id: int) -> dict[str, Any]:
        if item_id is None:
            raise ValueError("Item ID cannot be None")

        return self._process_response(self.module.client.get(f"{self.endpoint}/{item_id}"))

    def get_item(
        self,
        name: str | None = None,
        item_id: int | None = None,
        params: dict | None = None,
    ) -> dict[str, Any]:
        """Get item by name or ID"""

        if item_id is not None:
            return self.get_item_by_id(item_id)

        if name is not None:
            return self.get_item_by_name(name, params=params)

        raise ValueError("Provide either 'name' or 'item_id'")

    def list_items(self, params: dict | None = None) -> list[dict[str, Any]]:

        return self._process_response(self.module.client.get(self.endpoint, params=params))

    def create_item(
        self,
        name: str,
        item_data: dict | None = None,
        body_format: BodyFormat | None = None,
        params: dict | None = None,
    ) -> dict[str, Any]:
        if not name:
            raise ValueError("Name should not be empty")

        if item_data is None:
            item_data = {}

        endpoint = self._get_create_endpoint()

        return self._process_response(
            self.module.client.post(
                endpoint,
                {self.name_field: name, **item_data},
                body_format=body_format,
                params=params,
            )
        )

    def update_item(
        self, item_id: int, changes: dict, params: dict | None = None
    ) -> dict[str, Any]:
        if item_id is None:
            raise ValueError("Item ID cannot be None")

        endpoint = self._get_update_endpoint(item_id)

        return self._process_response(self._update_method(endpoint, data=changes, params=params))

    def delete_item_by_name(self, name: str) -> None:
        if not name:
            raise ValueError("Name should not be empty")

        item = self.get_item_by_name(name=name)

        self.delete_item_by_id(item[self.id_field])

    def delete_item_by_id(self, item_id: int, params: dict | None = None) -> None:
        if item_id is None:
            raise ValueError("Item ID cannot be None")

        endpoint = self._get_delete_endpoint(item_id)

        self.module.client.delete(endpoint, params=params)

    def delete_item(self, name: str | None = None, item_id: int | None = None) -> None:
        """Delete item by name or ID"""

        if item_id is not None:
            return self.delete_item_by_id(item_id)

        if name is not None:
            return self.delete_item_by_name(name)

        raise ValueError("Provide either 'name' or 'item_id'")

    def validate_single_item(
        self,
        name: str,
        operation="operate on",
        params: dict | None = None,
        filters: dict | None = None,
    ) -> dict[str, Any] | None:

        try:
            return self.get_item_by_name(name=name, params=params, filters=filters)
        except MultipleItemsReturned as e:
            self.module.fail_json(
                msg=f"Cannot {operation} {self.resource_name}: Multiple {self.resource_name}s found with name '{name}'. "
                f"Please use the Portainer UI to remove duplicates.",
                duplicate_ids=e.item_ids,
            )
        except ItemNotExists:
            return None

    def resolve_name_to_id(self, name: str, create_flag: str | None = None) -> int | None:

        create = self.module.params.get(create_flag, False)

        item = self.validate_single_item(name=name, operation="retrieve")

        if not item:

            if not create_flag:
                return None

            if create:
                item = self.create_item(name=name)
            else:
                self.module.fail_json(
                    msg=f"{self.resource_name.capitalize()} '{name}' does not exist. "
                    f"Use {create_flag}=true to create it automatically."
                )

        return item[self.id_field]

    def _process_response(self, data: T) -> T:
        """
        Hook for subclasses to normalize/transform response data.
        Can handle both single items and lists.
        """
        if not data:
            return data

        if isinstance(data, list):
            return [self._process_single_item(item) for item in data]
        return self._process_single_item(data)

    def _process_single_item(self, item: dict) -> dict:
        """Process a single item. Override this in subclasses."""
        return item


class BaseDockerCRUD(BaseCRUD):
    """
    Base class for Docker API resources accessed through Portainer's proxy.
    Handles endpoint construction and Docker-specific response processing.
    """

    def __init__(
        self,
        module: PortainerModule,
        docker_endpoint: str,
        name_field: str,
        id_field: str,
        resource_name: str,
    ) -> None:
        # Store the Docker endpoint separately
        self.docker_endpoint = docker_endpoint

        # Initialize parent with placeholder endpoint
        super().__init__(
            module=module,
            endpoint=docker_endpoint,
            name_field=name_field,
            id_field=id_field,
            resource_name=resource_name,
        )

        self._endpoint_id = self.module.params.get("endpoint_id")

    @contextmanager
    def using_endpoint(self, endpoint_id: int) -> Generator[BaseDockerCRUD, None, None]:
        """Context manager to set the Portainer endpoint for Docker API access"""
        old_endpoint_id = self._endpoint_id
        self._endpoint_id = endpoint_id
        try:
            yield self
        finally:
            self._endpoint_id = old_endpoint_id

    @property
    def endpoint(self) -> str:
        """Build the Docker API endpoint through Portainer proxy"""
        if self._endpoint_id is None:
            raise ValueError(
                f"endpoint_id must be set to use {self.resource_name}. "
                f"Either set 'endpoint_id' as module param or "
                f"use 'with crud.using_endpoint(endpoint_id):' context manager."
            )
        return f"/endpoints/{self._endpoint_id}/docker{self.docker_endpoint}"

    def _process_single_item(self, item: dict) -> dict:
        """
        Process Docker API responses, which often have nested structures.
        Can be overridden by subclasses for resource-specific processing.
        """
        name = get_nested(item, "Spec.Name", None)

        if name and "Name" not in item:
            item["Name"] = name

        return item

    def _get_create_endpoint(self) -> str:
        return f"{self.endpoint}/create"

    def _get_update_endpoint(self, id: int) -> str:
        return f"{self.endpoint}/{id}/update"


class EndpointGroupCRUD(BaseCRUD):

    def __init__(self, module: PortainerModule) -> None:
        resource_name = "group"
        endpoint = "/endpoint_groups"
        name_field = PF.GROUP_NAME
        id_field = PF.GROUP_ID
        super().__init__(module, endpoint, name_field, id_field, resource_name)

    def associate_endpoint(self, group_id: int, endpoint_id: int) -> None:
        self.module.client.put(f"{self.endpoint}/{group_id}/endpoints/{endpoint_id}")

    def deassociate_endpoint(self, group_id: int, endpoint_id: int) -> None:
        self.module.client.delete(f"{self.endpoint}/{group_id}/endpoints/{endpoint_id}")


class TagCRUD(BaseCRUD):

    def __init__(self, module: PortainerModule) -> None:
        resource_name = "tag"
        endpoint = "/tags"
        name_field = PF.TAG_NAME
        id_field = PF.TAG_ID
        super().__init__(module, endpoint, name_field, id_field, resource_name)


class EnvironmentCRUD(BaseCRUD):
    def __init__(self, module: PortainerModule) -> None:
        resource_name = "environment"
        endpoint = "/endpoints"
        name_field = PF.ENDPOINT_NAME
        id_field = PF.ENDPOINT_ID
        super().__init__(module, endpoint, name_field, id_field, resource_name)

    def _process_single_item(self, item: dict[str, Any]) -> dict[str, Any]:
        """
        Normalize Portainer's inconsistent TLS field structure.

        GET returns nested TLSConfig object, but POST/PUT expect flat fields.
        This converts GET format to POST format for consistent comparisons.
        """
        if not isinstance(item, dict):
            return item

        if item.get(PF.ENDPOINT_TYPE) == 4 and item.get(PF.ENDPOINT_HEARTBEAT, False):
            item[PF.ENDPOINT_SWARM] = self.get_swarm_info(endpoint_id=item[PF.ENDPOINT_ID])

        if PF.ENDPOINT_TLS_CONFIG not in item:
            return item

        normalized = item.copy()
        tls_config = normalized.pop(PF.ENDPOINT_TLS_CONFIG)

        # Flatten TLS fields to root level
        for key in [
            PF.ENDPOINT_TLS,
            PF.ENDPOINT_TLS_CA_CERT,
            PF.ENDPOINT_TLS_CERT,
            PF.ENDPOINT_TLS_KEY,
            PF.ENDPOINT_TLS_SKIP_VERIFY,
        ]:
            if key in tls_config:
                normalized[key] = tls_config.get(key)

        return normalized

    def create_item(
        self,
        name: str,
        item_data: dict[str, Any] | None = None,
        body_format: BodyFormat | None = None,
        params: dict | None = None,
    ) -> dict[str, Any]:
        item_data = item_data or {}

        if PF.ENDPOINT_TAG_IDS in item_data:
            item_data[PF.ENDPOINT_TAG_IDS] = json.dumps(item_data[PF.ENDPOINT_TAG_IDS])

        return super().create_item(name, item_data, body_format=body_format, params=params)

    def get_filtered_endpoints(
        self,
        name: str | None = None,
        group_ids: list[int] | None = None,
        tag_ids: list[int] | None = None,
    ) -> list[dict[str, Any]]:

        params: dict[str, Any] = {
            PF.ENDPOINT_EXCLUDE_SNAPSHOT: True,
            PF.ENDPOINT_EXCLUDE_SNAPSHOT_RAW: True,
        }

        if group_ids:
            params.update([(f"{PF.ENDPOINT_GROUP_IDS_QUERY}[]", gid) for gid in group_ids])

        if tag_ids:
            params.update([(f"{PF.ENDPOINT_TAG_IDS_QUERY}[]", tid) for tid in tag_ids])

        if name:
            params.update([(PF.ENDPOINT_NAME, name)])

        return self.list_items(params=params)

    @lru_cache
    def get_swarm_info(self, endpoint_id: int) -> dict[str, Any]:
        with self.module.crud.swarm.using_endpoint(endpoint_id):
            return self.module.crud.swarm.inspect_swarm()


class StackCRUD(BaseCRUD):

    def __init__(self, module: PortainerModule) -> None:
        resource_name = "stack"
        endpoint = "/stacks"
        name_field = PF.STACK_NAME
        id_field = PF.STACK_ID
        super().__init__(module, endpoint, name_field, id_field, resource_name)

        self.stack_type = module.params.get("stack_type", "")
        self.stack_source = module.params.get("stack_source", "")

    def _get_create_endpoint(self) -> str:
        return f"{self.endpoint}/create/{self.stack_type}/{self.stack_source}"

    def _get_update_endpoint(self, id: int) -> str:
        if self.stack_type == "swarm":
            if self.stack_source == "repository":
                return f"{self.endpoint}/{id}/git"

        return f"{self.endpoint}/{id}"

    @property
    def _update_method(self) -> Callable:
        if self.stack_type == "swarm":
            if self.stack_source == "repository":
                return self.module.client.post

        return self.module.client.put

    def get_stack_file_content(self, stack_id: int) -> str:
        stack_file = self.module.client.get(f"{self.endpoint}/{stack_id}/file")
        return stack_file[PF.STACK_FILE_CONTENT]

    def stop_stack(self, stack_id: int, endpoint_id: int) -> dict[str, Any]:
        params = {PF.STACK_ENDPOINT_ID_QUERY: endpoint_id}
        return self.module.client.post(f"{self.endpoint}/{stack_id}/stop", params=params)

    def start_stack(self, stack_id: int, endpoint_id: int) -> dict[str, Any]:
        params = {PF.STACK_ENDPOINT_ID_QUERY: endpoint_id}
        return self.module.client.post(f"{self.endpoint}/{stack_id}/start", params=params)

    def _process_single_item(self, item: dict[str, Any]) -> dict[str, Any]:

        git_configs = item.pop(PF.STACK_GIT_CONFIGS, None)
        if git_configs:
            item[PF.STACK_REPOSITORY_AUTHENTICATION] = bool(
                get_nested(git_configs, PF.STACK_GIT_CONFIGS_AUTHENTICATION)
            )
            item[PF.STACK_REPOSITORY_AUTHORIZATION_TYPE] = get_nested(
                git_configs, PF.STACK_GIT_CONFIGS_AUTH_TYPE
            )
            item[PF.STACK_REPOSITORY_REFERENCE_NAME] = get_nested(
                git_configs, PF.STACK_GIT_CONFIGS_REFS_NAME
            )
            item[PF.STACK_REPOSITORY_USERNAME] = get_nested(
                git_configs, PF.STACK_GIT_CONFIGS_USERNAME
            )
            item[PF.STACK_TLS_SKIP_VERIFY] = get_nested(
                git_configs, PF.STACK_GIT_CONFIGS_TLS_SKIP_VERIFY
            )

        return item

    def redeploy(
        self,
        stack_id: int,
        data: dict,
        params: dict | None = None,
    ) -> dict[str, Any] | None:
        response = None
        if self.stack_type == "swarm":
            if self.stack_source == "repository":
                response = self.module.client.put(
                    f"{self.endpoint}/{stack_id}/git/redeploy", data=data, params=params
                )

        if not isinstance(response, dict):
            raise ValueError("Unexpected response received")

        return self._process_response(response)


class SwarmCRUD(BaseDockerCRUD):

    def __init__(self, module: PortainerModule):
        super().__init__(
            module=module,
            docker_endpoint="/swarm",
            name_field="Name",
            id_field="ID",
            resource_name="swarm",
        )

    def _process_single_item(self, item: dict[str, Any]) -> dict[str, Any]:
        item = super()._process_single_item(item)

        name = get_nested(item, "Spec.Name", None)

        if name:
            item["Name"] = name

        return item

    def inspect_swarm(self) -> dict[str, Any]:
        return cast(dict, super().list_items())

    def create_item(self, *args, **kwargs) -> dict:
        return {}

    def delete_item(self, *args, **kwargs) -> None:
        pass

    def delete_item_by_id(self, *args, **kwargs) -> None:
        pass

    def delete_item_by_name(self, *args, **kwargs) -> None:
        pass

    def update_item(self, *args, **kwargs) -> dict:
        return {}


class SwarmConfigCRUD(BaseDockerCRUD):

    def __init__(self, module: PortainerModule):
        super().__init__(
            module=module,
            docker_endpoint="/configs",
            name_field="Name",
            id_field="ID",
            resource_name="swarm config",
        )


class SwarmSecretCRUD(BaseDockerCRUD):

    def __init__(self, module: PortainerModule):
        super().__init__(
            module=module,
            docker_endpoint="/secrets",
            name_field="Name",
            id_field="ID",
            resource_name="swarm secret",
        )


class DockerNetworkCRUD(BaseDockerCRUD):

    def __init__(self, module: PortainerModule):
        super().__init__(
            module=module,
            docker_endpoint="/networks",
            name_field="Name",
            id_field="Id",
            resource_name="docker network",
        )


class PortainerCRUD:

    class exc:
        ItemNotExists = ItemNotExists
        MultipleItemsReturned = MultipleItemsReturned
        PortainerCRUDException = PortainerCRUDException

    def __init__(self, module: PortainerModule) -> None:
        self.module = module
        self.group = EndpointGroupCRUD(module)
        self.tag = TagCRUD(module)
        self.environment = EnvironmentCRUD(module)
        self.stack = StackCRUD(module)

        self.swarm = SwarmCRUD(module)
        self.swarm_config = SwarmConfigCRUD(module)
        self.swarm_secret = SwarmSecretCRUD(module)
        self.docker_network = DockerNetworkCRUD(module)
