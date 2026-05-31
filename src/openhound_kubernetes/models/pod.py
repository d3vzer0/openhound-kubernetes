from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Any, TypeVar, Annotated

from openhound.core.asset import BaseAsset
from openhound.core.asset import EdgeDef, NodeDef
from pydantic import (
    BaseModel,
    Field,
    BeforeValidator,
    field_validator,
)
from pydantic_core import PydanticUseDefault

from openhound_kubernetes.graph import (
    K8SNode,
    K8SNodeProperties,
    Edge,
    EdgePath,
    cluster_node_id,
    dynamic_path,
    labels_to_list,
    match_by_properties,
)
from openhound_kubernetes.kinds import edges as ek, nodes as nk
from openhound_kubernetes.kinds import external as xk
from openhound_kubernetes.main import app
from openhound_kubernetes.models.pod_enrichment import pod_enrichment_edges
from openhound_kubernetes.models.volume import Volume as HostVolume


def default_if_none(value: Any) -> Any:
    if value is None:
        raise PydanticUseDefault()
    return value


T = TypeVar("T")
DefaultIfNone = Annotated[T, BeforeValidator(default_if_none)]


class SecurityContext(BaseModel):
    allow_privilege_escalation: DefaultIfNone[bool | None] = False
    privileged: DefaultIfNone[bool | None] = False


class VolumeMount(BaseModel):
    mount_path: str
    name: str


class LocalObjectReference(BaseModel):
    name: str | None = None


class EnvFromSource(BaseModel):
    config_map_ref: LocalObjectReference | None = None
    secret_ref: LocalObjectReference | None = None


class ConfigMapKeySelector(BaseModel):
    name: str | None = None


class SecretKeySelector(BaseModel):
    name: str | None = None


class EnvVarSource(BaseModel):
    config_map_key_ref: ConfigMapKeySelector | None = None
    secret_key_ref: SecretKeySelector | None = None


class EnvVar(BaseModel):
    value_from: EnvVarSource | None = None


class HostPath(BaseModel):
    path: str


class SecretVolumeSource(BaseModel):
    secret_name: str | None = None


class ConfigMapVolumeSource(BaseModel):
    name: str | None = None


class PersistentVolumeClaimVolumeSource(BaseModel):
    claim_name: str | None = None


class Volume(BaseModel):
    name: str
    host_path: HostPath | None = None
    secret: SecretVolumeSource | None = None
    config_map: ConfigMapVolumeSource | None = None
    persistent_volume_claim: PersistentVolumeClaimVolumeSource | None = None


class Container(BaseModel):
    image: str
    security_context: DefaultIfNone[SecurityContext | None] = Field(
        default_factory=SecurityContext
    )
    volume_mounts: list[VolumeMount] | None = []
    env: list[EnvVar] | None = []
    env_from: list[EnvFromSource] | None = []


class Spec(BaseModel):
    node_name: str | None = None
    service_account_name: Optional[str] = "default"
    containers: list[Container]
    volumes: DefaultIfNone[list[Volume] | None] = Field(default=[])
    image_pull_secrets: list[LocalObjectReference] | None = []


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
    resource_version: str
    labels: dict | None = {}
    owner_references: list[OwnerReferences] | None = None

    @field_validator("labels", mode="before")
    def set_default_if_none(cls, v):
        return v if v is not None else {}


@dataclass
class ExtendedProperties(K8SNodeProperties):
    # namespace: str
    node_name: str | None = None
    service_account_name: str | None = None


