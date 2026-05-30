from collections.abc import Iterator
from dataclasses import dataclass
from typing import Optional

from dlt.common import json
from openhound.core.asset import BaseAsset
from openhound.core.asset import EdgeDef, NodeDef
from pydantic import BaseModel, Field, field_validator

from openhound_kubernetes.graph import (
    K8SNode,
    K8SNodeProperties,
    Edge,
    EdgePath,
    match_by_properties,
    cluster_node_id,
)
from openhound_kubernetes.kinds import edges as ek, nodes as nk
from openhound_kubernetes.main import app


class ResourceLookup(BaseModel):
    kind: str
    name: str
    namespace: str | None


@dataclass
class ExtendedProperties(K8SNodeProperties):
    kind: str
    api_group_name: Optional[str] = ""
    api_group_uid: Optional[str] = ""


@app.asset(
    description="Kubernetes resource definitions. Returns a ResourceDefinition node with edges specifying API group membership.",
    node=NodeDef(
        properties=ExtendedProperties,
        kind=nk.RESOURCE_DEFINITION,
        description="Kubernetes resource definitions",
        icon="file-code",
        color="#aea1ff",
    ),
    edges=[
        EdgeDef(
            start=nk.CLUSTER,
            end=nk.RESOURCE_DEFINITION,
            kind=ek.CONTAINS,
            description="Cluster contains resource",
        ),
        EdgeDef(
            start=nk.RESOURCE_DEFINITION,
            end=nk.RESOURCE_GROUP,
            kind=ek.IN_RESOURCE_GROUP,
            description="Resource belongs to an API group",
        ),
    ],
)
class ResourceDefinition(BaseAsset):
    name: str
    categories: Optional[list[str]] = []
    kind: str
    group: Optional[str] = None
    api_version: str | None = None
    singular_name: str | None = Field(alias="singularName", default=None)
    name: str
    namespaced: bool = False
    verbs: list[str]

    # api_version: str
    # uid: Optional[str] = None
    # api_group_name: Optional[str] = ""
    # api_group_uid: Optional[str] = ""

    @property
    def uid(self) -> str:
        return K8SNode.guid(
            self.name,
            f"{nk.RESOURCE_DEFINITION}:{self.group}",
            self._extras["cluster"],
        )

    @field_validator("group", mode="after")
    @classmethod
    def validate_group(cls, v: str) -> str:
        group_name = "__core__" if not v or v == "" else v
        return group_name

    @field_validator("verbs", mode="before")
    @classmethod
    def parse_verbs(cls, value):
        if isinstance(value, str):
            value = json.loads(value)
        return value or []

    @property
    def as_node(self) -> "K8SNode":
        properties = ExtendedProperties(
            name=self.name,
            displayname=self.name,
            resource_kind=self.kind,
            labels=None,
            kind=self.kind,
            namespace=None,
            api_group_name=self.group,
            uid=self.uid,
            cluster=self._extras["cluster"],
            environmentid=cluster_node_id(self._extras["cluster"]),
        )
        node = K8SNode(kinds=[nk.RESOURCE_DEFINITION], properties=properties)
        node.id = self.uid
        return node

    @property
    def _resource_group_edge(self) -> Iterator[Edge]:
        if self.group:
            start_path = EdgePath(value=self.as_node.id, match_by="id")
            end_path = match_by_properties(
                nk.RESOURCE_GROUP,
                name=self.group,
                cluster=self._extras["cluster"],
            )
            yield Edge(kind=ek.IN_RESOURCE_GROUP, start=start_path, end=end_path)

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
        yield from self._resource_group_edge
