from functools import lru_cache

from duckdb import DuckDBPyConnection
from openhound.core.lookup import LookupManager


_NAMESPACED_RESOURCE_TABLES = {
    "ConfigMap": "config_maps",
    "PersistentVolumeClaim": "persistent_volume_claims",
    "Secret": "secrets",
}


class K8SLookup(LookupManager):
    def __init__(self, client: DuckDBPyConnection, schema: str = "kubernetes"):
        super().__init__(client, schema)
        self.schema = schema
        self.client = client

    @lru_cache
    def allowed_system_resources(self, resource_type: str):
        return self._find_all_objects(
            f"""SELECT
                name,
                kind,
                namespace,
                singular_name,
                definition
            FROM {self.schema}.resources_with_definitions
            WHERE definition GLOB ?;""",
            [resource_type],
        )

    @lru_cache
    def allowed_resource_definitions(
        self, resource_type: str, api_groups: tuple[str, ...] = ()
    ) -> list[tuple]:
        base_resource = resource_type.split("/", 1)[0]
        results = self._find_all_objects(
            f"""SELECT
                name,
                kind,
                singular_name,
                COALESCE(NULLIF("group", ''), '__core__') AS api_group_name
            FROM {self.schema}.resource_definitions
            WHERE name GLOB ?;""",
            [base_resource],
        )

        if not api_groups:
            return results

        allowed_groups = set(api_groups)
        return [row for row in results if row[3] in allowed_groups]

    @lru_cache
    def allowed_namespaced_resources(
        self, resource_type: str, namespace: str
    ) -> list[tuple]:
        results = self._find_all_objects(
            f"""SELECT
                name,
                kind,
                namespace,
                singular_name,
                definition
            FROM {self.schema}.resources_with_definitions
            WHERE definition GLOB ? AND namespace = ?;""",
            [resource_type, namespace],
        )
        return results

    @lru_cache
    def service_account_exists(self, name: str, namespace: str) -> bool:
        results = self._find_all_objects(
            f"""SELECT 1
            FROM {self.schema}.service_accounts
            WHERE (metadata->>'name') = ? AND (metadata->>'namespace') = ?
            LIMIT 1;""",
            [name, namespace],
        )
        return bool(results)

    @lru_cache
    def namespaced_resource(self, kind: str, name: str, namespace: str) -> tuple | None:
        table_name = _NAMESPACED_RESOURCE_TABLES.get(kind)
        if table_name is None:
            return None

        return self._find_single_object(
            f"""SELECT 1
            FROM {self.schema}.{table_name}
            WHERE (metadata->>'name') = ? AND (metadata->>'namespace') = ?
            LIMIT 1;""",
            [name, namespace],
        )