@app.asset(
    description="Kubernetes pod asset. Returns a pod node with edges specifying node, namespace, and volume relationships.",
    node=NodeDef(
        properties=ExtendedProperties,
        kind=nk.POD,
        description="Kubernetes pod node",
        icon="cube",
        color="#68bc00",
    ),
    edges=[
        EdgeDef(
            start=nk.CLUSTER,
            end=nk.POD,
            kind=ek.CONTAINS,
            description="Cluster contains resource",
        ),
        EdgeDef(
            start=nk.POD,
            end=nk.NODE,
            kind=ek.RUNS_ON,
            description="Pod is running on a node",
        ),
        EdgeDef(
            start=nk.POD,
            end=nk.NAMESPACE,
            kind=ek.BELONGS_TO,
            description="Pod belongs to a namespace",
        ),
        EdgeDef(
            start=nk.POD,
            end=nk.SERVICE_ACCOUNT,
            kind=ek.RUNS_AS,
            description="Pod runs as the service account",
        ),
        EdgeDef(
            start=nk.POD,
            end=nk.VOLUME,
            kind=ek.ATTACHES,
            description="Pod attaches HostPath volumes",
        ),
        EdgeDef(
            start=nk.POD,
            end=nk.SECRET,
            kind=ek.USES,
            description="Pod uses a Secret",
        ),
        EdgeDef(
            start=nk.POD,
            end=nk.CONFIG_MAP,
            kind=ek.USES,
            description="Pod uses a ConfigMap",
        ),
        EdgeDef(
            start=nk.POD,
            end=nk.PERSISTENT_VOLUME_CLAIM,
            kind=ek.MOUNTS,
            description="Pod mounts a PersistentVolumeClaim",
        ),
        EdgeDef(
            start=xk.GITHUB_RUNNER,
            end=nk.POD,
            kind=ek.RUNS_ACTIONS_FOR,
            description="GitHub runner runs as a Kubernetes pod",
        ),
        EdgeDef(
            start=nk.POD,
            end=nk.CLUSTER_ROLE,
            kind=ek.OWNED_BY,
            description="Pod is owned by a Kubernetes resource",
        ),
        EdgeDef(
            start=nk.POD,
            end=nk.CLUSTER_ROLE_BINDING,
            kind=ek.OWNED_BY,
            description="Pod is owned by a Kubernetes resource",
        ),
        EdgeDef(
            start=nk.POD,
            end=nk.CONFIG_MAP,
            kind=ek.OWNED_BY,
            description="Pod is owned by a Kubernetes resource",
        ),
        EdgeDef(
            start=nk.POD,
            end=nk.DAEMON_SET,
            kind=ek.OWNED_BY,
            description="Pod is owned by a Kubernetes resource",
        ),
        EdgeDef(
            start=nk.POD,
            end=nk.DEPLOYMENT,
            kind=ek.OWNED_BY,
            description="Pod is owned by a Kubernetes resource",
        ),
        EdgeDef(
            start=nk.POD,
            end=nk.CRON_JOB,
            kind=ek.OWNED_BY,
            description="Pod is owned by a Kubernetes resource",
        ),
        EdgeDef(
            start=nk.POD,
            end=nk.JOB,
            kind=ek.OWNED_BY,
            description="Pod is owned by a Kubernetes resource",
        ),
        EdgeDef(
            start=nk.POD,
            end=nk.NAMESPACE,
            kind=ek.OWNED_BY,
            description="Pod is owned by a Kubernetes resource",
        ),
        EdgeDef(
            start=nk.POD,
            end=nk.NODE,
            kind=ek.OWNED_BY,
            description="Pod is owned by a Kubernetes resource",
        ),
        EdgeDef(
            start=nk.POD,
            end=nk.POD,
            kind=ek.OWNED_BY,
            description="Pod is owned by a Kubernetes resource",
        ),
        EdgeDef(
            start=nk.POD,
            end=nk.PERSISTENT_VOLUME,
            kind=ek.OWNED_BY,
            description="Pod is owned by a Kubernetes resource",
        ),
        EdgeDef(
            start=nk.POD,
            end=nk.PERSISTENT_VOLUME_CLAIM,
            kind=ek.OWNED_BY,
            description="Pod is owned by a Kubernetes resource",
        ),
        EdgeDef(
            start=nk.POD,
            end=nk.REPLICA_SET,
            kind=ek.OWNED_BY,
            description="Pod is owned by a Kubernetes resource",
        ),
        EdgeDef(
            start=nk.POD,
            end=nk.RESOURCE,
            kind=ek.OWNED_BY,
            description="Pod is owned by a Kubernetes resource",
        ),
        EdgeDef(
            start=nk.POD,
            end=nk.SCOPED_ROLE,
            kind=ek.OWNED_BY,
            description="Pod is owned by a Kubernetes resource",
        ),
        EdgeDef(
            start=nk.POD,
            end=nk.SCOPED_ROLE_BINDING,
            kind=ek.OWNED_BY,
            description="Pod is owned by a Kubernetes resource",
        ),
        EdgeDef(
            start=nk.POD,
            end=nk.SERVICE_ACCOUNT,
            kind=ek.OWNED_BY,
            description="Pod is owned by a Kubernetes resource",
        ),
        EdgeDef(
            start=nk.POD,
            end=nk.SECRET,
            kind=ek.OWNED_BY,
            description="Pod is owned by a Kubernetes resource",
        ),
        EdgeDef(
            start=nk.POD,
            end=nk.STATEFUL_SET,
            kind=ek.OWNED_BY,
            description="Pod is owned by a Kubernetes resource",
        ),
    ],
)
class Pod(BaseAsset):
    metadata: Metadata
    spec: Spec
    kind: str | None = "Pod"

    @field_validator("kind", mode="before")
    def set_default_if_none(cls, v):
        return v if v is not None else "Pod"

    def _namespaced_resource_exists(self, kind: str, name: str) -> bool:
        lookup = getattr(self, "_lookup", None)
        if lookup is None:
            return True

        find_resource = getattr(lookup, "namespaced_resource", None)
        if find_resource is None:
            return True

        return find_resource(kind, name, self.metadata.namespace) is not None

    @property
    def as_node(self) -> "K8SNode":
        properties = ExtendedProperties(
            name=self.metadata.name,
            displayname=self.metadata.name,
            resource_kind=self.kind,
            labels=labels_to_list(self.metadata.labels),
            namespace=self.metadata.namespace,
            node_name=self.spec.node_name,
            uid=self.metadata.uid,
            service_account_name=self.spec.service_account_name,
            cluster=self._extras["cluster"],
            environmentid=cluster_node_id(self._extras["cluster"]),
            # **self.spec.containers[0].security_context.model_dump(),
        )
        node = K8SNode(kinds=[nk.POD], properties=properties)
        return node

    @property
    def _cluster_contains_edge(self) -> "Iterator[Edge]":
        node = self.as_node
        yield Edge(
            kind=ek.CONTAINS,
            start=EdgePath(value=node.properties.environmentid, match_by="id"),
            end=EdgePath(value=node.id, match_by="id"),
        )

    @property
    def _namespace_edge(self) -> "Iterator[Edge]":
        start_path = EdgePath(value=self.as_node.id, match_by="id")
        end_path = match_by_properties(
            nk.NAMESPACE,
            name=self.metadata.namespace,
            cluster=self._extras["cluster"],
        )
        yield Edge(kind=ek.BELONGS_TO, start=start_path, end=end_path)

    @property
    def _node_edge(self) -> "Iterator[Edge]":
        if self.spec.node_name:
            start_path = EdgePath(value=self.as_node.id, match_by="id")
            end_path = match_by_properties(
                nk.NODE,
                name=self.spec.node_name,
                cluster=self._extras["cluster"],
            )
            yield Edge(kind=ek.RUNS_ON, start=start_path, end=end_path)

    @property
    def _service_account_edge(self) -> "Iterator[Edge]":
        if self.spec.service_account_name:
            start_path = EdgePath(value=self.as_node.id, match_by="id")
            end_path = match_by_properties(
                nk.SERVICE_ACCOUNT,
                name=self.spec.service_account_name,
                namespace=self.metadata.namespace,
                cluster=self._extras["cluster"],
            )
            yield Edge(kind=ek.RUNS_AS, start=start_path, end=end_path)

    @property
    def _owned_by(self) -> "Iterator[Edge]":
        start_path = EdgePath(value=self.as_node.id, match_by="id")
        if self.metadata.owner_references:
            for owner in self.metadata.owner_references:
                end_path = dynamic_path(
                    kind=owner.kind,
                    uid=owner.uid,
                )
                yield Edge(kind=ek.OWNED_BY, start=start_path, end=end_path)

    @property
    def _volume_edges(self) -> "Iterator[Edge]":
        start_path = EdgePath(value=self.as_node.id, match_by="id")
        for volume in self.spec.volumes:
            if volume.host_path:
                node_name = self.spec.node_name
                if not node_name:
                    continue
                volume_object = HostVolume(
                    node_name=node_name, path=volume.host_path.path
                )
                volume_id = K8SNode.guid(
                    volume_object.name,
                    nk.VOLUME,
                    cluster=self._extras["cluster"],
                    namespace="__global__",
                )
                yield Edge(
                    kind=ek.ATTACHES,
                    start=start_path,
                    end=EdgePath(value=volume_id, match_by="id"),
                    properties={"name": volume.name, "type": "HostPath"},
                )

    @property
    def _secret_edges(self) -> "Iterator[Edge]":
        start_path = EdgePath(value=self.as_node.id, match_by="id")
        secret_names = set()
        for image_pull_secret in self.spec.image_pull_secrets or []:
            if image_pull_secret.name:
                secret_names.add(image_pull_secret.name)
        for volume in self.spec.volumes:
            if volume.secret and volume.secret.secret_name:
                secret_names.add(volume.secret.secret_name)
        for container in self.spec.containers:
            for env_from in container.env_from or []:
                if env_from.secret_ref and env_from.secret_ref.name:
                    secret_names.add(env_from.secret_ref.name)
            for env in container.env or []:
                if (
                    env.value_from
                    and env.value_from.secret_key_ref
                    and env.value_from.secret_key_ref.name
                ):
                    secret_names.add(env.value_from.secret_key_ref.name)
        for secret_name in sorted(secret_names):
            if not self._namespaced_resource_exists("Secret", secret_name):
                continue

            yield Edge(
                kind=ek.USES,
                start=start_path,
                end=match_by_properties(
                    nk.SECRET,
                    name=secret_name,
                    namespace=self.metadata.namespace,
                    cluster=self._extras["cluster"],
                ),
            )

    @property
    def _config_map_edges(self) -> "Iterator[Edge]":
        start_path = EdgePath(value=self.as_node.id, match_by="id")
        config_map_names = set()
        for volume in self.spec.volumes:
            if volume.config_map and volume.config_map.name:
                config_map_names.add(volume.config_map.name)
        for container in self.spec.containers:
            for env_from in container.env_from or []:
                if env_from.config_map_ref and env_from.config_map_ref.name:
                    config_map_names.add(env_from.config_map_ref.name)
            for env in container.env or []:
                if (
                    env.value_from
                    and env.value_from.config_map_key_ref
                    and env.value_from.config_map_key_ref.name
                ):
                    config_map_names.add(env.value_from.config_map_key_ref.name)
        for config_map_name in sorted(config_map_names):
            if not self._namespaced_resource_exists("ConfigMap", config_map_name):
                continue

            yield Edge(
                kind=ek.USES,
                start=start_path,
                end=match_by_properties(
                    nk.CONFIG_MAP,
                    name=config_map_name,
                    namespace=self.metadata.namespace,
                    cluster=self._extras["cluster"],
                ),
            )

    @property
    def _persistent_volume_claim_edges(self) -> "Iterator[Edge]":
        start_path = EdgePath(value=self.as_node.id, match_by="id")
        claim_names = set()
        for volume in self.spec.volumes:
            if (
                volume.persistent_volume_claim
                and volume.persistent_volume_claim.claim_name
            ):
                claim_names.add(volume.persistent_volume_claim.claim_name)
        for claim_name in sorted(claim_names):
            if not self._namespaced_resource_exists(
                "PersistentVolumeClaim", claim_name
            ):
                continue

            yield Edge(
                kind=ek.MOUNTS,
                start=start_path,
                end=match_by_properties(
                    nk.PERSISTENT_VOLUME_CLAIM,
                    name=claim_name,
                    namespace=self.metadata.namespace,
                    cluster=self._extras["cluster"],
                ),
            )

    @property
    def edges(self) -> "Iterator[Edge]":
        yield from self._cluster_contains_edge
        yield from self._node_edge
        yield from self._namespace_edge
        yield from self._service_account_edge
        yield from self._owned_by
        yield from self._volume_edges
        yield from self._secret_edges
        yield from self._config_map_edges
        yield from self._persistent_volume_claim_edges
        yield from pod_enrichment_edges(self)
