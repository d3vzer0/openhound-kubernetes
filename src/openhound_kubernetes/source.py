import os
from dataclasses import dataclass

import dlt
from kubernetes import client, config
from kubernetes.dynamic import DynamicClient
from urllib3.util.retry import Retry

from .main import app
from .models import (
    Cluster,
    ClusterRole,
    ClusterRoleBinding,
    ConfigMap,
    CronJob,
    DaemonSet,
    Deployment,
    Generic,
    Group,
    Job,
    KubeNode,
    Namespace,
    PersistentVolume,
    PersistentVolumeClaim,
    Pod,
    ReplicaSet,
    ResourceDefinition,
    ResourceGroup,
    Role,
    RoleBinding,
    Secret,
    ServiceAccount,
    StatefulSet,
    User,
    Volume,
)

IDENTITY_MAPPING = {"User": User, "Group": Group}
RESOURCE_TYPES = {
    "Pod": Pod,
    "ConfigMap": ConfigMap,
    "CronJob": CronJob,
    "Job": Job,
    "PersistentVolume": PersistentVolume,
    "PersistentVolumeClaim": PersistentVolumeClaim,
    "ServiceAccount": ServiceAccount,
    "Role": Role,
    "Node": KubeNode,
    "Namespace": Namespace,
    "RoleBinding": RoleBinding,
    "Secret": Secret,
    "ClusterRole": ClusterRole,
    "ClusterRoleBinding": ClusterRoleBinding,
    "ReplicaSet": ReplicaSet,
    "DaemonSet": DaemonSet,
    "StatefulSet": StatefulSet,
    "Deployment": Deployment,
    # "Service": ServiceNode
}


@dataclass
class SourceContext:
    cluster: str | None
    dyn_client: DynamicClient
    api_client: client.ApiClient


@app.resource(
    columns=Cluster,
    name="clusters",
)
def clusters(ctx: SourceContext):
    """DLT resource, emits a single cluster record.

    Yields:
        (Cluster): Cluster name record.
    """
    yield {"name": ctx.cluster}


@app.resource(columns=KubeNode, name="nodes", parallelized=True)
def nodes(ctx: SourceContext):
    """DLT resource, fetches Kubernetes nodes via CoreV1Api list_node.

    Yields:
        (KubeNode): Node records.
    """
    v1 = client.CoreV1Api(ctx.api_client)
    nodes = v1.list_node()
    for node in nodes.items:
        yield node.to_dict()


@app.resource(columns=Namespace, name="namespaces", parallelized=True)
def namespaces(ctx: SourceContext):
    """DLT resource, fetches Kubernetes namespaces via CoreV1Api list_namespace.

    Yields:
        (Namespace): Namespace records.
    """
    v1 = client.CoreV1Api(ctx.api_client)
    namespaces = v1.list_namespace()
    for ns in namespaces.items:
        yield ns.to_dict()


@app.resource(columns=DaemonSet, name="daemonsets", parallelized=True)
def daemonsets(ctx: SourceContext):
    """DLT resource, fetches DaemonSets via AppsV1Api list_daemon_set_for_all_namespaces.

    Yields:
        (DaemonSet): DaemonSet records.
    """
    v1 = client.AppsV1Api(ctx.api_client)
    daemonsets = v1.list_daemon_set_for_all_namespaces()
    for daemonset in daemonsets.items:
        yield daemonset.to_dict()


@app.resource(columns=StatefulSet, name="statefulsets", parallelized=True)
def statefulsets(ctx: SourceContext):
    """DLT resource, fetches StatefulSets via AppsV1Api list_stateful_set_for_all_namespaces.

    Yields:
        (StatefulSet): StatefulSet records.
    """
    v1 = client.AppsV1Api(ctx.api_client)
    statefulsets = v1.list_stateful_set_for_all_namespaces()
    for replica in statefulsets.items:
        yield replica.to_dict()


@app.resource(columns=ReplicaSet, name="replicasets", parallelized=True)
def replicasets(ctx: SourceContext):
    """DLT resource, fetches ReplicaSets via AppsV1Api list_replica_set_for_all_namespaces.

    Yields:
        (ReplicaSet): ReplicaSet records.
    """
    v1 = client.AppsV1Api(ctx.api_client)
    replicasets = v1.list_replica_set_for_all_namespaces()
    for replica in replicasets.items:
        yield replica.to_dict()


