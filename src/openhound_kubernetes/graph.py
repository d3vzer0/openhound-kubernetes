from dataclasses import dataclass, field

from openhound.core.models.entries_dataclass import (
    ConditionalEdgePath,
    EdgeProperties,
    Node as BaseNode,
    NodeProperties as BaseProperties,
    PropertyMatch,
    Edge,
    EdgePath,
)

from openhound_kubernetes.kinds import nodes as nk


class Edge(Edge): ...


class EdgePath(EdgePath): ...


@dataclass
class K8SNodeProperties(BaseProperties):
    """Base properties for all Kubernetes nodes.

    Attributes:
        namespace: Kubernetes namespace for namespaced resources.
        cluster: Kubernetes cluster name for the collected environment.
        uid: Kubernetes resource UID when available.
        environmentid: OpenGraph ID of the Kubernetes cluster node.
        resource_kind: Kubernetes-native resource kind or collector node kind.
        labels: Kubernetes labels serialized as key=value strings.
    """

    namespace: str | None
    cluster: str
    uid: str | None
    environmentid: str
    resource_kind: str
    labels: list[str] | None


@dataclass
class K8SNode(BaseNode):
    properties: K8SNodeProperties
    kinds: list[str]
    id: str = field(init=False)

    @staticmethod
    def guid(
        name: str,
        node_type: str,
        cluster: str,
        namespace: str = "__global__",
    ) -> str:
        return BaseNode.guid(name, node_type, cluster, namespace)

    def __post_init__(self):
        scope = self.properties.namespace if self.properties.namespace else "__global__"
        self.id = self.guid(
            self.properties.name,
            self.kinds[0],
            cluster=self.properties.cluster,
            namespace=scope,
        )
        self.properties.name = self.properties.name.upper()


@dataclass
class K8SEdgeProperties(EdgeProperties):
    """Base properties for Kubernetes edges."""


_TYPED_RESOURCE_KINDS = {
    "ClusterRole": nk.CLUSTER_ROLE,
    "ClusterRoleBinding": nk.CLUSTER_ROLE_BINDING,
    "ConfigMap": nk.CONFIG_MAP,
    "CronJob": nk.CRON_JOB,
    "DaemonSet": nk.DAEMON_SET,
    "Deployment": nk.DEPLOYMENT,
    "Job": nk.JOB,
    "Namespace": nk.NAMESPACE,
    "Node": nk.NODE,
    "PersistentVolume": nk.PERSISTENT_VOLUME,
    "PersistentVolumeClaim": nk.PERSISTENT_VOLUME_CLAIM,
    "Pod": nk.POD,
    "ReplicaSet": nk.REPLICA_SET,
    "Role": nk.SCOPED_ROLE,
    "RoleBinding": nk.SCOPED_ROLE_BINDING,
    "Secret": nk.SECRET,
    "ServiceAccount": nk.SERVICE_ACCOUNT,
    "StatefulSet": nk.STATEFUL_SET,
}


def match_by_properties(
    node_kind: str, **properties: str | bool | int | None
) -> ConditionalEdgePath:
    property_matchers = []
    for key, value in properties.items():
        if value is None:
            continue
        if key == "name" and isinstance(value, str):
            value = value.upper()
        property_matchers.append(PropertyMatch(key=key, value=value))

    return ConditionalEdgePath(kind=node_kind, property_matchers=property_matchers)


def labels_to_list(labels: dict | None) -> list[str] | None:
    if not labels:
        return None

    return [f"{key}={value}" for key, value in sorted(labels.items())]


def resource_definition_path(
    *,
    name: str,
    api_group_name: str,
    cluster: str,
) -> ConditionalEdgePath:
    return match_by_properties(
        nk.RESOURCE_DEFINITION,
        name=name,
        api_group_name=api_group_name,
        cluster=cluster,
    )


def dynamic_path(kind, **kwargs) -> ConditionalEdgePath:
    node_kind = _TYPED_RESOURCE_KINDS.get(kind, nk.RESOURCE)
    if node_kind == nk.RESOURCE:
        kwargs["resource_kind"] = kind

    return match_by_properties(node_kind, **kwargs)


def resource_permission_path(
    *,
    name: str,
    kind: str,
    namespace: str | None,
    cluster: str,
) -> ConditionalEdgePath:
    node_kind = _TYPED_RESOURCE_KINDS.get(kind, nk.RESOURCE)
    properties: dict[str, str | None] = {
        "name": name,
        "cluster": cluster,
        "namespace": namespace,
    }
    if node_kind == nk.RESOURCE:
        properties["resource_kind"] = kind

    return match_by_properties(node_kind, **properties)


def cluster_node_id(cluster: str) -> str:
    return K8SNode.guid(cluster, nk.CLUSTER, cluster)
