"""
Sandbox Manager — multi-dialect SQL execution environment.

Routing:
  sqlite     → in-memory SQLite (no Docker)
  postgresql → postgres:16-alpine container (ephemeral)
  mysql      → mysql:8.4 container (ephemeral)
  mssql      → mcr.microsoft.com/mssql/server:2022-latest (ephemeral, needs 2 GB RAM)
  bigquery   → ghcr.io/goccy/bigquery-emulator container (ephemeral)

Each non-SQLite sandbox:
  1. Pulls image if missing (cached after first run).
  2. Runs container with memory/CPU limits and a random-port binding.
  3. Waits for the DB to accept connections (health-check loop).
  4. Loads the INSERT statements for the mock data.
  5. Executes the user query and captures rows + columns.
  6. Destroys the container in a try/finally block.
"""
from __future__ import annotations

import json
import logging
import re
import secrets
import sqlite3
import time
from contextlib import contextmanager
from typing import Any, Generator

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MEMORY_LIMITS: dict[str, str] = {
    "postgresql": "512m",
    "mysql": "512m",
    "mssql": "2g",   # SQL Server minimum requirement
    "bigquery": "512m",
}

_NANO_CPU_LIMIT = 1_000_000_000   # 1 vCPU

_CONNECT_TIMEOUT = 60   # seconds to wait for container to be ready
_QUERY_TIMEOUT   = 30   # seconds for single query execution
_MAX_ROWS        = 100  # cap result set


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

class SandboxResult:
    def __init__(
        self,
        ok: bool,
        columns: list[str],
        rows: list[dict[str, Any]],
        error: str,
        dialect: str,
        warnings: list[str],
        duration_ms: int,
        mock_preview: dict[str, list[dict[str, Any]]],
    ):
        self.ok = ok
        self.columns = columns
        self.rows = rows
        self.error = error
        self.dialect = dialect
        self.warnings = warnings
        self.duration_ms = duration_ms
        self.mock_preview = mock_preview

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "columns": self.columns,
            "rows": self.rows,
            "error": self.error,
            "dialect": self.dialect,
            "warnings": self.warnings,
            "duration_ms": self.duration_ms,
            "mockPreview": self.mock_preview,
        }


def _fail(dialect: str, error: str, warnings: list[str] | None = None) -> SandboxResult:
    return SandboxResult(
        ok=False, columns=[], rows=[], error=error,
        dialect=dialect, warnings=warnings or [], duration_ms=0, mock_preview={},
    )


# ---------------------------------------------------------------------------
# SQL extraction helper
# ---------------------------------------------------------------------------

