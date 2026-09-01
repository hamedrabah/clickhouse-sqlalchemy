from types import SimpleNamespace
from unittest import TestCase

from sqlalchemy import Column, MetaData, String, Table
from sqlalchemy.sql.ddl import CreateTable

from clickhouse_sqlalchemy import engines
from clickhouse_sqlalchemy.alembic.dialect import patch_alembic_version
from clickhouse_sqlalchemy.drivers.base import ClickHouseDialect


class PatchAlembicVersionTestCase(TestCase):
    def _build_context(self):
        version = Table(
            "alembic_version",
            MetaData(),
            Column("version_num", String(32), nullable=False),
        )
        migration_context = SimpleNamespace(_version=version)
        context = SimpleNamespace(
            _proxy=SimpleNamespace(_migration_context=migration_context)
        )
        return context, version

    def test_replacing_merge_tree_uses_stable_sorting_key(self):
        cases = (
            ({}, engines.ReplacingMergeTree),
            (
                {
                    "cluster": "test_cluster",
                    "table_path": "/clickhouse/tables/{shard}/alembic_version",
                    "replica_name": "{replica}",
                },
                engines.ReplicatedReplacingMergeTree,
            ),
        )

        for kwargs, engine_type in cases:
            with self.subTest(engine_type=engine_type.__name__):
                context, version = self._build_context()

                patch_alembic_version(context, **kwargs)

                ddl = str(CreateTable(version).compile(dialect=ClickHouseDialect()))
                self.assertIsInstance(version.engine, engine_type)
                self.assertIn("version_key UInt8 DEFAULT 0", ddl)
                self.assertIn("ORDER BY version_key", ddl)
                self.assertNotIn("allow_suspicious_primary_key", ddl)
