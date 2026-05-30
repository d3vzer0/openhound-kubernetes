from typing import Tuple

import dlt
from dlt.extract.source import DltSource
from openhound.core.app import OpenHound
from openhound.core.collect import CollectContext
from openhound.core.convert import ConvertContext
from openhound.core.preproc import PreProcContext

from openhound_kubernetes.lookup import K8SLookup
from openhound_kubernetes.transforms import transforms

app = OpenHound(
    "kubernetes", source_kind="K8s", help="OpenGraph collector for Kubernetes"
)


@app.collect()
def collect(ctx: CollectContext) -> DltSource:
    """Register a Typer CLI command that collects Kubernetes resources and stores them (filtered) on disk.

    Args:
        ctx (CollectContext): Returns DLT pipeline context.
    """
    from openhound_kubernetes.source import source as kube_source

    return kube_source()


@app.preproc(transformer=transforms)
def preproc(ctx: PreProcContext) -> dict[str, str]:
    """Register a Typer CLI command that preprocesses Kubernetes resources and builds lookup data.

    Args:
        ctx (PreProcContext): Returns DLT pipeline context.
    """
    resources = {
        "resource_definitions": "resource_definitions",
        "pods": "pods",
        "config_maps": "config_maps",
        "cron_jobs": "cron_jobs",
        "jobs": "jobs",
        "persistent_volume_claims": "persistent_volume_claims",
        "persistent_volumes": "persistent_volumes",
        "roles": "roles",
        "role_bindings": "role_bindings",
        "secrets": "secrets",
        "service_accounts": "service_accounts",
        "nodes": "nodes",
        "namespaces": "namespaces",
        "deployments": "deployments",
        "replicasets": "replicasets",
        "statefulsets": "statefulsets",
        "daemonsets": "daemonsets",
        "cluster_roles": "cluster_roles",
        "cluster_role_bindings": "cluster_role_bindings",
    }
    return resources


@app.convert(lookup=K8SLookup)
def convert(ctx: ConvertContext) -> Tuple[DltSource, dict]:
    """Register a Typer CLI command that converts Kubernetes resources into OpenGraph nodes and edges.

    Args:
        ctx (ConvertContext): Returns DLT pipeline context.
    """
    from openhound_kubernetes.source import source as kube_source

    cluster_name = dlt.config.get("sources.source.kubernetes.cluster_name", str)
    extras = {"cluster": cluster_name}

    return kube_source(), extras