def _extract_sql(text: str) -> str:
    t = (text or "").strip()
    m = re.search(r"```(?:sql)?\s*\n(.*?)```", t, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return t


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_sandbox(
    sql: str,
    dialect: str,
    schema_info: dict,
    mock_data: dict[str, list[dict[str, Any]]] | None = None,
    rows_per_table: int = 8,
) -> SandboxResult:
    """
    Execute *sql* inside an isolated sandbox for the given *dialect*.

    Args:
        sql:           The SELECT query to run (may be wrapped in markdown fences).
        dialect:       One of postgresql | mysql | mssql | bigquery | sqlite.
        schema_info:   Output of schema_parser.parse_schema().
        mock_data:     {table_name: [row_dict, ...]} — pre-generated synthetic rows.
                       If None or empty, the SQLite path uses its built-in mock generator.
        rows_per_table: Fallback row count if mock_data is empty (SQLite path).

    Returns:
        SandboxResult
    """
    sql = _extract_sql(sql)
    dialect = (dialect or "sqlite").lower()
    mock_data = mock_data or {}

    if not sql:
        return _fail(dialect, "No SQL provided to sandbox.")

    if dialect == "sqlite":
        return _run_sqlite(sql, schema_info, mock_data, rows_per_table)

    # Attempt Docker-based sandbox; fall back to SQLite if Docker is unavailable
    docker_available = True
    docker_error = ""
    try:
        _docker_client()
    except RuntimeError as exc:
        docker_available = False
        docker_error = str(exc)

    if docker_available:
        try:
            return _run_docker(sql, dialect, schema_info, mock_data)
        except RuntimeError as exc:
            docker_available = False
            docker_error = str(exc)

    # ── Fallback: translate and run on SQLite ─────────────────────────
    warnings = [
        f"Docker is not available locally. Falling back to SQLite sandbox "
        f"(query auto-translated from {dialect.upper()} via sqlglot).",
        f"Docker error: {docker_error}",
    ]
    result = _run_sqlite(sql, schema_info, mock_data, rows_per_table)
    result.dialect = dialect  # Report the original dialect
    result.warnings = warnings + result.warnings
    return result


# ---------------------------------------------------------------------------
# SQLite path (uses pre-generated mock_data or falls back to built-in generator)
# ---------------------------------------------------------------------------

def _sqlite_type(raw: str) -> str:
    t = (raw or "").upper()
    if any(x in t for x in ("INT", "SERIAL", "BIGSERIAL")):
        return "INTEGER"
    if any(x in t for x in ("DECIMAL", "NUMERIC", "REAL", "DOUBLE", "FLOAT", "MONEY")):
        return "REAL"
    if "BOOL" in t:
        return "INTEGER"
    return "TEXT"


def _strip_id(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]", "", name or "")


def _qid(name: str) -> str:
    return f'"{_strip_id(name)}"'


def _mock_value(table: str, column: str, raw_type: str, row_index: int) -> Any:
    """Deterministic mock value used as fallback when mock_data is empty."""
    name = column.lower()
    typ = (raw_type or "").upper()

    if name == "id" or name.endswith("_id"):
        return row_index
    if "email" in name:
        return f"{table}{row_index}@example.test"
    if "name" in name or "title" in name:
        return f"{table.title()} {row_index}"
    if "status" in name:
        return ["active", "pending", "archived"][row_index % 3]
    if "category" in name or "type" in name:
        return ["standard", "premium", "trial"][row_index % 3]
    if "created" in name or "updated" in name or "date" in name or "time" in name:
        return (time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(1700000000 + row_index * 86400)))
    if "price" in name or "amount" in name or "total" in name or "salary" in name:
        return round(19.5 + row_index * 7.25, 2)
    if "count" in name or "qty" in name or "quantity" in name:
        return row_index * 2
    if "BOOL" in typ:
        return row_index % 2
    if any(x in typ for x in ("INT", "SERIAL")):
        return row_index * 10
    if any(x in typ for x in ("DECIMAL", "NUMERIC", "REAL", "DOUBLE", "FLOAT")):
        return round(row_index * 3.14, 2)
    return f"{column}_{row_index}"


def _build_sqlite_db(
    conn: sqlite3.Connection,
    schema_info: dict,
    mock_data: dict[str, list[dict[str, Any]]],
    rows_per_table: int,
) -> dict[str, list[dict[str, Any]]]:
    """Create tables and insert data. Returns mock_preview dict."""
    tables = schema_info.get("tables") or {}
    mock_preview: dict[str, list[dict[str, Any]]] = {}

    for tname, tinfo in tables.items():
        cols = tinfo.get("columns") or {}
        if not cols:
            continue
        col_defs = ", ".join(
            f"{_qid(c)} {_sqlite_type(info.get('type', ''))}"
            for c, info in cols.items()
        )
        conn.execute(f"CREATE TABLE {_qid(tname)} ({col_defs})")

    for tname, tinfo in tables.items():
        cols = tinfo.get("columns") or {}
        if not cols:
            continue

        if mock_data and tname in mock_data and mock_data[tname]:
            rows = mock_data[tname]
            col_names = list(rows[0].keys())
            ph = ", ".join(["?"] * len(col_names))
            insert_sql = (
                f"INSERT INTO {_qid(tname)} "
                f"({', '.join(_qid(c) for c in col_names)}) "
                f"VALUES ({ph})"
            )
            for row in rows:
                conn.execute(insert_sql, [row.get(c) for c in col_names])
        else:
            col_names = list(cols.keys())
            ph = ", ".join(["?"] * len(col_names))
            insert_sql = (
                f"INSERT INTO {_qid(tname)} "
                f"({', '.join(_qid(c) for c in col_names)}) "
                f"VALUES ({ph})"
            )
            rows = []
            for row_idx in range(1, rows_per_table + 1):
                row = {
                    col: _mock_value(tname, col, cols[col].get("type", ""), row_idx)
                    for col in col_names
                }
                rows.append(row)
                conn.execute(insert_sql, [row[col] for col in col_names])
        mock_preview[tname] = rows[:3]

    conn.commit()
    return mock_preview


