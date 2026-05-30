from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime

from dlt.common import json
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
    host_path: HostPath | None = None


class TemplateSpec(BaseModel):
    containers: list[Container] | None = None
    volumes: list[Volume] | None = None


class Template(BaseModel):
    # metadata: Metadata
    spec: TemplateSpec


class Spec(BaseModel):
    template: Template


@dataclass
class ExtendedProperties(K8SNodeProperties):
    namespace: str


@app.asset(
    description="Kubernetes Deployment asset. Contains no direct edges, but serves as a parent for all pods created by the Deployment.",
    node=NodeDef(
        properties=ExtendedProperties,
        kind=nk.DEPLOYMENT,
        description="Kube deployment",
        icon="rocket",
        color="#68bc00",
    ),
    edges=[
        EdgeDef(
            start=nk.CLUSTER,
            end=nk.DEPLOYMENT,
            kind=ek.CONTAINS,
            description="Cluster contains resource",
        ),
    ],
)
class Deployment(BaseAsset):
    kind: str | None = "Deployment"
    metadata: Metadata
    spec: Spec

    @field_validator("kind", mode="before")
    def set_default_if_none(cls, v):
        return v if v is not None else "Deployment"

    @field_validator("metadata", "spec", mode="before")
    @classmethod
    def parse_json_string(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v

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
        return K8SNode(kinds=[nk.DEPLOYMENT], properties=properties)

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
