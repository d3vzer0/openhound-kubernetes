from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime

from openhound.core.asset import BaseAsset
from openhound.core.asset import EdgeDef, NodeDef
from pydantic import BaseModel, field_validator

from openhound_kubernetes.graph import (
    K8SNode,
    K8SNodeProperties,
    Edge,
    EdgePath,
)
from openhound_kubernetes.graph import cluster_node_id
from openhound_kubernetes.graph import labels_to_list
from openhound_kubernetes.graph import match_by_properties
from openhound_kubernetes.kinds import edges as ek
from openhound_kubernetes.kinds import nodes as nk
from openhound_kubernetes.main import app


class Secret(BaseModel):
    field_path: str | None = None
    name: str
    namespace: str | None = None
    uid: str | None = None


class Subject(BaseModel):
    api_group: str | None = None
    kind: str
    name: str
    namespace: str | None = None


class RoleRef(BaseModel):
    api_group: str
    kind: str
    name: str


class Metadata(BaseModel):
    name: str
    uid: str
    namespace: str
    creation_timestamp: datetime
    labels: dict | None = None


@dataclass
class ExtendedProperties(K8SNodeProperties):
    namespace: str
    bla: str | None = None


@app.asset(
    description="Kubernetes service account asset. Returns a ServiceAccount node with edges specifying namespace and group memberships.",
    node=NodeDef(
        properties=ExtendedProperties,
        kind=nk.SERVICE_ACCOUNT,
        description="Kubernetes service account",
        icon="robot",
        color="#d33115",
    ),
    edges=[
        EdgeDef(
            start=nk.CLUSTER,
            end=nk.SERVICE_ACCOUNT,
            kind=ek.CONTAINS,
            description="Cluster contains resource",
        ),
        EdgeDef(
            start=nk.SERVICE_ACCOUNT,
            end=nk.NAMESPACE,
            kind=ek.BELONGS_TO,
            description="ServiceAccount belongs to a namespace",
        ),
        EdgeDef(
            start=nk.SERVICE_ACCOUNT,
            end=nk.GROUP,
            kind=ek.MEMBER_OF,
            description="ServiceAccount is a member of groups",
        ),
    ],
)
class ServiceAccount(BaseAsset):
    kind: str | None = "ServiceAccount"
    metadata: Metadata
    automount_service_account_token: bool | None = None
    secrets: list[Secret] | None = None
    exists: bool = True

    @field_validator("kind", mode="before")
    def set_default_if_none(cls, v):
        return v if v is not None else "ServiceAccount"

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
        return K8SNode(kinds=[nk.SERVICE_ACCOUNT], properties=properties)

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
    def _authenticated_group_edge(self) -> Iterator[Edge]:
        start_path = EdgePath(value=self.as_node.id, match_by="id")
        end_path = match_by_properties(
            nk.GROUP,
            name="system:authenticated",
            cluster=self._extras["cluster"],
        )
        yield Edge(kind=ek.MEMBER_OF, start=start_path, end=end_path)

    @property
    def _service_accounts_edge(self) -> Iterator[Edge]:
        start_path = EdgePath(value=self.as_node.id, match_by="id")
        end_path = match_by_properties(
            nk.GROUP,
            name="system:serviceaccounts",
            cluster=self._extras["cluster"],
        )
        yield Edge(kind=ek.MEMBER_OF, start=start_path, end=end_path)

    @property
    def edges(self) -> Iterator[Edge]:
        yield from self._cluster_contains_edge
        yield from self._namespace_edge
        yield from self._authenticated_group_edge
        yield from self._service_accounts_edge