def _run_sqlite(
    sql: str,
    schema_info: dict,
    mock_data: dict[str, list[dict[str, Any]]],
    rows_per_table: int,
) -> SandboxResult:
    warnings: list[str] = []

    # Translate to SQLite if needed
    try:
        import sqlglot
        translated_list = sqlglot.transpile(sql, read="postgres", write="sqlite")
        sqlite_sql = ";\n".join(translated_list) if translated_list else sql
        if sqlite_sql != sql:
            warnings.append("Query was auto-translated from the source dialect to SQLite.")
    except Exception:
        sqlite_sql = sql

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    mock_preview: dict[str, list[dict[str, Any]]] = {}

    try:
        mock_preview = _build_sqlite_db(conn, schema_info, mock_data, rows_per_table)

        t0 = time.monotonic()
        cursor = conn.execute(sqlite_sql)
        rows_out = [dict(r) for r in cursor.fetchmany(_MAX_ROWS)]
        duration_ms = int((time.monotonic() - t0) * 1000)
        columns = [d[0] for d in (cursor.description or [])]

        return SandboxResult(
            ok=True, columns=columns, rows=rows_out, error="",
            dialect="sqlite", warnings=warnings,
            duration_ms=duration_ms, mock_preview=mock_preview,
        )
    except Exception as exc:
        return _fail("sqlite", str(exc), warnings)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Docker path
# ---------------------------------------------------------------------------

def _docker_client():
    """Lazy import so the tool still loads when docker-py isn't installed."""
    try:
        import docker
        return docker.from_env()
    except Exception as exc:
        raise RuntimeError(
            "docker-py is not available or Docker socket is not accessible. "
            "Make sure the runner container has /var/run/docker.sock mounted and "
            "'docker>=7.0.0' is in requirements.txt."
        ) from exc


@contextmanager
def _ephemeral_container(
    image: str,
    env: dict[str, str],
    ports: dict[str, int | None],
    dialect: str,
    command: str | None = None,
) -> Generator[Any, None, None]:
    """Spin up a Docker container, yield it, then always remove it."""
    client = _docker_client()
    container = None
    mem_limit = _MEMORY_LIMITS.get(dialect, "512m")
    try:
        container = client.containers.run(
            image,
            command=command,
            environment=env,
            ports=ports,
            detach=True,
            remove=False,   # we remove manually in finally
            mem_limit=mem_limit,
            nano_cpus=_NANO_CPU_LIMIT,
            network_mode="bridge",
        )
        yield container
    finally:
        if container:
            try:
                container.stop(timeout=5)
            except Exception:
                pass
            try:
                container.remove(force=True)
            except Exception:
                pass


def _wait_for_port(host: str, port: int, timeout: int = _CONNECT_TIMEOUT) -> None:
    """Block until a TCP connection succeeds or timeout is reached."""
    import socket
    deadline = time.monotonic() + timeout
    last_exc: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=2):
                return
        except Exception as exc:
            last_exc = exc
            time.sleep(1)
    raise TimeoutError(
        f"Service at {host}:{port} did not become ready within {timeout}s. "
        f"Last error: {last_exc}"
    )


