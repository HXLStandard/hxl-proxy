"""
Unit tests for hxl-proxy dao module
David Megginson
February 2016

License: Public Domain
"""

import unittest, os
from hxl_proxy import app, dao


class AbstractDBTest(unittest.TestCase):
    """Abstract base class for DAO tests."""
    
    def setUp(self):
        # Prime with an in-memory database
        dao.create_db()
        dao.execute_file(os.path.join(os.path.dirname(__file__), 'test-data.sql'))

    def assertEquiv(self, model, actual):
        """Test equivalence where everything in model must be the same in actual
        (but actual can have extra values)."""
        for key in model:
            self.assertEqual(model.get(key), actual.get(key), key)


class TestUser(AbstractDBTest):
    """Test user DAO functionality"""

    NEW_USER = {
        'user_id': 'user3',
        'email': 'user3@example.org',
        'name': 'User Three',
        'name_given': 'User',
        'name_family': 'Three'
    }

    def test_create(self):
        dao.user.create(self.NEW_USER)
        result = dao.user.read(self.NEW_USER['user_id'])
        self.assertEquiv(self.NEW_USER, result)
        assert result.get('last_login') is not None

    def test_read(self):
        user = {
            'user_id': 'user1',
            'email': 'user1@example.org',
            'name': 'User One',
            'name_given': 'User',
            'name_family': 'One'
        }
        self.assertEquiv(user, dao.user.read('user1'))

    def test_update(self):
        user = dict(self.NEW_USER)
        user['user_id'] = 'user1'
        dao.user.update(user)
        self.assertEquiv(user, dao.user.read(user['user_id']))

    def test_delete(self):
        dao.user.create(self.NEW_USER)
        assert dao.user.read(self.NEW_USER['user_id']) is not None
        dao.user.delete(self.NEW_USER['user_id'])
        assert dao.user.read(self.NEW_USER['user_id']) is None


class TestRecipe(AbstractDBTest):

    NEW_RECIPE = {
        'recipe_id': 'XXXXX',
        'user_id': 'user1',
        'name': 'Recipe X',
        'description': 'New test recipe',
        'cloneable': 1,
        'stub': 'recipex',
        'args': {}
    }

    def test_create(self):
        dao.recipe.create(self.NEW_RECIPE)
        result = dao.recipe.read(self.NEW_RECIPE['recipe_id'])
        self.assertEquiv(self.NEW_RECIPE, result)
        assert result['date_created']
        self.assertEqual(result['date_created'], result['date_modified'])

    def test_read(self):
        recipe = {
            'recipe_id': 'AAAAA',
            'user_id': 'user1',
            'name': 'Recipe #1',
            'description': 'First test recipe',
            'cloneable': 1,
            'stub': 'recipe1',
            'args': {}
        }
        self.assertEquiv(recipe, dao.recipe.read(recipe['recipe_id']))

    def test_update(self):
        recipe = dict(self.NEW_RECIPE)
        recipe['recipe_id'] = 'AAAAA'
        dao.recipe.update(recipe)
        result = dao.recipe.read('AAAAA')
        self.assertEquiv(recipe, result)
        self.assertNotEqual(result['date_created'], result['date_modified'])

    def test_delete(self):
        assert dao.recipe.read('AAAAA') is not None
        dao.recipe.delete('AAAAA')
        assert dao.recipe.read('AAAAA') is None
