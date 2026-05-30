from collections.abc import Iterator
from typing import Optional

from openhound.core.asset import BaseAsset
from openhound.core.asset import EdgeDef, NodeDef
from pydantic import BaseModel, computed_field

from openhound_kubernetes.graph import (
    K8SNode,
    K8SNodeProperties,
    Edge,
    EdgePath,
    cluster_node_id,
)
from openhound_kubernetes.kinds import edges as ek, nodes as nk
from openhound_kubernetes.main import app


class GroupVersion(BaseModel):
    group_version: str
    version: str


@app.asset(
    description="Kubernetes API group asset. Returns a ResourceGroup node with no direct edges. Resource membership is determined by edges from Resource nodes.",
    node=NodeDef(
        properties=K8SNodeProperties,
        kind=nk.RESOURCE_GROUP,
        description="Kubernetes API group",
        icon="layer-group",
        color="#fb9e00",
    ),
    edges=[
        EdgeDef(
            start=nk.CLUSTER,
            end=nk.RESOURCE_GROUP,
            kind=ek.CONTAINS,
            description="Cluster contains resource",
        ),
    ],
)
class ResourceGroup(BaseAsset):
    name: str
    api_version: Optional[str] = None

    @computed_field
    @property
    def uid(self) -> str:
        return K8SNode.guid(self.name, nk.RESOURCE_GROUP, "")

    @property
    def as_node(self) -> "K8SNode":
        properties = K8SNodeProperties(
            name=self.name,
            displayname=self.name,
            resource_kind=nk.RESOURCE_GROUP,
            labels=None,
            uid=self.uid,
            namespace=None,
            cluster=self._extras["cluster"],
            environmentid=cluster_node_id(self._extras["cluster"]),
        )
        return K8SNode(kinds=[nk.RESOURCE_GROUP], properties=properties)

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