@app.resource(columns=Deployment, name="deployments", parallelized=True)
def deployments(ctx: SourceContext):
    """DLT resource, fetches Deployments via AppsV1Api list_deployment_for_all_namespaces.

    Yields:
        (Deployment): Deployment records.
    """
    v1 = client.AppsV1Api(ctx.api_client)
    deployments = v1.list_deployment_for_all_namespaces()
    for deployment in deployments.items:
        yield deployment.to_dict()


@app.resource(columns=Pod, name="pods", parallelized=True)
def pods(ctx: SourceContext):
    """DLT resource, fetches Pods via CoreV1Api list_pod_for_all_namespaces.

    Yields:
        (Pod): Pod records.
    """
    v1 = client.CoreV1Api(ctx.api_client)
    pods = v1.list_pod_for_all_namespaces()
    for pod in pods.items:
        yield pod.to_dict()


@app.resource(columns=ConfigMap, name="config_maps", parallelized=True)
def config_maps(ctx: SourceContext):
    """DLT resource, fetches sanitized ConfigMap metadata and keys without values."""
    v1 = client.CoreV1Api(ctx.api_client)
    config_maps_data = v1.list_config_map_for_all_namespaces()
    for config_map in config_maps_data.items:
        metadata = config_map.metadata.to_dict()
        yield {
            "metadata": {
                "name": metadata.get("name"),
                "uid": metadata.get("uid"),
                "namespace": metadata.get("namespace"),
                "creation_timestamp": metadata.get("creation_timestamp"),
                "labels": metadata.get("labels"),
            },
            "kind": config_map.kind,
            "data_keys": list(config_map.data.keys()) if config_map.data else None,
            "binary_data_keys": list(config_map.binary_data.keys())
            if config_map.binary_data
            else None,
            "immutable": config_map.immutable,
        }


@app.resource(
    columns=PersistentVolumeClaim, name="persistent_volume_claims", parallelized=True
)
def persistent_volume_claims(ctx: SourceContext):
    """DLT resource, fetches PersistentVolumeClaims."""
    v1 = client.CoreV1Api(ctx.api_client)
    claims = v1.list_persistent_volume_claim_for_all_namespaces()
    for claim in claims.items:
        yield claim.to_dict()


@app.resource(columns=PersistentVolume, name="persistent_volumes", parallelized=True)
def persistent_volumes(ctx: SourceContext):
    """DLT resource, fetches PersistentVolumes."""
    v1 = client.CoreV1Api(ctx.api_client)
    volumes_data = v1.list_persistent_volume()
    for volume in volumes_data.items:
        yield volume.to_dict()


@app.transformer(columns=Volume, name="cust_volumes")
def volumes(pod: dict):
    """DLT transformer, extracts hostPath volumes from pod specs.

    Args:
        pod (dict): Pod record from the pods resource.
    Yields:
        (Volume): HostPath volume records with node and path.
    """
    volumes = pod["spec"]["volumes"]
    if volumes:
        node_name = pod["spec"].get("node_name")
        if not node_name:
            return
        for volume in volumes:
            host_path = volume.get("host_path")
            if not host_path:
                continue
            path = host_path.get("path")
            yield {"node_name": node_name, "path": path}


@app.resource(columns=Role, name="roles", parallelized=True)
def roles(ctx: SourceContext):
    """DLT resource, fetches Roles via RbacAuthorizationV1Api list_role_for_all_namespaces.

    Yields:
        (Role): Role records.
    """
    v1 = client.RbacAuthorizationV1Api(ctx.api_client)
    roles = v1.list_role_for_all_namespaces()
    for role in roles.items:
        yield role.to_dict()


@app.resource(columns=RoleBinding, name="role_bindings", parallelized=True)
def role_bindings(ctx: SourceContext):
    """DLT resource, fetches RoleBindings via RbacAuthorizationV1Api list_role_binding_for_all_namespaces.

    Yields:
        (RoleBinding): RoleBinding records.
    """
    v1 = client.RbacAuthorizationV1Api(ctx.api_client)
    rolebs = v1.list_role_binding_for_all_namespaces()
    for roleb in rolebs.items:
        yield roleb.to_dict()


@app.transformer(name="cust_users", columns=User)
def users_role(role_binding):
    """DLT transformer, extracts User subjects from RoleBindings.

    Args:
        role_binding (dict): RoleBinding record.
    Yields:
        (User): User subject records.
    """
    for subject in role_binding["subjects"]:
        if subject["kind"] == "User":
            yield subject


@app.transformer(name="cust_groups", columns=Group)
def groups_role(role_binding):
    """DLT transformer, extracts Group subjects from RoleBindings.

    Args:
        role_binding (dict): RoleBinding record.
    Yields:
        (Group): Group subject records.
    """
    for subject in role_binding["subjects"]:
        if subject["kind"] == "Group":
            yield subject


