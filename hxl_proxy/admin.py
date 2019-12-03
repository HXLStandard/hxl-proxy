""" Admin functions """

from hxl_proxy import dao

def admin_get_recipes ():
    recipes = dao.recipes.list()
    return recipes

def admin_get_recipe (recipe_id):
    recipe = dao.recipes.read(recipe_id)
    return recipe
