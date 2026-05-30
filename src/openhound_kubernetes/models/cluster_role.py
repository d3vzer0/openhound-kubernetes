import fnmatch
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Any

from dlt.common import json
from openhound.core.asset import EdgeDef, BaseAsset, NodeDef
from pydantic import BaseModel, field_validator

from openhound_kubernetes.graph import (
    K8SNode,
    K8SNodeProperties,
    Edge,
    EdgePath,
)
from openhound_kubernetes.graph import cluster_node_id
from openhound_kubernetes.graph import labels_to_list
from openhound_kubernetes.graph import match_by_properties
from openhound_kubernetes.graph import resource_definition_path
from openhound_kubernetes.graph import resource_permission_path
from openhound_kubernetes.kinds import edges as ek
from openhound_kubernetes.kinds import nodes as nk
from openhound_kubernetes.main import app


class Verbs(str, Enum):
    get = "get"
    list = "list"
    watch = "watch"
    create = "create"
    update = "update"
    patch = "patch"
    delete = "delete"
    deletecollection = "deletecollection"
    proxy = "proxy"
    impersonate = "impersonate"
    wildcard = "*"
    approve = "approve"
    sign = "sign"
    escalate = "escalate"
    bind = "bind"
    use = "use"

    def __str__(self):
        return self.value


VERB_TO_PERMISSION = {
    "get": ek.CAN_GET,
    "list": ek.CAN_LIST,
    "watch": ek.CAN_WATCH,
    "create": ek.CAN_CREATE,
    "update": ek.CAN_UPDATE,
    "patch": ek.CAN_PATCH,
    "delete": ek.CAN_DELETE,
    "deletecollection": ek.CAN_DELETE_COLLECTION,
    "proxy": ek.CAN_PROXY,
    "impersonate": ek.CAN_IMPERSONATE,
    "approve": ek.CAN_APPROVE,
    "sign": ek.CAN_SIGN,
    "escalate": ek.CAN_ESCALATE,
    "bind": ek.CAN_BIND,
    "*": ek.CAN_ALL,
    "use": ek.CAN_USE,
}


class Metadata(BaseModel):
    name: str
    uid: str
    creation_timestamp: datetime | None = None
    namespace: str | None = ""
    labels: dict | None = None


class Rule(BaseModel):
    api_groups: Optional[list[str]] = ["__core__"]
    resources: Optional[list[str]] = []
    verbs: list[Verbs]
    resource_names: Optional[list[str]] = None

    @field_validator("api_groups")
    def validate_api_groups(cls, v):
        if not v or (len(v) == 1 and v[0] == ""):
            return ["__core__"]
        return v


@dataclass
class ExtendedProperties(K8SNodeProperties): ...


