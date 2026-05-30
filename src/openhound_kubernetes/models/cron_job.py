from collections.abc import Iterator
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


@app.asset(
    description="Kubernetes CronJob asset.",
    node=NodeDef(
        properties=K8SNodeProperties,
        kind=nk.CRON_JOB,
        description="Kubernetes CronJob",
        icon="clock",
        color="#68bc00",
    ),
    edges=[
        EdgeDef(
            start=nk.CLUSTER,
            end=nk.CRON_JOB,
            kind=ek.CONTAINS,
            description="Cluster contains resource",
        ),
        EdgeDef(
            start=nk.CRON_JOB,
            end=nk.NAMESPACE,
            kind=ek.BELONGS_TO,
            description="CronJob belongs to a namespace",
        ),
    ],
)
class CronJob(BaseAsset):
    kind: str | None = "CronJob"
    metadata: Metadata

    @field_validator("kind", mode="before")
    @classmethod
    def set_default_if_none(cls, value):
        return value if value is not None else "CronJob"

    @property
    def as_node(self) -> K8SNode:
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
        return K8SNode(kinds=[nk.CRON_JOB], properties=properties)

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
