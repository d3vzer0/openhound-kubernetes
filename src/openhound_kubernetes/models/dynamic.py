from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime

from openhound.core.asset import BaseAsset
from openhound.core.asset import EdgeDef, NodeDef
from pydantic import BaseModel, ConfigDict

from openhound_kubernetes.graph import (
    Edge,
    EdgePath,
    K8SNode,
    K8SNodeProperties,
)
from openhound_kubernetes.graph import cluster_node_id
from openhound_kubernetes.graph import labels_to_list
from openhound_kubernetes.graph import match_by_properties
from openhound_kubernetes.kinds import edges as ek
from openhound_kubernetes.kinds import nodes as nk
from openhound_kubernetes.main import app

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
    "*": ek.CAN_ALL,
}


class Metadata(BaseModel):
    name: str
    uid: str
    namespace: str
    creation_timestamp: datetime | None = None
    labels: dict = {}
    annotations: dict = {}


class SourceRole(BaseModel):
    name: str
    uid: str
    permissions: list[str]


@dataclass
class ExtendedProperties(K8SNodeProperties):
    model_config = ConfigDict(extra="allow")
    # namespace: str


@app.asset(
    description="Dynamically discovered resource assets. Returns a generic asset and edges with namespace scope and role permissions",
    node=NodeDef(
        properties=ExtendedProperties,
        kind=nk.RESOURCE,
        description="Dynamically discovered resource",
        icon="shapes",
        color="#e6b65b",
    ),
    edges=[
        EdgeDef(
            start=nk.CLUSTER,
            end=nk.RESOURCE,
            kind=ek.CONTAINS,
            description="Cluster contains resource",
        ),
        EdgeDef(
            start=nk.RESOURCE,
            end=nk.NAMESPACE,
            kind=ek.BELONGS_TO,
            description="Resource belongs to a namespace",
        ),
        EdgeDef(
            start=nk.SCOPED_ROLE,
            end=nk.RESOURCE,
            kind=ek.CAN_ALL,
            description="Permissions from source role to dynamic resource",
        ),
        EdgeDef(
            start=nk.SCOPED_ROLE,
            end=nk.RESOURCE,
            kind=ek.CAN_CREATE,
            description="Permissions from source role to dynamic resource",
        ),
        EdgeDef(
            start=nk.SCOPED_ROLE,
            end=nk.RESOURCE,
            kind=ek.CAN_DELETE,
            description="Permissions from source role to dynamic resource",
        ),
        EdgeDef(
            start=nk.SCOPED_ROLE,
            end=nk.RESOURCE,
            kind=ek.CAN_DELETE_COLLECTION,
            description="Permissions from source role to dynamic resource",
        ),
        EdgeDef(
            start=nk.SCOPED_ROLE,
            end=nk.RESOURCE,
            kind=ek.CAN_GET,
            description="Permissions from source role to dynamic resource",
        ),
        EdgeDef(
            start=nk.SCOPED_ROLE,
            end=nk.RESOURCE,
            kind=ek.CAN_LIST,
            description="Permissions from source role to dynamic resource",
        ),
        EdgeDef(
            start=nk.SCOPED_ROLE,
            end=nk.RESOURCE,
            kind=ek.CAN_PATCH,
            description="Permissions from source role to dynamic resource",
        ),
        EdgeDef(
            start=nk.SCOPED_ROLE,
            end=nk.RESOURCE,
            kind=ek.CAN_PROXY,
            description="Permissions from source role to dynamic resource",
        ),
        EdgeDef(
            start=nk.SCOPED_ROLE,
            end=nk.RESOURCE,
            kind=ek.CAN_UPDATE,
            description="Permissions from source role to dynamic resource",
        ),
        EdgeDef(
            start=nk.SCOPED_ROLE,
            end=nk.RESOURCE,
            kind=ek.CAN_WATCH,
            description="Permissions from source role to dynamic resource",
        ),
    ],
)
class DynamicResource(BaseAsset):
    kind: str
    role: SourceRole
    metadata: Metadata

    @property
    def as_node(self) -> "K8SNode":
        properties = ExtendedProperties(
            name=self.metadata.name,
            displayname=self.metadata.name,
            resource_kind=self.kind,
            labels=labels_to_list(self.metadata.labels),
            namespace=self.metadata.namespace,
            uid=self.metadata.uid,
            cluster=self._extras["cluster"],
            environmentid=cluster_node_id(self._extras["cluster"]),
        )
        node = K8SNode(
            kinds=[nk.RESOURCE],
            properties=properties,
        )
        scope = self.metadata.namespace if self.metadata.namespace else "__global__"
        node.id = K8SNode.guid(
            self.metadata.name,
            f"{nk.RESOURCE}:{self.kind}",
            self._extras["cluster"],
            scope,
        )
        return node

    @property
    def _namespace_edge(self) -> Iterator[Edge]:
        # target_id = self._lookup.namespaces(self.properties.namespace)
        start_path = EdgePath(value=self.as_node.id, match_by="id")
        end_path = match_by_properties(
            nk.NAMESPACE,
            name=self.metadata.namespace,
            cluster=self._extras["cluster"],
        )
        yield Edge(kind=ek.BELONGS_TO, start=start_path, end=end_path)

    @property
    def _role_edge(self) -> Iterator[Edge]:
        for permission in self.role.permissions:
            end_path = EdgePath(value=self.as_node.id, match_by="id")
            start_path = EdgePath(value=self.role.uid, match_by="id")
            mapped_permission = VERB_TO_PERMISSION[permission]
            yield Edge(kind=mapped_permission, start=start_path, end=end_path)

    @property
    def _cluster_contains_edge(self) -> Iterator[Edge]:
        node = self.as_node
        yield Edge(
            kind=ek.CONTAINS,
            start=EdgePath(value=node.properties.environmentid, match_by="id"),
            end=EdgePath(value=node.id, match_by="id"),
        )

    @property
    def edges(self) -> Iterator[Edge]:
        yield from self._cluster_contains_edge
        yield from self._namespace_edge
        yield from self._role_edge
