from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime

from openhound.core.asset import BaseAsset, EdgeDef, NodeDef
from pydantic import BaseModel, ConfigDict, field_validator

from openhound_kubernetes.graph import Edge, EdgePath, K8SNode, K8SNodeProperties
from openhound_kubernetes.graph import (
    cluster_node_id,
    labels_to_list,
    match_by_properties,
)
from openhound_kubernetes.kinds import edges as ek
from openhound_kubernetes.kinds import nodes as nk
from openhound_kubernetes.main import app


class Metadata(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    uid: str
    namespace: str
    creation_timestamp: datetime | None = None
    labels: dict | None = None


class Spec(BaseModel):
    model_config = ConfigDict(extra="ignore")

    volume_name: str | None = None
    storage_class_name: str | None = None


@dataclass
class PersistentVolumeClaimProperties(K8SNodeProperties):
    """Properties for Kubernetes PersistentVolumeClaim nodes.

    Attributes:
        volume_name: Bound PersistentVolume name when available.
        storage_class_name: StorageClass name requested by the claim.
    """

    volume_name: str | None = None
    storage_class_name: str | None = None


@app.asset(
    description="Kubernetes PersistentVolumeClaim asset.",
    node=NodeDef(
        properties=PersistentVolumeClaimProperties,
        kind=nk.PERSISTENT_VOLUME_CLAIM,
        description="Kubernetes PersistentVolumeClaim",
        icon="database",
        color="#ff746c",
    ),
    edges=[
        EdgeDef(
            start=nk.CLUSTER,
            end=nk.PERSISTENT_VOLUME_CLAIM,
            kind=ek.CONTAINS,
            description="Cluster contains resource",
        ),
        EdgeDef(
            start=nk.PERSISTENT_VOLUME_CLAIM,
            end=nk.NAMESPACE,
            kind=ek.BELONGS_TO,
            description="PersistentVolumeClaim belongs to a namespace",
        ),
        EdgeDef(
            start=nk.PERSISTENT_VOLUME_CLAIM,
            end=nk.PERSISTENT_VOLUME,
            kind=ek.BINDS_TO,
            description="PersistentVolumeClaim binds to a PersistentVolume",
        ),
    ],
)
class PersistentVolumeClaim(BaseAsset):
    kind: str | None = "PersistentVolumeClaim"
    metadata: Metadata
    spec: Spec | None = None

    @field_validator("kind", mode="before")
    @classmethod
    def set_default_if_none(cls, value):
        return value if value is not None else "PersistentVolumeClaim"

    @property
    def as_node(self) -> K8SNode:
        properties = PersistentVolumeClaimProperties(
            name=self.metadata.name,
            displayname=self.metadata.name,
            resource_kind=self.kind,
            labels=labels_to_list(self.metadata.labels),
            namespace=self.metadata.namespace,
            uid=self.metadata.uid,
            cluster=self._extras["cluster"],
            environmentid=cluster_node_id(self._extras["cluster"]),
            volume_name=self.spec.volume_name if self.spec else None,
            storage_class_name=self.spec.storage_class_name if self.spec else None,
        )
        return K8SNode(kinds=[nk.PERSISTENT_VOLUME_CLAIM], properties=properties)

    @property
    def edges(self) -> Iterator[Edge]:
        node = self.as_node
        start_path = EdgePath(value=node.id, match_by="id")
        yield Edge(
            kind=ek.CONTAINS,
            start=EdgePath(value=node.properties.environmentid, match_by="id"),
            end=start_path,
        )
        yield Edge(
            kind=ek.BELONGS_TO,
            start=start_path,
            end=match_by_properties(
                nk.NAMESPACE,
                name=self.metadata.namespace,
                cluster=self._extras["cluster"],
            ),
        )
        if self.spec and self.spec.volume_name:
            yield Edge(
                kind=ek.BINDS_TO,
                start=start_path,
                end=match_by_properties(
                    nk.PERSISTENT_VOLUME,
                    name=self.spec.volume_name,
                    cluster=self._extras["cluster"],
                ),
            )
