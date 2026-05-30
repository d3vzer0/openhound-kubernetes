from collections.abc import Iterator
from dataclasses import dataclass

from openhound.core.asset import BaseAsset
from openhound.core.asset import EdgeDef, NodeDef
from pydantic import computed_field

from openhound_kubernetes.graph import (
    K8SNode,
    K8SNodeProperties,
    Edge,
    EdgePath,
    cluster_node_id,
    match_by_properties,
)
from openhound_kubernetes.kinds import edges as ek, nodes as nk
from openhound_kubernetes.main import app


@dataclass
class ExtendedProperties(K8SNodeProperties):
    node_name: str


@app.asset(
    description="HostPath-based volume asset. Returns a Volume node with an edge specifying the node it resides on. PS. Not a native Kubernetes resource.",
    node=NodeDef(
        properties=ExtendedProperties,
        kind=nk.VOLUME,
        description="HostPath-based volume",
        icon="hard-drive",
        color="#ff746c",
    ),
    edges=[
        EdgeDef(
            start=nk.CLUSTER,
            end=nk.VOLUME,
            kind=ek.CONTAINS,
            description="Cluster contains resource",
        ),
        EdgeDef(
            start=nk.VOLUME,
            end=nk.NODE,
            kind=ek.HOSTED_ON,
            description="Volume resides on the physical/virtual node",
        ),
    ],
)
class Volume(BaseAsset):
    node_name: str
    path: str

    # cluster: str

    @computed_field
    @property
    def name(self) -> str:
        return f"fs://{self.node_name}{self.path}"

    @computed_field
    @property
    def uid(self) -> str:
        return K8SNode.guid(self.name, nk.VOLUME, "")

    @property
    def as_node(self) -> "K8SNode":
        properties = ExtendedProperties(
            name=self.name,
            displayname=self.name,
            resource_kind=nk.VOLUME,
            labels=None,
            node_name=self.node_name,
            namespace=None,
            uid=self.uid,
            cluster=self._extras["cluster"],
            environmentid=cluster_node_id(self._extras["cluster"]),
        )
        return K8SNode(kinds=[nk.VOLUME], properties=properties)

    @property
    def _cluster_contains_edge(self) -> Iterator[Edge]:
        node = self.as_node
        yield Edge(
            kind=ek.CONTAINS,
            start=EdgePath(value=node.properties.environmentid, match_by="id"),
            end=EdgePath(value=node.id, match_by="id"),
        )

    @property
    def _node_edge(self) -> Iterator[Edge]:
        start_path = EdgePath(value=self.as_node.id, match_by="id")
        end_path = match_by_properties(
            nk.NODE,
            name=self.node_name,
            cluster=self._extras["cluster"],
        )
        yield Edge(kind=ek.HOSTED_ON, start=start_path, end=end_path)

    @property
    def edges(self) -> Iterator[Edge]:
        yield from self._cluster_contains_edge
        yield from self._node_edge