def _get_host_port(container, internal_port: str) -> int:
    container.reload()
    bindings = container.ports.get(internal_port) or []
    if not bindings:
        raise RuntimeError(f"No host port bound for {internal_port}")
    return int(bindings[0]["HostPort"])


def _run_docker(
    sql: str,
    dialect: str,
    schema_info: dict,
    mock_data: dict[str, list[dict[str, Any]]],
) -> SandboxResult:
    dispatch = {
        "postgresql": _run_postgresql,
        "mysql": _run_mysql,
        "mssql": _run_mssql,
        "bigquery": _run_bigquery,
    }
    fn = dispatch.get(dialect)
    if not fn:
        return _fail(dialect, f"Unsupported dialect: {dialect}")

    try:
        return fn(sql, schema_info, mock_data)
    except Exception as exc:
        logger.exception("Sandbox error for dialect=%s", dialect)
        return _fail(dialect, f"Sandbox error: {exc}")


# ---------------------------------------------------------------------------
# PostgreSQL
# ---------------------------------------------------------------------------

def _run_postgresql(
    sql: str,
    schema_info: dict,
    mock_data: dict[str, list[dict[str, Any]]],
) -> SandboxResult:
    db_pass = secrets.token_urlsafe(16)
    db_name = "sandbox"
    db_user = "sandbox"

    env = {
        "POSTGRES_PASSWORD": db_pass,
        "POSTGRES_USER": db_user,
        "POSTGRES_DB": db_name,
    }
    ports = {"5432/tcp": None}   # random host port

    with _ephemeral_container("postgres:16-alpine", env, ports, "postgresql") as ctr:
        port = _get_host_port(ctr, "5432/tcp")
        _wait_for_port("127.0.0.1", port)

        import psycopg2
        # Extra wait: postgres takes a moment after TCP accepts
        conn = _pg_connect_with_retry(db_user, db_pass, db_name, port)
        try:
            warnings: list[str] = []
            mock_preview: dict[str, list[dict[str, Any]]] = {}

            with conn:
                with conn.cursor() as cur:
                    # Create tables from DDL
                    ddl = (schema_info.get("raw_ddl") or "").strip()
                    if ddl:
                        cur.execute(ddl)
                    else:
                        _create_tables_from_schema(cur, schema_info, "postgresql")

                    # Insert mock data
                    for tname, rows in (mock_data or {}).items():
                        if not rows:
                            continue
                        _insert_rows_pg(cur, tname, rows)
                        mock_preview[tname] = rows[:3]

                    # Execute query
                    t0 = time.monotonic()
                    cur.execute(sql)
                    duration_ms = int((time.monotonic() - t0) * 1000)
                    rows_out = [
                        dict(zip([d.name for d in cur.description], row))
                        for row in (cur.fetchmany(_MAX_ROWS) if cur.description else [])
                    ]
                    columns = [d.name for d in (cur.description or [])]

            return SandboxResult(
                ok=True, columns=columns, rows=rows_out, error="",
                dialect="postgresql", warnings=warnings,
                duration_ms=duration_ms, mock_preview=mock_preview,
            )
        except Exception as exc:
            return _fail("postgresql", str(exc))
        finally:
            conn.close()


def _pg_connect_with_retry(user, password, dbname, port, retries=20):
    import psycopg2
    last: Exception | None = None
    for _ in range(retries):
        try:
            return psycopg2.connect(
                host="127.0.0.1", port=port,
                user=user, password=password, dbname=dbname,
                connect_timeout=3,
            )
        except Exception as exc:
            last = exc
            time.sleep(2)
    raise RuntimeError(f"PostgreSQL did not accept connections: {last}")


