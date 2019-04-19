""" Unit tests for hxl_proxy.recipe module
David Megginson
April 2019
License: Public Domain
"""

import unittest

from hxl_proxy.recipe import Recipe

from . import base


class TestConstructor(base.AbstractDBTest):

    def test_params(self):

        ARGS = {
            "url": "http://example.org/data.csv",
        }
        recipe = Recipe(request_args=ARGS)
        self.assertEqual(ARGS["url"], recipe.args.get("url"))
        self.assertEqual(ARGS["url"], recipe.url)
