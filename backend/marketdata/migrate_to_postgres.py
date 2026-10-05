from __future__ import annotations

import argparse
import os
import sqlite3

from marketdata import store

TABLES = {
    "candles": (
        "CREATE TABLE IF NOT EXISTS candles (symbol TEXT NOT NULL, timeframe TEXT NOT NULL, ts BIGINT NOT NULL,"
        " open DOUBLE PRECISION NOT NULL, high DOUBLE PRECISION NOT NULL, low DOUBLE PRECISION NOT NULL,"
        " close DOUBLE PRECISION NOT NULL, volume DOUBLE PRECISION NOT NULL, PRIMARY KEY (symbol, timeframe, ts))"
    ),
    "backtest_runs": (
        "CREATE TABLE IF NOT EXISTS backtest_runs (id BIGINT PRIMARY KEY, created_at TEXT NOT NULL,"
        " kind TEXT NOT NULL, params TEXT NOT NULL, result TEXT NOT NULL)"
    ),
}


class MigrationError(Exception):
    pass


def _count(pg, table: str) -> int:
    row = pg.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
    return int(row[0]) if row else 0


def migrate(sqlite_path: str, database_url: str, *, replace: bool = False, dry_run: bool = False) -> dict:
    src = sqlite3.connect(f"file:{sqlite_path}?mode=ro", uri=True)
    report: dict[str, dict[str, int]] = {}
    try:
        data = {}
        for table in TABLES:
            cur = src.execute(f"SELECT * FROM {table}")
            data[table] = ([c[0] for c in cur.description], cur.fetchall())
            report[table] = {"source": len(data[table][1]), "target": 0}
        if dry_run:
            return report

        import psycopg

        with psycopg.connect(database_url) as pg:
            for table, ddl in TABLES.items():
                pg.execute(ddl)
                existing = _count(pg, table)
                if existing and not replace:
                    raise MigrationError(f"{table} already has {existing} rows; pass --replace to overwrite")
                if replace:
                    pg.execute(f"DELETE FROM {table}")
            for table, (columns, rows) in data.items():
                marks = ", ".join(["%s"] * len(columns))
                with pg.cursor() as pg_cur:
                    pg_cur.executemany(f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({marks})", rows)
            for table in TABLES:
                report[table]["target"] = _count(pg, table)
        bad = {t: r for t, r in report.items() if r["source"] != r["target"]}
        if bad:
            raise MigrationError(f"row counts differ after copy: {bad}")
        return report
    finally:
        src.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Copy the SQLite store to PostgreSQL")
    parser.add_argument("--sqlite", default=store.db_path())
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    url = os.environ.get("DATABASE_URL", "")
    if not url and not args.dry_run:
        raise SystemExit("DATABASE_URL is not set")
    for table, counts in migrate(args.sqlite, url, replace=args.replace, dry_run=args.dry_run).items():
        print(f"{table}: {counts['source']} -> {counts['target']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
