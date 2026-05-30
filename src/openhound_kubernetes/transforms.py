import duckdb


def create_resources_with_definitions(
    con: duckdb.DuckDBPyConnection, schema: str = "kubernetes"
) -> None:
    """Join Kubernetes resources with the resource definitions. Combines collected resource metadata with definitions from the Kubernetes API.

    Args:
        con: The DuckDB connection to use for querying the preprocessed tables.

    Returns:
        Table: A table containing Kubernetes resources joined with their resource definitions.
    """

    resource_tables = (
        "pods",
        "config_maps",
        "cron_jobs",
        "jobs",
        "persistent_volume_claims",
        "persistent_volumes",
        "roles",
        "role_bindings",
        "nodes",
        "namespaces",
        "deployments",
        "replicasets",
        "statefulsets",
        "daemonsets",
        "secrets",
        "cluster_roles",
        "cluster_role_bindings",
        "service_accounts",
    )

    con.execute(
        f"""
        CREATE OR REPLACE TABLE {schema}.resources_with_definitions AS
        SELECT
            CAST(NULL AS VARCHAR) AS name,
            CAST(NULL AS VARCHAR) AS namespace,
            CAST(NULL AS VARCHAR) AS kind,
            CAST(NULL AS VARCHAR) AS singular_name,
            CAST(NULL AS VARCHAR) AS definition
        WHERE FALSE
        """
    )

    existing_tables = {
        row[0]
        for row in con.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = ?
            """,
            [schema],
        ).fetchall()
    }
    if "resource_definitions" not in existing_tables:
        return

    existing_resource_tables = [
        table_name for table_name in resource_tables if table_name in existing_tables
    ]
    if not existing_resource_tables:
        return

    union_sql = "\nUNION ALL\n".join(
        f"""
        SELECT
            resource.metadata->>'name' AS name,
            resource.metadata->>'namespace' AS namespace,
            resource.kind AS kind,
            resource_defs.singular_name AS singular_name,
            resource_defs.name AS definition
        FROM {schema}.{table_name} AS resource
        LEFT JOIN {schema}.resource_definitions AS resource_defs
            ON resource.kind = resource_defs.kind
        """
        for table_name in existing_resource_tables
    )

    con.execute(
        f"""
        CREATE OR REPLACE TABLE {schema}.resources_with_definitions AS
        {union_sql}
        """
    )


def transforms(con: duckdb.DuckDBPyConnection, schema: str = "kubernetes") -> None:
    """Apply all Kubernetes preprocessing transformations to DuckDB.

    Args:
        con: The DuckDB connection to use for querying the preprocessed tables.
    """

    create_resources_with_definitions(con, schema)
