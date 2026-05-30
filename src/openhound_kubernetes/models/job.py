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
from openhound_kubernetes.graph import resource_permission_path
from openhound_kubernetes.kinds import edges as ek
from openhound_kubernetes.kinds import nodes as nk
from openhound_kubernetes.main import app


class OwnerReferences(BaseModel):
    model_config = ConfigDict(extra="ignore")

    api_version: str | None = None
    controller: bool | None = None
    kind: str
    name: str
    uid: str | None = None


class Metadata(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    uid: str
    namespace: str
    creation_timestamp: datetime | None = None
    labels: dict | None = None
    owner_references: list[OwnerReferences] | None = None


@app.asset(
    description="Kubernetes Job asset.",
    node=NodeDef(
        properties=K8SNodeProperties,
        kind=nk.JOB,
        description="Kubernetes Job",
        icon="briefcase",
        color="#68bc00",
    ),
    edges=[
        EdgeDef(
            start=nk.CLUSTER,
            end=nk.JOB,
            kind=ek.CONTAINS,
            description="Cluster contains resource",
        ),
        EdgeDef(
            start=nk.JOB,
            end=nk.NAMESPACE,
            kind=ek.BELONGS_TO,
            description="Job belongs to a namespace",
        ),
        EdgeDef(
            start=nk.JOB,
            end=nk.CRON_JOB,
            kind=ek.OWNED_BY,
            description="Job is owned by a CronJob",
        ),
        EdgeDef(
            start=nk.JOB,
            end=nk.RESOURCE,
            kind=ek.OWNED_BY,
            description="Job is owned by a Kubernetes resource",
        ),
    ],
)
class Job(BaseAsset):
    kind: str | None = "Job"
    metadata: Metadata

    @field_validator("kind", mode="before")
    @classmethod
    def set_default_if_none(cls, value):
        return value if value is not None else "Job"

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
        return K8SNode(kinds=[nk.JOB], properties=properties)

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
        if self.metadata.owner_references:
            for owner in self.metadata.owner_references:
                yield Edge(
                    kind=ek.OWNED_BY,
                    start=start_path,
                    end=resource_permission_path(
                        name=owner.name,
                        kind=owner.kind,
                        namespace=self.metadata.namespace,
                        cluster=self._extras["cluster"],
                    ),
                )
