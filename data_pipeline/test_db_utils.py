import unittest
import pandas as pd
from sqlalchemy import inspect, text

from db_utils import DBHelper


class TestDBHelperSQLInjection(unittest.TestCase):
    def setUp(self):
        self.db = DBHelper('sqlite://')
        with self.db.engine.begin() as conn:
            conn.execute(text('CREATE TABLE safe_table (id INTEGER)'))
            conn.execute(text('INSERT INTO safe_table (id) VALUES (1)'))

    def tearDown(self):
        self.db.close()

    def test_malicious_table_name_does_not_execute(self):
        df = pd.DataFrame({'col1': [1]})
        malicious = 'malicious; DROP TABLE safe_table;--'
        self.db.create_table(malicious, df)
        self.db.insert_row(malicious, {'col1': 1})

        inspector = inspect(self.db.engine)
        self.assertIn('safe_table', inspector.get_table_names())

        preparer = self.db.engine.dialect.identifier_preparer
        quoted = preparer.quote(malicious)
        with self.db.engine.connect() as conn:
            count = conn.execute(text('SELECT count(*) FROM safe_table')).scalar()
            self.assertEqual(count, 1)
            value = conn.execute(text(f'SELECT col1 FROM {quoted}')).scalar()
            self.assertEqual(value, 1)
