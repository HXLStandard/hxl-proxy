""" Unit tests for hxl_proxy.recipe module
David Megginson
April 2019
License: Public Domain
"""

import unittest

from hxl_proxy.recipe import Recipe

from . import base


class TestConstructor(base.AbstractDBTest):

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def test_params(self):
        args = {
            "url": "http://example.org/data.csv",
        }
        recipe = Recipe(request_args=args)
        self.assertEqual(args["url"], recipe.args.get("url"))
        self.assertEqual(args["url"], recipe.url)
        self.assertTrue(recipe.recipe_id is None)

    def test_saved(self):
        recipe_id = 'AAAAA'
        recipe = Recipe(recipe_id=recipe_id, request_args={})
