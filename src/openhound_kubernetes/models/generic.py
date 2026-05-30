from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime

from openhound.core.asset import BaseAsset
from openhound.core.asset import EdgeDef, NodeDef
from pydantic import BaseModel

from openhound_kubernetes.graph import (
    K8SNode,
    K8SNodeProperties,
    Edge,
    EdgePath,
)
from openhound_kubernetes.graph import cluster_node_id
from openhound_kubernetes.graph import labels_to_list
from openhound_kubernetes.kinds import edges as ek
from openhound_kubernetes.kinds import nodes as nk
from openhound_kubernetes.main import app


class Metadata(BaseModel):
    name: str
    uid: str | None = None
    namespace: str | None = None
    creation_timestamp: datetime | None = None
    labels: dict | None = None


@dataclass
class ExtendedProperties(K8SNodeProperties):
    uid: str | None


@app.asset(
    description="Unmapped Kubernetes resource asset. Returns a generic node with kind and UID properties, but no edges.",
    node=NodeDef(
        properties=ExtendedProperties,
        kind=nk.RESOURCE,
        description="Unmapped Kubernetes resource",
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
    ],
)
class Generic(BaseAsset):
    metadata: Metadata
    kind: str

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
        node = K8SNode(kinds=[nk.RESOURCE], properties=properties)
        scope = self.metadata.namespace if self.metadata.namespace else "__global__"
        node.id = K8SNode.guid(
            self.metadata.name,
            f"{nk.RESOURCE}:{self.kind}",
            self._extras["cluster"],
            scope,
        )
        return node

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
