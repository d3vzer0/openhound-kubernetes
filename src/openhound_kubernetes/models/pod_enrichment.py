from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Any, Literal

from openhound_kubernetes.graph import Edge, EdgePath, match_by_properties
from openhound_kubernetes.kinds import edges as ek
from openhound_kubernetes.kinds import external as xk


@dataclass(frozen=True)
class PodEnrichmentRule:
    name: str
    required_labels: dict[str, str]
    edge_kind: str
    target_kind: str
    target_properties: Callable[[Any], dict[str, str | None]]
    direction: Literal["pod_to_target", "target_to_pod"] = "pod_to_target"


def label_matches(actual: Any, expected: str) -> bool:
    if actual is None:
        return False

    return str(actual).casefold() == expected.casefold()


def rule_matches(labels: dict | None, rule: PodEnrichmentRule) -> bool:
    labels = labels or {}
    return all(
        label_matches(labels.get(key), expected)
        for key, expected in rule.required_labels.items()
    )


def github_runner_from_pod(pod: Any) -> dict[str, str | None]:
    labels = pod.metadata.labels or {}
    return {
        "name": pod.metadata.name,
        "environment_name": labels.get("actions.github.com/organization"),
    }


POD_ENRICHMENT_RULES = (
    PodEnrichmentRule(
        name="github_arc_ephemeral_runner",
        required_labels={"actions-ephemeral-runner": "True"},
        edge_kind=ek.RUNS_ACTIONS_FOR,
        target_kind=xk.GITHUB_RUNNER,
        target_properties=github_runner_from_pod,
        direction="target_to_pod",
    ),
)


def pod_enrichment_edges(pod: Any) -> Iterator[Edge]:
    start_path = EdgePath(value=pod.as_node.id, match_by="id")

    for rule in POD_ENRICHMENT_RULES:
        if not rule_matches(pod.metadata.labels, rule):
            continue

        target_properties = rule.target_properties(pod)
        if any(value is None for value in target_properties.values()):
            continue

        target_path = match_by_properties(rule.target_kind, **target_properties)
        if rule.direction == "target_to_pod":
            yield Edge(kind=rule.edge_kind, start=target_path, end=start_path)
        else:
            yield Edge(kind=rule.edge_kind, start=start_path, end=target_path)
