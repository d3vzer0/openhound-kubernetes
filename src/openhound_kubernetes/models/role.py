import fnmatch
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from openhound.core.asset import BaseAsset
from openhound.core.asset import EdgeDef, NodeDef
from pydantic import BaseModel, field_validator

from openhound_kubernetes.graph import (
    K8SNode,
    K8SNodeProperties,
    Edge,
    EdgePath,
    EdgeProperties,
    cluster_node_id,
    labels_to_list,
    match_by_properties,
    resource_definition_path,
    resource_permission_path,
)
from openhound_kubernetes.kinds import edges as ek, nodes as nk
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
    wildcard = "*"
    impersonate = "impersonate"
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


class Spec(BaseModel):
    node_name: str


class Metadata(BaseModel):
    name: str
    uid: str
    namespace: str
    creation_timestamp: datetime | None = None
    labels: dict | None = None


class Rule(BaseModel):
    api_groups: list[str] = ["__core__"]
    resources: list[str]
    verbs: list[Verbs]
    resource_names: Optional[list[str]] = None

    @field_validator("api_groups")
    def validate_api_groups(cls, v):
        if not v or (len(v) == 1 and v[0] == ""):
            return ["__core__"]
        return v


@dataclass
class ExtendedProperties(K8SNodeProperties):
    namespace: str
    rules: list[str] = field(default_factory=list)


@dataclass
class ExtendedEdgeProperties(EdgeProperties):
    verbs: list[str]