@app.resource(columns=ClusterRole, name="cluster_roles", parallelized=True)
def cluster_roles(ctx: SourceContext):
    """DLT resource, fetches ClusterRoles via RbacAuthorizationV1Api list_cluster_role.

    Yields:
        (ClusterRole): ClusterRole records.
    """
    v1 = client.RbacAuthorizationV1Api(ctx.api_client)
    roles = v1.list_cluster_role()
    for role in roles.items:
        yield role.to_dict()


@app.resource(columns=Job, name="jobs", parallelized=True)
def jobs(ctx: SourceContext):
    """DLT resource, fetches Jobs via BatchV1Api list_job_for_all_namespaces."""
    v1 = client.BatchV1Api(ctx.api_client)
    jobs_data = v1.list_job_for_all_namespaces()
    for job in jobs_data.items:
        yield job.to_dict()


@app.resource(columns=CronJob, name="cron_jobs", parallelized=True)
def cron_jobs(ctx: SourceContext):
    """DLT resource, fetches CronJobs via BatchV1Api list_cron_job_for_all_namespaces."""
    v1 = client.BatchV1Api(ctx.api_client)
    cron_jobs_data = v1.list_cron_job_for_all_namespaces()
    for cron_job in cron_jobs_data.items:
        yield cron_job.to_dict()


@app.resource(
    columns=ClusterRoleBinding,
    name="cluster_role_bindings",
    parallelized=True,
)
def cluster_role_bindings(ctx: SourceContext):
    """DLT resource, fetches ClusterRoleBindings via RbacAuthorizationV1Api list_cluster_role_binding.

    Yields:
        (ClusterRoleBinding): ClusterRoleBinding records.
    """
    v1 = client.RbacAuthorizationV1Api(ctx.api_client)
    rolebs = v1.list_cluster_role_binding()
    for roleb in rolebs.items:
        yield roleb.to_dict()


@app.transformer(name="cust_users_clusters", columns=User)
def users_cluster_role(role_binding):
    """DLT transformer, extracts User subjects from ClusterRoleBindings.

    Args:
        role_binding (dict): ClusterRoleBinding record.
    Yields:
        dict: (User) subject records.
    """
    for subject in role_binding["subjects"]:
        if subject["kind"] == "User":
            yield subject


@app.transformer(name="cust_groups_clusters", columns=Group)
def groups_cluster_role(role_binding):
    """DLT transformer, extracts Group subjects from ClusterRoleBindings.

    Args:
        role_binding (dict): ClusterRoleBinding record.
    Yields:
        (Group): Group subject records.
    """
    for subject in role_binding["subjects"]:
        if subject["kind"] == "Group":
            yield subject


@app.resource(columns=ServiceAccount, name="service_accounts", parallelized=True)
def service_accounts(ctx: SourceContext):
    """DLT resource, fetches ServiceAccounts via CoreV1Api list_service_account_for_all_namespaces.

    Yields:
        (ServiceAccount): ServiceAccount records.
    """
    v1 = client.CoreV1Api(ctx.api_client)
    service_accounts = v1.list_service_account_for_all_namespaces()
    for service_account in service_accounts.items:
        yield service_account.to_dict()


@app.resource(name="secrets", columns=Secret, parallelized=True)
def secrets(ctx: SourceContext):
    """DLT resource, fetches sanitized Secret metadata without secret contents.

    Yields:
        (Secret): Secret metadata records.
    """
    v1 = client.CoreV1Api(ctx.api_client)
    secrets_data = v1.list_secret_for_all_namespaces()
    for secret in secrets_data.items:
        metadata = secret.metadata.to_dict()
        yield {
            "metadata": {
                "name": metadata.get("name"),
                "uid": metadata.get("uid"),
                "namespace": metadata.get("namespace"),
                "creation_timestamp": metadata.get("creation_timestamp"),
                "labels": metadata.get("labels"),
            },
            "kind": secret.kind,
            "type": secret.type,
            "immutable": secret.immutable,
        }


@app.resource(
    columns=ResourceDefinition, name="resource_definitions", parallelized=True
)
def resource_definitions(ctx: SourceContext):
    """DLT resource, discovers API resource definitions via the dynamic client.

    Yields:
        (ResourceDefinition): Resource definition records.
    """
    discovered_resources = ctx.dyn_client.resources.search()
    for resource in discovered_resources:
        if not resource.kind.endswith("List"):
            yield resource.to_dict()