def _insert_rows_pg(cur, tname: str, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    cols = list(rows[0].keys())
    col_list = ", ".join(f'"{c}"' for c in cols)
    placeholders = ", ".join(["%s"] * len(cols))
    sql = f'INSERT INTO "{tname}" ({col_list}) VALUES ({placeholders})'
    cur.executemany(sql, [[r.get(c) for c in cols] for r in rows])


# ---------------------------------------------------------------------------
# MySQL
# ---------------------------------------------------------------------------

def _run_mysql(
    sql: str,
    schema_info: dict,
    mock_data: dict[str, list[dict[str, Any]]],
) -> SandboxResult:
    db_pass = secrets.token_urlsafe(16)
    db_name = "sandbox"
    db_user = "sandbox"

    env = {
        "MYSQL_ROOT_PASSWORD": secrets.token_urlsafe(16),
        "MYSQL_DATABASE": db_name,
        "MYSQL_USER": db_user,
        "MYSQL_PASSWORD": db_pass,
    }
    ports = {"3306/tcp": None}

    with _ephemeral_container("mysql:8.4", env, ports, "mysql") as ctr:
        port = _get_host_port(ctr, "3306/tcp")
        _wait_for_port("127.0.0.1", port)

        import pymysql
        conn = _mysql_connect_with_retry(db_user, db_pass, db_name, port)
        try:
            warnings: list[str] = []
            mock_preview: dict[str, list[dict[str, Any]]] = {}

            with conn:
                with conn.cursor() as cur:
                    ddl = (schema_info.get("raw_ddl") or "").strip()
                    if ddl:
                        for stmt in _split_ddl(ddl):
                            cur.execute(stmt)
                    else:
                        _create_tables_from_schema(cur, schema_info, "mysql")

                    for tname, rows in (mock_data or {}).items():
                        if not rows:
                            continue
                        _insert_rows_mysql(cur, tname, rows)
                        mock_preview[tname] = rows[:3]

                    t0 = time.monotonic()
                    cur.execute(sql)
                    duration_ms = int((time.monotonic() - t0) * 1000)
                    rows_raw = cur.fetchmany(_MAX_ROWS) if cur.description else []
                    columns = [d[0] for d in (cur.description or [])]
                    rows_out = [dict(zip(columns, row)) for row in rows_raw]

            return SandboxResult(
                ok=True, columns=columns, rows=rows_out, error="",
                dialect="mysql", warnings=warnings,
                duration_ms=duration_ms, mock_preview=mock_preview,
            )
        except Exception as exc:
            return _fail("mysql", str(exc))
        finally:
            conn.close()


def _mysql_connect_with_retry(user, password, db, port, retries=30):
    import pymysql
    last: Exception | None = None
    for _ in range(retries):
        try:
            return pymysql.connect(
                host="127.0.0.1", port=port,
                user=user, password=password, database=db,
                connect_timeout=3, autocommit=True,
            )
        except Exception as exc:
            last = exc
            time.sleep(2)
    raise RuntimeError(f"MySQL did not accept connections: {last}")


def _insert_rows_mysql(cur, tname: str, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    cols = list(rows[0].keys())
    col_list = ", ".join(f"`{c}`" for c in cols)
    placeholders = ", ".join(["%s"] * len(cols))
    sql = f"INSERT INTO `{tname}` ({col_list}) VALUES ({placeholders})"
    cur.executemany(sql, [[r.get(c) for c in cols] for r in rows])


# ---------------------------------------------------------------------------
# SQL Server (MSSQL)
# ---------------------------------------------------------------------------

def _run_mssql(
    sql: str,
    schema_info: dict,
    mock_data: dict[str, list[dict[str, Any]]],
) -> SandboxResult:
    sa_pass = "Sandbox_" + secrets.token_urlsafe(10) + "1!"
    db_name = "sandbox"

    env = {
        "ACCEPT_EULA": "Y",
        "SA_PASSWORD": sa_pass,
        "MSSQL_PID": "Express",
    }
    ports = {"1433/tcp": None}
    warnings = [
        "SQL Server requires ≥2 GB RAM on the Docker host. "
        "Startup may take 30–60 seconds."
    ]

    with _ephemeral_container(
        "mcr.microsoft.com/mssql/server:2022-latest",
        env, ports, "mssql",
    ) as ctr:
        port = _get_host_port(ctr, "1433/tcp")
        _wait_for_port("127.0.0.1", port)

        import pyodbc
        conn = _mssql_connect_with_retry(sa_pass, port)
        try:
            mock_preview: dict[str, list[dict[str, Any]]] = {}

            with conn:
                cur = conn.cursor()
                cur.execute(f"IF DB_ID('{db_name}') IS NULL CREATE DATABASE [{db_name}]")
                cur.execute(f"USE [{db_name}]")

                ddl = (schema_info.get("raw_ddl") or "").strip()
                if ddl:
                    # Translate to T-SQL
                    try:
                        import sqlglot
                        translated = sqlglot.transpile(ddl, read="postgres", write="tsql")
                        for stmt in translated:
                            cur.execute(stmt)
                    except Exception:
                        for stmt in _split_ddl(ddl):
                            cur.execute(stmt)
                else:
                    _create_tables_from_schema(cur, schema_info, "mssql")

                for tname, rows in (mock_data or {}).items():
                    if not rows:
                        continue
                    _insert_rows_mssql(cur, tname, rows)
                    mock_preview[tname] = rows[:3]

                conn.commit()

                t0 = time.monotonic()
                cur.execute(sql)
                duration_ms = int((time.monotonic() - t0) * 1000)
                rows_raw = cur.fetchmany(_MAX_ROWS) if cur.description else []
                columns = [d[0] for d in (cur.description or [])]
                rows_out = [dict(zip(columns, row)) for row in rows_raw]

            return SandboxResult(
                ok=True, columns=columns, rows=rows_out, error="",
                dialect="mssql", warnings=warnings,
                duration_ms=duration_ms, mock_preview=mock_preview,
            )
        except Exception as exc:
            return _fail("mssql", str(exc), warnings)
        finally:
            conn.close()


def _mssql_connect_with_retry(sa_pass, port, retries=40):
    import pyodbc
    conn_str = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER=127.0.0.1,{port};"
        f"UID=sa;PWD={sa_pass};"
        f"TrustServerCertificate=yes;"
        f"Connection Timeout=3;"
    )
    last: Exception | None = None
    for _ in range(retries):
        try:
            return pyodbc.connect(conn_str, autocommit=False)
        except Exception as exc:
            last = exc
            time.sleep(3)
    raise RuntimeError(f"SQL Server did not accept connections: {last}")


def _insert_rows_mssql(cur, tname: str, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    cols = list(rows[0].keys())
    col_list = ", ".join(f"[{c}]" for c in cols)
    placeholders = ", ".join(["?"] * len(cols))
    sql = f"INSERT INTO [{tname}] ({col_list}) VALUES ({placeholders})"
    cur.executemany(sql, [[r.get(c) for c in cols] for r in rows])


# ---------------------------------------------------------------------------
# BigQuery emulator
# ---------------------------------------------------------------------------

def _run_bigquery(
    sql: str,
    schema_info: dict,
    mock_data: dict[str, list[dict[str, Any]]],
) -> SandboxResult:
    project = "sandbox-project"
    dataset = "sandbox_dataset"

    env = {"BIGQUERY_EMULATOR_PROJECT": project}
    ports = {"9050/tcp": None, "9060/tcp": None}

    with _ephemeral_container(
        "ghcr.io/goccy/bigquery-emulator:latest",
        env, ports, "bigquery",
        command=f"--project={project} --data-from-query-emulation",
    ) as ctr:
        grpc_port = _get_host_port(ctr, "9050/tcp")
        _wait_for_port("127.0.0.1", grpc_port, timeout=30)

        try:
            from google.cloud import bigquery
            from google.api_core.client_options import ClientOptions
            from google.auth.credentials import AnonymousCredentials

            client = bigquery.Client(
                project=project,
                credentials=AnonymousCredentials(),
                client_options=ClientOptions(
                    api_endpoint=f"http://127.0.0.1:{grpc_port}"
                ),
            )

            warnings: list[str] = []
            mock_preview: dict[str, list[dict[str, Any]]] = {}

            # Create dataset
            client.create_dataset(
                bigquery.Dataset(f"{project}.{dataset}"), exists_ok=True
            )

            # Create tables and load data
            tables = schema_info.get("tables") or {}
            for tname, tinfo in tables.items():
                cols_info = tinfo.get("columns") or {}
                bq_schema = [
                    bigquery.SchemaField(cname, _bq_type(cinfo.get("type", "")))
                    for cname, cinfo in cols_info.items()
                ]
                table_ref = f"{project}.{dataset}.{tname}"
                tbl = bigquery.Table(table_ref, schema=bq_schema)
                client.create_table(tbl, exists_ok=True)

                rows = mock_data.get(tname) or []
                if rows:
                    client.insert_rows_json(table_ref, rows)
                    mock_preview[tname] = rows[:3]

            # Execute query — rewrite table refs to include project.dataset
            bq_sql = _rewrite_bq_refs(sql, dataset, project)

            t0 = time.monotonic()
            query_job = client.query(bq_sql)
            result = query_job.result(timeout=_QUERY_TIMEOUT)
            duration_ms = int((time.monotonic() - t0) * 1000)

            columns = [f.name for f in result.schema]
            rows_out = [dict(row) for row in list(result)[:_MAX_ROWS]]

            return SandboxResult(
                ok=True, columns=columns, rows=rows_out, error="",
                dialect="bigquery", warnings=warnings,
                duration_ms=duration_ms, mock_preview=mock_preview,
            )
        except Exception as exc:
            return _fail("bigquery", str(exc))


def _bq_type(raw: str) -> str:
    t = (raw or "").upper()
    if any(x in t for x in ("INT", "SERIAL", "BIGINT")):
        return "INT64"
    if any(x in t for x in ("FLOAT", "DOUBLE", "REAL", "NUMERIC", "DECIMAL")):
        return "FLOAT64"
    if "BOOL" in t:
        return "BOOL"
    if any(x in t for x in ("DATE",)) and "TIME" not in t:
        return "DATE"
    if "TIMESTAMP" in t or "DATETIME" in t:
        return "TIMESTAMP"
    return "STRING"


def _rewrite_bq_refs(sql: str, dataset: str, project: str) -> str:
    """Prefix bare table names with project.dataset for BigQuery."""
    def replacer(m: re.Match) -> str:
        kw = m.group(1)
        tname = m.group(2)
        if "." not in tname:
            return f"{kw} `{project}.{dataset}.{tname}`"
        return m.group(0)

    return re.sub(
        r"\b(FROM|JOIN)\s+([`\"]?[a-zA-Z_][a-zA-Z0-9_]*[`\"]?)",
        replacer,
        sql,
        flags=re.IGNORECASE,
    )


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _split_ddl(ddl: str) -> list[str]:
    return [s.strip() for s in ddl.split(";") if s.strip()]


def _create_tables_from_schema(cur, schema_info: dict, dialect: str) -> None:
    """Fallback: generate CREATE TABLE statements from parsed schema dict."""
    tables = schema_info.get("tables") or {}
    for tname, tinfo in tables.items():
        cols = tinfo.get("columns") or {}
        if not cols:
            continue
        col_defs = []
        for cname, cinfo in cols.items():
            ctype = _portable_type(cinfo.get("type", ""), dialect)
            null_clause = " NOT NULL" if cinfo.get("not_null") else ""
            col_defs.append(f'  "{cname}" {ctype}{null_clause}')
        create_sql = f'CREATE TABLE "{tname}" (\n' + ",\n".join(col_defs) + "\n)"
        cur.execute(create_sql)


def _portable_type(raw: str, dialect: str) -> str:
    """Map a type string to a safe, dialect-compatible equivalent."""
    t = (raw or "").upper()
    if any(x in t for x in ("SERIAL", "BIGSERIAL")):
        mapping = {
            "postgresql": "SERIAL", "mysql": "INT AUTO_INCREMENT",
            "mssql": "INT IDENTITY(1,1)", "bigquery": "INT64",
        }
        return mapping.get(dialect, "INTEGER")
    if any(x in t for x in ("BIGINT",)):
        return {"bigquery": "INT64"}.get(dialect, "BIGINT")
    if any(x in t for x in ("INT",)):
        return {"bigquery": "INT64"}.get(dialect, "INT")
    if any(x in t for x in ("DECIMAL", "NUMERIC")):
        return {"bigquery": "FLOAT64"}.get(dialect, raw or "DECIMAL(18,4)")
    if any(x in t for x in ("FLOAT", "DOUBLE", "REAL")):
        return {"bigquery": "FLOAT64"}.get(dialect, "FLOAT")
    if "BOOL" in t:
        return {"mssql": "BIT", "mysql": "TINYINT(1)", "bigquery": "BOOL"}.get(dialect, "BOOLEAN")
    if "TIMESTAMP" in t:
        return {"mssql": "DATETIME2", "bigquery": "TIMESTAMP", "mysql": "DATETIME"}.get(dialect, "TIMESTAMP")
    if "TEXT" in t:
        return {"mssql": "NVARCHAR(MAX)", "bigquery": "STRING"}.get(dialect, "TEXT")
    if "VARCHAR" in t:
        return {"bigquery": "STRING", "mssql": "NVARCHAR(255)"}.get(dialect, raw or "VARCHAR(255)")
    return {"bigquery": "STRING"}.get(dialect, raw or "TEXT")


# ---------------------------------------------------------------------------
# Markdown formatter
# ---------------------------------------------------------------------------

def sandbox_markdown(result: SandboxResult) -> str:
    status = "✅ passed" if result.ok else "❌ failed"
    lines = [
        "\n\n## Sandbox Test",
        f"**Dialect:** {result.dialect.upper()} &nbsp;|&nbsp; "
        f"**Status:** {status} &nbsp;|&nbsp; "
        f"**Time:** {result.duration_ms} ms",
    ]

    if result.error:
        lines += ["", f"**Error:** `{result.error}`"]

    for w in result.warnings:
        lines += ["", f"⚠️ {w}"]

    if result.ok:
        rows = result.rows
        cols = result.columns
        lines += ["", f"**Rows returned:** {len(rows)}"]
        if cols:
            lines += ["", _md_table(cols, rows)]

    if result.mock_preview:
        lines += ["", "### Mock Data Preview"]
        for tname, rows in result.mock_preview.items():
            lines += [
                "", f"**{tname}**", "",
                "```json",
                json.dumps(rows, ensure_ascii=False, indent=2, default=str),
                "```",
            ]

    return "\n".join(lines)


def _md_table(columns: list[str], rows: list[dict[str, Any]]) -> str:
    def cell(v: Any) -> str:
        return str(v if v is not None else "").replace("|", "\\|").replace("\n", " ")

    header = "| " + " | ".join(columns) + " |"
    sep    = "| " + " | ".join("---" for _ in columns) + " |"
    body   = [
        "| " + " | ".join(cell(row.get(c)) for c in columns) + " |"
        for row in rows[:20]
    ]
    return "\n".join([header, sep] + body)