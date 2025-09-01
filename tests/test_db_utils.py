import unittest
from unittest.mock import MagicMock, patch

import pandas as pd
from sqlalchemy import Column, Float, MetaData, Table
from sqlalchemy import Text as SAText
from sqlalchemy import inspect, text
from sqlalchemy.dialects import mysql, postgresql

from data_pipeline.db_utils import DBHelper


class TestDBHelperSQLInjection(unittest.TestCase):
    def setUp(self):
        self.db = DBHelper("sqlite://")
        with self.db.engine.begin() as conn:
            conn.execute(text("CREATE TABLE safe_table (id INTEGER)"))
            conn.execute(text("INSERT INTO safe_table (id) VALUES (1)"))

    def tearDown(self):
        self.db.close()

    def test_malicious_table_name_does_not_execute(self):
        df = pd.DataFrame({"col1": [1]})
        malicious = "malicious; DROP TABLE safe_table;--"
        self.db.create_table(malicious, df)
        self.db.insert_row(malicious, {"col1": 1})

        inspector = inspect(self.db.engine)
        self.assertIn("safe_table", inspector.get_table_names())

        preparer = self.db.engine.dialect.identifier_preparer
        quoted = preparer.quote(malicious)
        with self.db.engine.connect() as conn:
            count = conn.execute(
                text("SELECT count(*) FROM safe_table")).scalar()
            self.assertEqual(count, 1)
            value = conn.execute(text(f"SELECT col1 FROM {quoted}")).scalar()
            self.assertEqual(value, 1)


class TestInsertDialect(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame(
            {
                "Ticker": ["A.L", "B.L"],
                "Close": [100, 200],
                "Volume": [1000, 1500],
            }
        )

    def _prepare_helper(self, dialect):
        helper = DBHelper("sqlite://")
        helper.engine.dialect = dialect

        conn = MagicMock()
        ctx = MagicMock()
        ctx.__enter__.return_value = conn
        ctx.__exit__.return_value = False
        helper.engine.begin = MagicMock(return_value=ctx)

        table = Table(
            "test_tbl",
            MetaData(),
            Column("Ticker", SAText, primary_key=True),
            Column("Close", Float),
            Column("Volume", Float),
        )
        patcher = patch("data_pipeline.db_utils.Table", return_value=table)
        patcher.start()
        self.addCleanup(patcher.stop)

        return helper, conn

    def test_postgresql_insert_clause(self):
        helper, conn = self._prepare_helper(postgresql.dialect())
        helper.insert_dataframe("test_tbl", self.df, unique_cols=["Ticker"])
        stmt = conn.execute.call_args[0][0]
        compiled = str(stmt.compile(dialect=postgresql.dialect()))
        self.assertIn("ON CONFLICT", compiled)
        helper.close()

    def test_mysql_insert_clause(self):
        helper, conn = self._prepare_helper(mysql.dialect())
        helper.insert_dataframe("test_tbl", self.df, unique_cols=["Ticker"])
        stmt = conn.execute.call_args[0][0]
        compiled = str(stmt.compile(dialect=mysql.dialect()))
        self.assertIn("ON DUPLICATE KEY UPDATE", compiled)
        helper.close()