@app.transformer(name="cust_api_groups", columns=ResourceGroup)
def api_groups(item):
    """DLT transformer, extracts API groups from resource definitions.

    Args:
        item (dict): Resource definition record.
    Yields:
        (ResourceGroup): API group records.
    """
    if item["group"]:
        yield {"name": item["group"], "api_version": item["api_version"]}


@app.transformer(name="unmapped", columns=Generic, parallelized=True)
def unmapped_resources(resource: dict, ctx: SourceContext):
    """DLT transformer, fetches resources for kinds not mapped to explicit models.

    Args:
        resource (dict): Resource definition record.
    Yields:
        (Generic): Raw resource records for unmapped kinds.
    """
    resource_filter = (
        resource["kind"] not in RESOURCE_TYPES and "list" in resource["verbs"]
    )
    if resource_filter:
        resource_client = ctx.dyn_client.resources.get(
            api_version=resource["api_version"], kind=resource["kind"]
        )
        items = resource_client.get()
        for item in items.items:
            yield item.to_dict()


@app.source(name="kubernetes", max_table_nesting=0)
def source(kube_config: str = "~/.kube/config", cluster_name: str = dlt.config.value):
    """DLT source, defines Kubernetes collection resources and transformers.

    Args:
        kube_config (str | None): Path to kubeconfig file.
        cluster (str | None): Cluster name for context and labeling.

    Returns:
        (tuple[pods, namespaces, nodes, service_accounts, deployments, replicasets, statefulsets, daemonsets, roles, role_bindings, cluster_roles, cluster_role_bindings, resource_definitions, api_groups, unmapped_resources, volumes, users_cluster_role, groups_cluster_role, users_role, groups_role, clusters]): A tuple of DLT resources/transformers registered for Kubernetes.
    """
    if os.getenv("KUBERNETES_SERVICE_HOST"):
        config.load_incluster_config()
    else:
        config.load_kube_config(kube_config)

    configuration = client.Configuration.get_default_copy()
    configuration.retries = Retry(
        total=10,
        backoff_factor=2,
        respect_retry_after_header=True,
        status_forcelist=[429],
    )
    api_client = client.ApiClient(configuration=configuration)
    dyn_client = DynamicClient(api_client)

    ctx = SourceContext(
        cluster=cluster_name, api_client=api_client, dyn_client=dyn_client
    )

    pods_resource = pods(ctx)
    crb_resource = cluster_role_bindings(ctx)
    rd_resource = resource_definitions(ctx)
    rb_resource = role_bindings(ctx)

    return (
        pods_resource,
        pods_resource | volumes,
        namespaces(ctx),
        nodes(ctx),
        config_maps(ctx),
        service_accounts(ctx),
        secrets(ctx),
        persistent_volume_claims(ctx),
        persistent_volumes(ctx),
        deployments(ctx),
        replicasets(ctx),
        statefulsets(ctx),
        daemonsets(ctx),
        jobs(ctx),
        cron_jobs(ctx),
        roles(ctx),
        rb_resource,
        rb_resource | users_role,
        rb_resource | groups_role,
        cluster_roles(ctx),
        crb_resource,
        crb_resource | users_cluster_role,
        crb_resource | groups_cluster_role,
        rd_resource,
        rd_resource | api_groups,
        rd_resource | unmapped_resources(ctx),
        clusters(ctx),
    )


# @dlt.source(name="kubernetes_opengraph_eks")
# def kubernetes_eks_opengraph(
#     *,
#     cluster: str,
#     lookup: K8SLookup,
# ):
#     """DLT source, emits OpenGraph graphs for EKS virtual cluster roles.

#     Args:
#         cluster (str): Cluster name for context and labeling.
#         lookup (K8SLookup): Lookup helper for node/edge enrichment.
#     """

#     def build_graph(model_cls, resource: dict) -> Graph:
#         resource_model = model_cls(**resource)
#         resource_model._cluster = cluster
#         resource_model._lookup = lookup
#         node = resource_model.as_node

#         entries = GraphEntries(
#             nodes=[node],
#             edges=[edge for edge in node.edges if edge],
#         )
#         return Graph(graph=entries)

#     @app.resource(name="eks_virtual_cluster_roles", columns=Graph)
#     def eks_cluster_roles():
#         """DLT resource, emits virtual EKS cluster role graphs.

#         Yields:
#             Graph: OpenGraph graph for the virtual cluster role.
#         """

#         virtual_admin = EKSVirtualClusterAdminRole()
#         print(virtual_admin.model_dump())

#         yield build_graph(ClusterRole, virtual_admin.model_dump())

#     return eks_cluster_roles
