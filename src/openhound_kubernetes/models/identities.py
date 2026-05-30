from collections.abc import Iterator

from openhound.core.asset import BaseAsset
from openhound.core.asset import EdgeDef, NodeDef
from pydantic import computed_field

from openhound_kubernetes.graph import (
    K8SNode,
    K8SNodeProperties,
    Edge,
    EdgePath,
    cluster_node_id,
    match_by_properties,
)
from openhound_kubernetes.kinds import edges as ek, nodes as nk
from openhound_kubernetes.main import app


@app.asset(
    description="Kubernetes user asset. Returns a user node with edges specifying group memberships.",
    node=NodeDef(
        properties=K8SNodeProperties,
        kind=nk.USER,
        description="Kubernetes user",
        icon="user",
        color="#d33115",
    ),
    edges=[
        EdgeDef(
            start=nk.CLUSTER,
            end=nk.USER,
            kind=ek.CONTAINS,
            description="Cluster contains resource",
        ),
        EdgeDef(
            start=nk.USER,
            end=nk.GROUP,
            kind=ek.MEMBER_OF,
            description="User is a member of system groups via bindings",
        ),
    ],
)
class User(BaseAsset):
    name: str
    api_group: str
    kind: str = "User"

    @computed_field
    @property
    def uid(self) -> str:
        return K8SNode.guid(self.name, nk.USER, "")

    @property
    def as_node(self) -> "K8SNode":
        properties = K8SNodeProperties(
            name=self.name,
            displayname=self.name,
            resource_kind=self.kind,
            labels=None,
            uid=self.uid,
            namespace=None,
            cluster=self._extras["cluster"],
            environmentid=cluster_node_id(self._extras["cluster"]),
        )
        return K8SNode(kinds=[nk.USER], properties=properties)

    @property
    def _authenticated_group_edge(self) -> Iterator[Edge]:
        # target_id = self._lookup.groups("system:authenticated")
        start_path = EdgePath(value=self.as_node.id, match_by="id")
        end_path = match_by_properties(
            nk.GROUP,
            name="system:authenticated",
            cluster=self._extras["cluster"],
        )
        yield Edge(kind=ek.MEMBER_OF, start=start_path, end=end_path)

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
        yield from self._authenticated_group_edge


@app.asset(
    description="Kubernetes group asset. Returns a group node with no direct edges. Membership is determined by edges from users and service accounts.",
    node=NodeDef(
        properties=K8SNodeProperties,
        kind=nk.GROUP,
        description="Kubernetes group",
        icon="users",
        color="#fcdc00",
    ),
)
class Group(BaseAsset):
    name: str
    api_group: str
    kind: str = "Group"

    @computed_field
    @property
    def uid(self) -> str:
        return K8SNode.guid(self.name, nk.GROUP, "")

    @property
    def as_node(self) -> "K8SNode":
        properties = K8SNodeProperties(
            name=self.name,
            displayname=self.name,
            resource_kind=self.kind,
            labels=None,
            uid=self.uid,
            namespace=None,
            cluster=self._extras["cluster"],
            environmentid=cluster_node_id(self._extras["cluster"]),
        )
        return K8SNode(kinds=[nk.GROUP], properties=properties)

    @property
    def edges(self) -> Iterator[Edge]:
        yield from ()
