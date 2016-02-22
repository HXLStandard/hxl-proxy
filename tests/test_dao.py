"""
Unit tests for hxl-proxy dao module
David Megginson
February 2016

License: Public Domain
"""

import unittest, os
from hxl_proxy import app, dao


class AbstractDBTest(unittest.TestCase):
    
    def setUp(self):
        # Prime with an in-memory database
        dao.create_db()
        dao.execute_file(os.path.join(os.path.dirname(__file__), 'test-data.sql'))

class TestDB(AbstractDBTest):

    def test_get_db(self):
        assert dao.get_db() is not None

    def test_execute_statement(self):
        dao.execute_statement(
            "delete from Recipes where recipe_id=?", ('AAAAA',), commit=True
        )
        assert not dao.fetchone("select * from Recipes where recipe_id=?", ('AAAAA',))

    def test_fetchone(self):
        row = dao.fetchone("select * from Users where user_id=?", ('user1',))
        self.assertEqual(row.get('email'), 'user1@example.org')