@app.asset(
    description="Namespaced role asset. Returns a Role node with edges specifying permission bindings.",
    node=NodeDef(
        properties=ExtendedProperties,
        kind=nk.SCOPED_ROLE,
        description="Namespaced role",
        icon="id-badge",
        color="#3e8e41",
    ),
    edges=[
        EdgeDef(
            start=nk.CLUSTER,
            end=nk.SCOPED_ROLE,
            kind=ek.CONTAINS,
            description="Cluster contains resource",
        ),
        EdgeDef(
            start=nk.SCOPED_ROLE,
            end=nk.NAMESPACE,
            kind=ek.BELONGS_TO,
            description="Role belongs to a namespace",
        ),
        EdgeDef(
            start=nk.SCOPED_ROLE,
            end=nk.RESOURCE,
            kind=ek.HAS_PERMISSIONS,
            description="Role grants permissions to namespaced resources",
        ),
        EdgeDef(
            start=nk.SCOPED_ROLE,
            end=nk.CLUSTER_ROLE,
            kind=ek.HAS_PERMISSIONS,
            description="Role grants permissions to namespaced resources",
        ),
        EdgeDef(
            start=nk.SCOPED_ROLE,
            end=nk.CLUSTER_ROLE_BINDING,
            kind=ek.HAS_PERMISSIONS,
            description="Role grants permissions to namespaced resources",
        ),
        EdgeDef(
            start=nk.SCOPED_ROLE,
            end=nk.CONFIG_MAP,
            kind=ek.HAS_PERMISSIONS,
            description="Role grants permissions to namespaced resources",
        ),
        EdgeDef(
            start=nk.SCOPED_ROLE,
            end=nk.CRON_JOB,
            kind=ek.HAS_PERMISSIONS,
            description="Role grants permissions to namespaced resources",
        ),
        EdgeDef(
            start=nk.SCOPED_ROLE,
            end=nk.DAEMON_SET,
            kind=ek.HAS_PERMISSIONS,
            description="Role grants permissions to namespaced resources",
        ),
        EdgeDef(
            start=nk.SCOPED_ROLE,
            end=nk.DEPLOYMENT,
            kind=ek.HAS_PERMISSIONS,
            description="Role grants permissions to namespaced resources",
        ),
        EdgeDef(
            start=nk.SCOPED_ROLE,
            end=nk.NAMESPACE,
            kind=ek.HAS_PERMISSIONS,
            description="Role grants permissions to namespaced resources",
        ),
        EdgeDef(
            start=nk.SCOPED_ROLE,
            end=nk.JOB,
            kind=ek.HAS_PERMISSIONS,
            description="Role grants permissions to namespaced resources",
        ),
        EdgeDef(
            start=nk.SCOPED_ROLE,
            end=nk.NODE,
            kind=ek.HAS_PERMISSIONS,
            description="Role grants permissions to namespaced resources",
        ),
        EdgeDef(
            start=nk.SCOPED_ROLE,
            end=nk.POD,
            kind=ek.HAS_PERMISSIONS,
            description="Role grants permissions to namespaced resources",
        ),
        EdgeDef(
            start=nk.SCOPED_ROLE,
            end=nk.PERSISTENT_VOLUME,
            kind=ek.HAS_PERMISSIONS,
            description="Role grants permissions to namespaced resources",
        ),
        EdgeDef(
            start=nk.SCOPED_ROLE,
            end=nk.PERSISTENT_VOLUME_CLAIM,
            kind=ek.HAS_PERMISSIONS,
            description="Role grants permissions to namespaced resources",
        ),
        EdgeDef(
            start=nk.SCOPED_ROLE,
            end=nk.REPLICA_SET,
            kind=ek.HAS_PERMISSIONS,
            description="Role grants permissions to namespaced resources",
        ),
        EdgeDef(
            start=nk.SCOPED_ROLE,
            end=nk.SCOPED_ROLE,
            kind=ek.HAS_PERMISSIONS,
            description="Role grants permissions to namespaced resources",
        ),
        EdgeDef(
            start=nk.SCOPED_ROLE,
            end=nk.SCOPED_ROLE_BINDING,
            kind=ek.HAS_PERMISSIONS,
            description="Role grants permissions to namespaced resources",
        ),
        EdgeDef(
            start=nk.SCOPED_ROLE,
            end=nk.SERVICE_ACCOUNT,
            kind=ek.HAS_PERMISSIONS,
            description="Role grants permissions to namespaced resources",
        ),
        EdgeDef(
            start=nk.SCOPED_ROLE,
            end=nk.SECRET,
            kind=ek.HAS_PERMISSIONS,
            description="Role grants permissions to namespaced resources",
        ),
        EdgeDef(
            start=nk.SCOPED_ROLE,
            end=nk.STATEFUL_SET,
            kind=ek.HAS_PERMISSIONS,
            description="Role grants permissions to namespaced resources",
        ),
        EdgeDef(
            start=nk.SCOPED_ROLE,
            end=nk.RESOURCE_DEFINITION,
            kind=ek.CAN_CREATE,
            description="Role can create a resource kind",
        ),
    ],
)
class Role(BaseAsset):
    metadata: Metadata
    rules: Optional[list[Rule]] = []
    kind: str | None = "Role"

    @field_validator("kind", mode="before")
    def set_default_if_none(cls, v):
        return v if v is not None else "Role"

    @property
    def as_node(self) -> "K8SNode":
        properties = ExtendedProperties(
            # rules=self.rules,
            name=self.metadata.name,
            displayname=self.metadata.name,
            resource_kind=self.kind,
            labels=labels_to_list(self.metadata.labels),
            namespace=self.metadata.namespace,
            uid=self.metadata.uid,
            cluster=self._extras["cluster"],
            environmentid=cluster_node_id(self._extras["cluster"]),
        )
        return K8SNode(
            kinds=[nk.SCOPED_ROLE, nk.ROLE],
            properties=properties,
        )

    def _matching_verbs(self, verbs: list) -> list:
        matched = []
        for verb in verbs:
            for key in VERB_TO_PERMISSION.keys():
                if fnmatch.fnmatch(key, verb.value) and key != "*":
                    matched.append(key)
        return matched

    @property
    def _cluster_contains_edge(self) -> Iterator[Edge]:
        node = self.as_node
        yield Edge(
            kind=ek.CONTAINS,
            start=EdgePath(value=node.properties.environmentid, match_by="id"),
            end=EdgePath(value=node.id, match_by="id"),
        )

    @property
    def _namespace_edge(self) -> Iterator[Edge]:
        start_path = EdgePath(value=self.as_node.id, match_by="id")
        end_path = match_by_properties(
            nk.NAMESPACE,
            name=self.metadata.namespace,
            cluster=self._extras["cluster"],
        )
        yield Edge(kind=ek.BELONGS_TO, start=start_path, end=end_path)

    def _rule_edge(self, rule: Rule) -> Iterator[Edge]:
        if not rule.api_groups or not rule.resources:
            return

        start_path = EdgePath(value=self.as_node.id, match_by="id")
        matched_verbs = self._matching_verbs(rule.verbs)
        namespace = self.metadata.namespace
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

            allowed_resources = self._lookup.allowed_namespaced_resources(
                resource, namespace
            )
            for name, kind, r_namespace, singular, rd in allowed_resources:
                yield Edge(
                    kind=ek.HAS_PERMISSIONS,
                    start=start_path,
                    end=resource_permission_path(
                        name=name,
                        kind=kind,
                        namespace=r_namespace,
                        cluster=self._extras["cluster"],
                    ),
                    properties=ExtendedEdgeProperties(verbs=matched_verbs),
                )

    @property
    def _rules_edge(self) -> Iterator[Edge]:
        for rule in self.rules:
            yield from self._rule_edge(rule)

    @property
    def edges(self) -> Iterator[Edge]:
        yield from self._cluster_contains_edge
        yield from self._namespace_edge
        yield from self._rules_edge
