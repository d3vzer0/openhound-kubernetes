from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime

from openhound.core.asset import BaseAsset, EdgeDef, NodeDef
from pydantic import BaseModel, ConfigDict, field_validator

from openhound_kubernetes.graph import Edge, EdgePath, K8SNode, K8SNodeProperties
from openhound_kubernetes.graph import cluster_node_id, labels_to_list
from openhound_kubernetes.kinds import edges as ek
from openhound_kubernetes.kinds import nodes as nk
from openhound_kubernetes.main import app


class Metadata(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    uid: str
    creation_timestamp: datetime | None = None
    labels: dict | None = None


class Spec(BaseModel):
    model_config = ConfigDict(extra="ignore")

    storage_class_name: str | None = None


@dataclass
class PersistentVolumeProperties(K8SNodeProperties):
    """Properties for Kubernetes PersistentVolume nodes.

    Attributes:
        storage_class_name: StorageClass name for the PersistentVolume.
    """

    storage_class_name: str | None = None


@app.asset(
    description="Kubernetes PersistentVolume asset.",
    node=NodeDef(
        properties=PersistentVolumeProperties,
        kind=nk.PERSISTENT_VOLUME,
        description="Kubernetes PersistentVolume",
        icon="hard-drive",
        color="#ff746c",
    ),
    edges=[
        EdgeDef(
            start=nk.CLUSTER,
            end=nk.PERSISTENT_VOLUME,
            kind=ek.CONTAINS,
            description="Cluster contains resource",
        ),
    ],
)
class PersistentVolume(BaseAsset):
    kind: str | None = "PersistentVolume"
    metadata: Metadata
    spec: Spec | None = None

    @field_validator("kind", mode="before")
    @classmethod
    def set_default_if_none(cls, value):
        return value if value is not None else "PersistentVolume"

    @property
    def as_node(self) -> K8SNode:
        properties = PersistentVolumeProperties(
            name=self.metadata.name,
            displayname=self.metadata.name,
            resource_kind=self.kind,
            labels=labels_to_list(self.metadata.labels),
            namespace=None,
            uid=self.metadata.uid,
            cluster=self._extras["cluster"],
            environmentid=cluster_node_id(self._extras["cluster"]),
            storage_class_name=self.spec.storage_class_name if self.spec else None,
        )
        return K8SNode(kinds=[nk.PERSISTENT_VOLUME], properties=properties)

    @property
    def edges(self) -> Iterator[Edge]:
        node = self.as_node
        yield Edge(
            kind=ek.CONTAINS,
            start=EdgePath(value=node.properties.environmentid, match_by="id"),
            end=EdgePath(value=node.id, match_by="id"),
        )
