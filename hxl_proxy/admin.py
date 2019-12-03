""" Admin functions """

from hxl_proxy import dao

def admin_get_recipes ():
    cursor = dao.recipes.list()
    return cursor
