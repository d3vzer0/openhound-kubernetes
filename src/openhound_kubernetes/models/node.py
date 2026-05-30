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
    creation_timestamp: datetime
    labels: dict = {}


@app.asset(
    description="Kubernetes node asset. Returns a node with edges specifying cluster membership.",
    node=NodeDef(
        properties=K8SNodeProperties,
        kind=nk.NODE,
        description="Kubernetes node",
        icon="server",
        color="#4971bc",
    ),
    edges=[
        EdgeDef(
            start=nk.CLUSTER,
            end=nk.NODE,
            kind=ek.CONTAINS,
            description="Cluster contains resource",
        ),
        EdgeDef(
            start=nk.NODE,
            end=nk.CLUSTER,
            kind=ek.BELONGS_TO,
            description="Node belongs to the cluster",
        ),
        EdgeDef(
            start=nk.NODE,
            end=nk.GROUP,
            kind=ek.MEMBER_OF,
            description="Node is a member of system groups",
        ),
    ],
)
class KubeNode(BaseAsset):
    metadata: Metadata
    kind: str | None = "Node"

    @field_validator("kind", mode="before")
    def set_default_if_none(cls, v):
        return v if v is not None else "Node"

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
        return K8SNode(kinds=[nk.NODE], properties=properties)

    @property
    def _cluster_contains_edge(self) -> Iterator[Edge]:
        node = self.as_node
        yield Edge(
            kind=ek.CONTAINS,
            start=EdgePath(value=node.properties.environmentid, match_by="id"),
            end=EdgePath(value=node.id, match_by="id"),
        )

    @property
    def _authenticated_group_edge(self) -> Iterator[Edge]:
        start_path = EdgePath(value=self.as_node.id, match_by="id")
        end_path = match_by_properties(
            nk.GROUP,
            name="system:authenticated",
            cluster=self._extras["cluster"],
        )
        yield Edge(kind=ek.MEMBER_OF, start=start_path, end=end_path)

    @property
    def _nodes_group_edge(self) -> Iterator[Edge]:
        start_path = EdgePath(value=self.as_node.id, match_by="id")
        end_path = match_by_properties(
            nk.GROUP,
            name="system:nodes",
            cluster=self._extras["cluster"],
        )
        yield Edge(kind=ek.MEMBER_OF, start=start_path, end=end_path)

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
        yield from self._authenticated_group_edge
        yield from self._nodes_group_edge
