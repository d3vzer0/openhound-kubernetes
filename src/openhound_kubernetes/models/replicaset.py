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
    resource_permission_path,
)
from openhound_kubernetes.kinds import edges as ek, nodes as nk
from openhound_kubernetes.main import app


class OwnerReferences(BaseModel):
    api_version: str
    controller: bool
    kind: str
    name: str
    uid: str


class Metadata(BaseModel):
    name: str
    uid: str
    namespace: str
    creation_timestamp: datetime | None = None
    labels: dict | None = {}
    owner_references: list[OwnerReferences] | None = None

    @field_validator("labels", mode="before")
    def set_default_if_none(cls, v):
        return v if v is not None else {}


@dataclass
class ExtendedProperties(K8SNodeProperties):
    namespace: str


@app.asset(
    description="Kubernetes ReplicaSet asset. Returns a ReplicaSet node with edges specifying ownership by Deployments or other controllers.",
    node=NodeDef(
        properties=ExtendedProperties,
        kind=nk.REPLICA_SET,
        description="ReplicaSet node",
        icon="copy",
        color="#68bc00",
    ),
    edges=[
        EdgeDef(
            start=nk.CLUSTER,
            end=nk.REPLICA_SET,
            kind=ek.CONTAINS,
            description="Cluster contains resource",
        ),
        EdgeDef(
            start=nk.REPLICA_SET,
            end=nk.CLUSTER_ROLE,
            kind=ek.OWNED_BY,
            description="ReplicaSet is owned by a Kubernetes resource",
        ),
        EdgeDef(
            start=nk.REPLICA_SET,
            end=nk.CLUSTER_ROLE_BINDING,
            kind=ek.OWNED_BY,
            description="ReplicaSet is owned by a Kubernetes resource",
        ),
        EdgeDef(
            start=nk.REPLICA_SET,
            end=nk.CONFIG_MAP,
            kind=ek.OWNED_BY,
            description="ReplicaSet is owned by a Kubernetes resource",
        ),
        EdgeDef(
            start=nk.REPLICA_SET,
            end=nk.CRON_JOB,
            kind=ek.OWNED_BY,
            description="ReplicaSet is owned by a Kubernetes resource",
        ),
        EdgeDef(
            start=nk.REPLICA_SET,
            end=nk.DAEMON_SET,
            kind=ek.OWNED_BY,
            description="ReplicaSet is owned by a Kubernetes resource",
        ),
        EdgeDef(
            start=nk.REPLICA_SET,
            end=nk.DEPLOYMENT,
            kind=ek.OWNED_BY,
            description="ReplicaSet is owned by a Kubernetes resource",
        ),
        EdgeDef(
            start=nk.REPLICA_SET,
            end=nk.NAMESPACE,
            kind=ek.OWNED_BY,
            description="ReplicaSet is owned by a Kubernetes resource",
        ),
        EdgeDef(
            start=nk.REPLICA_SET,
            end=nk.JOB,
            kind=ek.OWNED_BY,
            description="ReplicaSet is owned by a Kubernetes resource",
        ),
        EdgeDef(
            start=nk.REPLICA_SET,
            end=nk.NODE,
            kind=ek.OWNED_BY,
            description="ReplicaSet is owned by a Kubernetes resource",
        ),
        EdgeDef(
            start=nk.REPLICA_SET,
            end=nk.POD,
            kind=ek.OWNED_BY,
            description="ReplicaSet is owned by a Kubernetes resource",
        ),
        EdgeDef(
            start=nk.REPLICA_SET,
            end=nk.PERSISTENT_VOLUME,
            kind=ek.OWNED_BY,
            description="ReplicaSet is owned by a Kubernetes resource",
        ),
        EdgeDef(
            start=nk.REPLICA_SET,
            end=nk.PERSISTENT_VOLUME_CLAIM,
            kind=ek.OWNED_BY,
            description="ReplicaSet is owned by a Kubernetes resource",
        ),
        EdgeDef(
            start=nk.REPLICA_SET,
            end=nk.REPLICA_SET,
            kind=ek.OWNED_BY,
            description="ReplicaSet is owned by a Kubernetes resource",
        ),
        EdgeDef(
            start=nk.REPLICA_SET,
            end=nk.RESOURCE,
            kind=ek.OWNED_BY,
            description="ReplicaSet is owned by a Kubernetes resource",
        ),
        EdgeDef(
            start=nk.REPLICA_SET,
            end=nk.SCOPED_ROLE,
            kind=ek.OWNED_BY,
            description="ReplicaSet is owned by a Kubernetes resource",
        ),
        EdgeDef(
            start=nk.REPLICA_SET,
            end=nk.SCOPED_ROLE_BINDING,
            kind=ek.OWNED_BY,
            description="ReplicaSet is owned by a Kubernetes resource",
        ),
        EdgeDef(
            start=nk.REPLICA_SET,
            end=nk.SERVICE_ACCOUNT,
            kind=ek.OWNED_BY,
            description="ReplicaSet is owned by a Kubernetes resource",
        ),
        EdgeDef(
            start=nk.REPLICA_SET,
            end=nk.SECRET,
            kind=ek.OWNED_BY,
            description="ReplicaSet is owned by a Kubernetes resource",
        ),
        EdgeDef(
            start=nk.REPLICA_SET,
            end=nk.STATEFUL_SET,
            kind=ek.OWNED_BY,
            description="ReplicaSet is owned by a Kubernetes resource",
        ),
    ],
)
class ReplicaSet(BaseAsset):
    kind: str | None = "ReplicaSet"
    metadata: Metadata

    @field_validator("kind", mode="before")
    def set_default_if_none(cls, v):
        return v if v is not None else "ReplicaSet"

    @field_validator("metadata", mode="before")
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
        node = K8SNode(kinds=[nk.REPLICA_SET], properties=properties)
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
    def _owned_by(self) -> Iterator[Edge]:
        start_path = EdgePath(value=self.as_node.id, match_by="id")
        if self.metadata.owner_references:
            for owner in self.metadata.owner_references:
                end_path = resource_permission_path(
                    name=owner.name,
                    kind=owner.kind,
                    namespace=self.metadata.namespace,
                    cluster=self._extras["cluster"],
                )
                yield Edge(kind=ek.OWNED_BY, start=start_path, end=end_path)

    @property
    def edges(self) -> Iterator[Edge]:
        yield from self._cluster_contains_edge
        yield from self._owned_by
