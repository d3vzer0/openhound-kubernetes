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


@dataclass
class ConfigMapProperties(K8SNodeProperties):
    """Properties for Kubernetes ConfigMap nodes.

    Attributes:
        data_keys: ConfigMap data keys without values.
        binary_data_keys: ConfigMap binaryData keys without values.
        immutable: Whether the ConfigMap is immutable.
    """

    data_keys: list[str] | None = None
    binary_data_keys: list[str] | None = None
    immutable: bool | None = None


@app.asset(
    description="Kubernetes ConfigMap asset. Returns keys only and never stores config values.",
    node=NodeDef(
        properties=ConfigMapProperties,
        kind=nk.CONFIG_MAP,
        description="Kubernetes ConfigMap metadata",
        icon="sliders",
        color="#73d8ff",
    ),
    edges=[
        EdgeDef(
            start=nk.CLUSTER,
            end=nk.CONFIG_MAP,
            kind=ek.CONTAINS,
            description="Cluster contains resource",
        ),
        EdgeDef(
            start=nk.CONFIG_MAP,
            end=nk.NAMESPACE,
            kind=ek.BELONGS_TO,
            description="ConfigMap belongs to a namespace",
        ),
    ],
)
class ConfigMap(BaseAsset):
    model_config = ConfigDict(extra="ignore")

    kind: str | None = "ConfigMap"
    metadata: Metadata
    data_keys: list[str] | None = None
    binary_data_keys: list[str] | None = None
    immutable: bool | None = None

    @field_validator("kind", mode="before")
    @classmethod
    def set_default_if_none(cls, value):
        return value if value is not None else "ConfigMap"

    @property
    def as_node(self) -> K8SNode:
        properties = ConfigMapProperties(
            name=self.metadata.name,
            displayname=self.metadata.name,
            resource_kind=self.kind,
            labels=labels_to_list(self.metadata.labels),
            namespace=self.metadata.namespace,
            uid=self.metadata.uid,
            cluster=self._extras["cluster"],
            environmentid=cluster_node_id(self._extras["cluster"]),
            data_keys=sorted(self.data_keys) if self.data_keys else None,
            binary_data_keys=sorted(self.binary_data_keys)
            if self.binary_data_keys
            else None,
            immutable=self.immutable,
        )
        return K8SNode(kinds=[nk.CONFIG_MAP], properties=properties)

    @property
    def edges(self) -> Iterator[Edge]:
        node = self.as_node
        yield Edge(
            kind=ek.CONTAINS,
            start=EdgePath(value=node.properties.environmentid, match_by="id"),
            end=EdgePath(value=node.id, match_by="id"),
        )
        yield Edge(
            kind=ek.BELONGS_TO,
            start=EdgePath(value=node.id, match_by="id"),
            end=match_by_properties(
                nk.NAMESPACE,
                name=self.metadata.namespace,
                cluster=self._extras["cluster"],
            ),
        )
