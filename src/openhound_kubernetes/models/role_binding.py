from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime

from openhound.core.asset import BaseAsset, EdgeDef, NodeDef
from pydantic import BaseModel, field_validator

from openhound_kubernetes.graph import (
    K8SNode,
    K8SNodeProperties,
    Edge,
    EdgePath,
    EdgeProperties,
)
from openhound_kubernetes.graph import cluster_node_id
from openhound_kubernetes.graph import labels_to_list
from openhound_kubernetes.graph import match_by_properties
from openhound_kubernetes.kinds import edges as ek
from openhound_kubernetes.kinds import nodes as nk
from openhound_kubernetes.main import app


# from pydantic.dataclasses import dataclass


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
    creation_timestamp: datetime | None = None
    labels: dict | None = None


@dataclass
class ExtendedProperties(K8SNodeProperties):
    role_ref: str
    subjects: list[str]


@app.asset(
    description="Namespaced role binding asset. Returns a RoleBinding node with edges specifying subject and role reference relationships.",
    node=NodeDef(
        properties=ExtendedProperties,
        kind=nk.SCOPED_ROLE_BINDING,
        description="Namespaced role binding",
        icon="link",
        color="#fda1ff",
    ),
    edges=[
        EdgeDef(
            start=nk.CLUSTER,
            end=nk.SCOPED_ROLE_BINDING,
            kind=ek.CONTAINS,
            description="Cluster contains resource",
        ),
        EdgeDef(
            start=nk.SCOPED_ROLE_BINDING,
            end=nk.NAMESPACE,
            kind=ek.BELONGS_TO,
            description="RoleBinding scoped to a namespace",
        ),
        EdgeDef(
            start=nk.SCOPED_ROLE_BINDING,
            end=nk.SCOPED_ROLE,
            kind=ek.REFERENCES_ROLE,
            description="RoleBinding references a Role",
        ),
        EdgeDef(
            start=nk.SCOPED_ROLE_BINDING,
            end=nk.CLUSTER_ROLE,
            kind=ek.REFERENCES_ROLE,
            description="RoleBinding references a ClusterRole",
        ),
        EdgeDef(
            start=nk.SCOPED_ROLE_BINDING,
            end=nk.SERVICE_ACCOUNT,
            kind=ek.AUTHORIZES,
            description="RoleBinding authorizes ServiceAccount",
        ),
        EdgeDef(
            start=nk.SCOPED_ROLE_BINDING,
            end=nk.USER,
            kind=ek.AUTHORIZES,
            description="RoleBinding authorizes User",
        ),
        EdgeDef(
            start=nk.SCOPED_ROLE_BINDING,
            end=nk.GROUP,
            kind=ek.AUTHORIZES,
            description="RoleBinding authorizes Group",
        ),
        EdgeDef(
            start=nk.SERVICE_ACCOUNT,
            end=nk.SCOPED_ROLE,
            kind=ek.INHERITS_ROLE,
            description="ServiceAccount inherits Role via RoleBinding",
        ),
        EdgeDef(
            start=nk.SERVICE_ACCOUNT,
            end=nk.CLUSTER_ROLE,
            kind=ek.INHERITS_ROLE,
            description="ServiceAccount inherits ClusterRole via RoleBinding",
        ),
    ],
)
class RoleBinding(BaseAsset):
    kind: str | None = "RoleBinding"
    subjects: list[Subject] = []
    metadata: Metadata
    role_ref: RoleRef
    subjects: list[Subject]

    @field_validator("kind", mode="before")
    def set_default_if_none(cls, v):
        return v if v is not None else "RoleBinding"

    @property
    def as_node(self) -> "K8SNode":
        properties = ExtendedProperties(
            name=self.metadata.name,
            displayname=self.metadata.name,
            resource_kind=self.kind,
            labels=labels_to_list(self.metadata.labels),
            namespace=self.metadata.namespace,
            role_ref=self.role_ref.name,
            subjects=[subject.name for subject in self.subjects],
            uid=self.metadata.uid,
            cluster=self._extras["cluster"],
            environmentid=cluster_node_id(self._extras["cluster"]),
        )

        return K8SNode(
            kinds=[nk.SCOPED_ROLE_BINDING, nk.ROLE_BINDING],
            properties=properties,
        )

    def _get_target_user(self, target_name: str) -> "EdgePath":
        return match_by_properties(
            nk.USER,
            name=target_name,
            cluster=self._extras["cluster"],
        )

    def _get_target_group(self, target_name: str) -> "EdgePath":
        return match_by_properties(
            nk.GROUP,
            name=target_name,
            cluster=self._extras["cluster"],
        )

    def _service_account_path(self, target: str, namespace):
        return match_by_properties(
            nk.SERVICE_ACCOUNT,
            name=target,
            namespace=namespace,
            cluster=self._extras["cluster"],
        )

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
    def _role_path(self):
        if self.role_ref.kind == "ClusterRole":
            return match_by_properties(
                nk.CLUSTER_ROLE,
                name=self.role_ref.name,
                cluster=self._extras["cluster"],
            )

        return match_by_properties(
            nk.SCOPED_ROLE,
            name=self.role_ref.name,
            namespace=self.metadata.namespace,
            cluster=self._extras["cluster"],
        )

    @property
    def _role_edge(self) -> Iterator[Edge]:
        start_path = EdgePath(value=self.as_node.id, match_by="id")
        yield Edge(kind=ek.REFERENCES_ROLE, start=start_path, end=self._role_path)

    @property
    def _subjects(self) -> Iterator[Edge]:
        rb_path = EdgePath(value=self.as_node.id, match_by="id")
        for target in self.subjects:
            if target.kind == "ServiceAccount":
                namespace = (
                    target.namespace if target.namespace else self.metadata.namespace
                )
                if not self._lookup.service_account_exists(target.name, namespace):
                    continue
                get_sa_path = self._service_account_path(target.name, namespace)
                yield Edge(kind=ek.AUTHORIZES, start=rb_path, end=get_sa_path)

                yield Edge(
                    kind=ek.INHERITS_ROLE,
                    start=get_sa_path,
                    end=self._role_path,
                    properties=EdgeProperties(composed=True),
                )

            elif target.kind == "User":
                end_path = self._get_target_user(target.name)
                yield Edge(kind=ek.AUTHORIZES, start=rb_path, end=end_path)

            elif target.kind == "Group":
                end_path = self._get_target_group(target.name)
                yield Edge(kind=ek.AUTHORIZES, start=rb_path, end=end_path)

            else:
                print(
                    f"Unsupported subject kind: {target.kind} in RoleBinding {self.metadata.name}"
                )

    @property
    def edges(self) -> Iterator[Edge]:
        yield from self._cluster_contains_edge
        yield from self._namespace_edge
        yield from self._role_edge
        yield from self._subjects
