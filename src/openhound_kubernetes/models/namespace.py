from collections.abc import Iterator
from datetime import datetime

from openhound.core.asset import BaseAsset
from openhound.core.asset import EdgeDef, NodeDef
from pydantic import BaseModel, field_validator

from openhound_kubernetes.graph import (
    K8SNode,
    K8SNodeProperties,
    Edge,
    EdgePath,
    cluster_node_id,
    labels_to_list,
    match_by_properties,
)
from openhound_kubernetes.kinds import edges as ek, nodes as nk
from openhound_kubernetes.main import app


class Metadata(BaseModel):
    name: str
    uid: str
    creation_timestamp: datetime | None = None
    labels: dict


@app.asset(
    description="Kubernetes Namespace asset. Returns a namespace node with edges specifying cluster membership.",
    node=NodeDef(
        properties=K8SNodeProperties,
        kind=nk.NAMESPACE,
        description="Kubernetes Namespace node",
        icon="folder-tree",
        color="#73d8ff",
    ),
    edges=[
        EdgeDef(
            start=nk.CLUSTER,
            end=nk.NAMESPACE,
            kind=ek.CONTAINS,
            description="Cluster contains resource",
        ),
        EdgeDef(
            start=nk.NAMESPACE,
            end=nk.CLUSTER,
            kind=ek.BELONGS_TO,
            description="Namespace belongs to the cluster",
        ),
    ],
)
class Namespace(BaseAsset):
    metadata: Metadata
    kind: str | None = "Namespace"

    @field_validator("kind", mode="before")
    @classmethod
    def set_default_if_none(cls, v):
        return v if v is not None else "Namespace"

    @property
    def as_node(self) -> "K8SNode":
        properties = K8SNodeProperties(
            name=self.metadata.name,
            displayname=self.metadata.name,
            resource_kind=self.kind,
            labels=labels_to_list(self.metadata.labels),
            uid=self.metadata.uid,
            namespace=None,
            cluster=self._extras["cluster"],
            environmentid=cluster_node_id(self._extras["cluster"]),
        )
        return K8SNode(kinds=[nk.NAMESPACE], properties=properties)

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

    @property
    def edges(self) -> Iterator[Edge]:
        yield from self._cluster_contains_edge
        yield from self._cluster_edge
