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
)
from openhound_kubernetes.kinds import edges as ek, nodes as nk
from openhound_kubernetes.main import app
from openhound_kubernetes.models.pod import Container


class Metadata(BaseModel):
    name: str
    uid: str
    namespace: str
    creation_timestamp: datetime | None = None
    labels: dict | None = {}

    @field_validator("labels", mode="before")
    def set_default_if_none(cls, v):
        return v if v is not None else {}


class HostPath(BaseModel):
    path: str


class Volume(BaseModel):
    name: str
    hostPath: HostPath | None = None


class TemplateSpec(BaseModel):
    containers: list[Container] | None = None
    volumes: list[Volume] | None = None


class Template(BaseModel):
    # metadata: Metadata
    spec: TemplateSpec


class Spec(BaseModel):
    template: Template


@app.asset(
    description="Kubernetes StatefulSet asset. Returns a StatefulSet node with edges specifying ownership by Deployments or other controllers.",
    node=NodeDef(
        properties=K8SNodeProperties,
        kind=nk.STATEFUL_SET,
        description="StatefulSet node",
        icon="database",
        color="#68bc00",
    ),
    edges=[
        EdgeDef(
            start=nk.CLUSTER,
            end=nk.STATEFUL_SET,
            kind=ek.CONTAINS,
            description="Cluster contains resource",
        ),
    ],
)
class StatefulSet(BaseAsset):
    kind: str | None = "StatefulSet"
    metadata: Metadata
    spec: Spec

    @field_validator("kind", mode="before")
    def set_default_if_none(cls, v):
        return v if v is not None else "StatefulSet"

    @property
    def as_node(self) -> "K8SNode":
        properties = K8SNodeProperties(
            name=self.metadata.name,
            displayname=self.metadata.name,
            resource_kind=self.kind,
            labels=labels_to_list(self.metadata.labels),
            namespace=self.metadata.namespace,
            uid=self.metadata.uid,
            cluster=self._extras["cluster"],
            environmentid=cluster_node_id(self._extras["cluster"]),
        )
        return K8SNode(kinds=[nk.STATEFUL_SET], properties=properties)

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
