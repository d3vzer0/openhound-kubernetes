from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime

from openhound.core.asset import EdgeDef, NodeDef, BaseAsset
from pydantic import BaseModel, ConfigDict, field_validator

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
    model_config = ConfigDict(extra="ignore")

    name: str
    uid: str
    namespace: str
    creation_timestamp: datetime | None = None
    labels: dict | None = None


@dataclass
class SecretProperties(K8SNodeProperties):
    """Properties for Kubernetes Secret nodes.

    Attributes:
        secret_type: Kubernetes Secret type, excluding secret payload data.
        immutable: Whether the Secret is immutable.
    """

    secret_type: str | None = None
    immutable: bool | None = None


@app.asset(
    description="Kubernetes Secret asset. Returns metadata only and never stores secret contents.",
    node=NodeDef(
        properties=SecretProperties,
        kind=nk.SECRET,
        description="Kubernetes Secret metadata",
        icon="key",
        color="#ff746c",
    ),
    edges=[
        EdgeDef(
            start=nk.CLUSTER,
            end=nk.SECRET,
            kind=ek.CONTAINS,
            description="Cluster contains resource",
        ),
        EdgeDef(
            start=nk.SECRET,
            end=nk.NAMESPACE,
            kind=ek.BELONGS_TO,
            description="Secret belongs to a namespace",
        ),
    ],
)
class Secret(BaseAsset):
    model_config = ConfigDict(extra="ignore")

    kind: str | None = "Secret"
    metadata: Metadata
    type: str | None = None
    immutable: bool | None = None

    @field_validator("kind", mode="before")
    @classmethod
    def set_default_if_none(cls, value):
        return value if value is not None else "Secret"

    @property
    def as_node(self) -> K8SNode:
        properties = SecretProperties(
            name=self.metadata.name,
            displayname=self.metadata.name,
            resource_kind=self.kind,
            labels=labels_to_list(self.metadata.labels),
            namespace=self.metadata.namespace,
            uid=self.metadata.uid,
            cluster=self._extras["cluster"],
            environmentid=cluster_node_id(self._extras["cluster"]),
            secret_type=self.type,
            immutable=self.immutable,
        )
        return K8SNode(kinds=[nk.SECRET], properties=properties)

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

    @property
    def edges(self) -> Iterator[Edge]:
        yield from self._cluster_contains_edge
        yield from self._namespace_edge