@app.asset(
    description="Cluster-scoped role asset with edges specifying permission bindings",
    node=NodeDef(
        properties=ExtendedProperties,
        kind=nk.CLUSTER_ROLE,
        description="Cluster-scoped role",
        icon="clipboard-list",
        color="#3e8e41",
    ),
    edges=[
        EdgeDef(
            start=nk.CLUSTER,
            end=nk.CLUSTER_ROLE,
            kind=ek.CONTAINS,
            description="Cluster contains resource",
        ),
        EdgeDef(
            start=nk.CLUSTER_ROLE,
            end=nk.CLUSTER,
            kind=ek.BELONGS_TO,
            description="ClusterRole defined on the cluster",
        ),
        EdgeDef(
            start=nk.CLUSTER_ROLE,
            end=nk.RESOURCE,
            kind=ek.HAS_PERMISSIONS,
            description="ClusterRole grants permissions to resources",
        ),
        EdgeDef(
            start=nk.CLUSTER_ROLE,
            end=nk.CLUSTER_ROLE,
            kind=ek.HAS_PERMISSIONS,
            description="ClusterRole grants permissions to resources",
        ),
        EdgeDef(
            start=nk.CLUSTER_ROLE,
            end=nk.CLUSTER_ROLE_BINDING,
            kind=ek.HAS_PERMISSIONS,
            description="ClusterRole grants permissions to resources",
        ),
        EdgeDef(
            start=nk.CLUSTER_ROLE,
            end=nk.CONFIG_MAP,
            kind=ek.HAS_PERMISSIONS,
            description="ClusterRole grants permissions to resources",
        ),
        EdgeDef(
            start=nk.CLUSTER_ROLE,
            end=nk.CRON_JOB,
            kind=ek.HAS_PERMISSIONS,
            description="ClusterRole grants permissions to resources",
        ),
        EdgeDef(
            start=nk.CLUSTER_ROLE,
            end=nk.DAEMON_SET,
            kind=ek.HAS_PERMISSIONS,
            description="ClusterRole grants permissions to resources",
        ),
        EdgeDef(
            start=nk.CLUSTER_ROLE,
            end=nk.DEPLOYMENT,
            kind=ek.HAS_PERMISSIONS,
            description="ClusterRole grants permissions to resources",
        ),
        EdgeDef(
            start=nk.CLUSTER_ROLE,
            end=nk.NAMESPACE,
            kind=ek.HAS_PERMISSIONS,
            description="ClusterRole grants permissions to resources",
        ),
        EdgeDef(
            start=nk.CLUSTER_ROLE,
            end=nk.JOB,
            kind=ek.HAS_PERMISSIONS,
            description="ClusterRole grants permissions to resources",
        ),
        EdgeDef(
            start=nk.CLUSTER_ROLE,
            end=nk.NODE,
            kind=ek.HAS_PERMISSIONS,
            description="ClusterRole grants permissions to resources",
        ),
        EdgeDef(
            start=nk.CLUSTER_ROLE,
            end=nk.POD,
            kind=ek.HAS_PERMISSIONS,
            description="ClusterRole grants permissions to resources",
        ),
        EdgeDef(
            start=nk.CLUSTER_ROLE,
            end=nk.PERSISTENT_VOLUME,
            kind=ek.HAS_PERMISSIONS,
            description="ClusterRole grants permissions to resources",
        ),
        EdgeDef(
            start=nk.CLUSTER_ROLE,
            end=nk.PERSISTENT_VOLUME_CLAIM,
            kind=ek.HAS_PERMISSIONS,
            description="ClusterRole grants permissions to resources",
        ),
        EdgeDef(
            start=nk.CLUSTER_ROLE,
            end=nk.REPLICA_SET,
            kind=ek.HAS_PERMISSIONS,
            description="ClusterRole grants permissions to resources",
        ),
        EdgeDef(
            start=nk.CLUSTER_ROLE,
            end=nk.SCOPED_ROLE,
            kind=ek.HAS_PERMISSIONS,
            description="ClusterRole grants permissions to resources",
        ),
        EdgeDef(
            start=nk.CLUSTER_ROLE,
            end=nk.SCOPED_ROLE_BINDING,
            kind=ek.HAS_PERMISSIONS,
            description="ClusterRole grants permissions to resources",
        ),
        EdgeDef(
            start=nk.CLUSTER_ROLE,
            end=nk.SERVICE_ACCOUNT,
            kind=ek.HAS_PERMISSIONS,
            description="ClusterRole grants permissions to resources",
        ),
        EdgeDef(
            start=nk.CLUSTER_ROLE,
            end=nk.SECRET,
            kind=ek.HAS_PERMISSIONS,
            description="ClusterRole grants permissions to resources",
        ),
        EdgeDef(
            start=nk.CLUSTER_ROLE,
            end=nk.STATEFUL_SET,
            kind=ek.HAS_PERMISSIONS,
            description="ClusterRole grants permissions to resources",
        ),
        EdgeDef(
            start=nk.CLUSTER_ROLE,
            end=nk.RESOURCE_DEFINITION,
            kind=ek.CAN_CREATE,
            description="ClusterRole can create a resource kind",
        ),
    ],
)
class ClusterRole(BaseAsset):
    metadata: Metadata
    rules: list[Rule] = []
    kind: str | None = "ClusterRole"

    @field_validator("kind", mode="before")
    def set_default_if_none(cls, v):
        return v if v is not None else "ClusterRole"

    @field_validator("rules", mode="before")
    @classmethod
    def parse_rules(cls, value: Any):
        if isinstance(value, str):
            value = json.loads(value)
        return value or []

    @property
    def as_node(self) -> "K8SNode":
        properties = ExtendedProperties(
            name=self.metadata.name,
            displayname=self.metadata.name,
            resource_kind=self.kind,
            labels=labels_to_list(self.metadata.labels),
            # rules=self.rules,
            uid=self.metadata.uid,
            namespace=None,
            cluster=self._extras["cluster"],
            environmentid=cluster_node_id(self._extras["cluster"]),
        )
        return K8SNode(
            kinds=[nk.CLUSTER_ROLE, nk.ROLE],
            properties=properties,
        )

    @property
    def _cluster_contains_edge(self) -> Iterator[Edge]:
        node = self.as_node
        yield Edge(
            kind=ek.CONTAINS,
            start=EdgePath(value=node.properties.environmentid, match_by="id"),
            end=EdgePath(value=node.id, match_by="id"),
        )

    @property
    def _cluster_edge(self) -> Iterator[Edge]:
        start_path = EdgePath(value=self.as_node.id, match_by="id")
        end_path = match_by_properties(
            nk.CLUSTER,
            name=self._extras["cluster"],
            cluster=self._extras["cluster"],
        )
        yield Edge(kind=ek.BELONGS_TO, start=start_path, end=end_path)

    def _matching_verbs(self, verbs: list) -> list:
        matched = []
        for verb in verbs:
            for key in VERB_TO_PERMISSION.keys():
                if fnmatch.fnmatch(key, verb.value) and key != "*":
                    matched.append(key)
        return matched

    def _rule_edge(self, rule: Rule) -> Iterator[Edge]:
        if not rule.api_groups or not rule.resources:
            return

        start_path = EdgePath(value=self.as_node.id, match_by="id")
        matched_verbs = self._matching_verbs(rule.verbs)
        created_definitions = set()

        for resource in rule.resources:
            if "create" in matched_verbs:
                for (
                    name,
                    kind,
                    singular,
                    api_group_name,
                ) in self._lookup.allowed_resource_definitions(
                    resource, tuple(rule.api_groups)
                ):
                    definition_key = (name, api_group_name)
                    if definition_key in created_definitions:
                        continue
                    created_definitions.add(definition_key)
                    yield Edge(
                        kind=ek.CAN_CREATE,
                        start=start_path,
                        end=resource_definition_path(
                            name=name,
                            api_group_name=api_group_name,
                            cluster=self._extras["cluster"],
                        ),
                    )

            allowed_resources = self._lookup.allowed_system_resources(resource)
            for name, kind, namespace, singular, rd in allowed_resources:
                yield Edge(
                    kind=ek.HAS_PERMISSIONS,
                    start=start_path,
                    end=resource_permission_path(
                        name=name,
                        kind=kind,
                        namespace=namespace,
                        cluster=self._extras["cluster"],
                    ),
                    properties={"verbs": matched_verbs},
                )

    @property
    def _rules_edge(self) -> Iterator[Edge]:
        for rule in self.rules:
            yield from self._rule_edge(rule)

    @property
    def edges(self) -> Iterator[Edge]:
        yield from self._cluster_contains_edge
        yield from self._cluster_edge
        yield from self._rules_edge
