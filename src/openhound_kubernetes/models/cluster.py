from collections.abc import Iterator

from openhound.core.asset import BaseAsset, NodeDef
from pydantic import computed_field

from openhound_kubernetes.graph import (
    K8SNode,
    K8SNodeProperties,
    Edge,
)
from openhound_kubernetes.graph import cluster_node_id
from openhound_kubernetes.kinds import nodes as nk
from openhound_kubernetes.main import app


@app.asset(
    description="Kubernetes cluster asset. Contains no direct edges, but serves as a parent for all other nodes in the cluster.",
    node=NodeDef(
        properties=K8SNodeProperties,
        kind=nk.CLUSTER,
        description="Kubernetes cluster",
        icon="globe",
        color="#16a5a5",
    ),
)
class Cluster(BaseAsset):
    name: str
    kind: str = "Cluster"

    @computed_field
    @property
    def uid(self) -> str:
        return K8SNode.guid(self.name, nk.CLUSTER, self.name)

    @property
    def as_node(self) -> K8SNode:
        properties = K8SNodeProperties(
            name=self.name,
            displayname=self.name,
            resource_kind=self.kind,
            labels=None,
            uid=self.uid,
            namespace=None,
            cluster=self._extras["cluster"],
            environmentid=cluster_node_id(self._extras["cluster"]),
        )
        return K8SNode(kinds=[nk.CLUSTER], properties=properties)

    @property
    def edges(self) -> Iterator["Edge"]:
        yield from ()
