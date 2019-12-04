""" Admin functions """

from hxl_proxy import app
from flask import flash, session
from hxl_proxy import dao, exceptions

import hashlib

def admin_auth ():
    """ Check authorisation for admin tasks
    Will redirect to a login page if not authorised.
    ADMIN_PASSWORD_MD5 must be set in the config file
    """
    if not session.get('is_admin'):
        flash("Password required for admin functions")
        raise exceptions.RedirectException('/admin/login')

def admin_get_recipes ():
    """ Get a list of saved recipes for the admin page
    @returns: a list of recipes (just dicts, not Recipe objects)
    """
    admin_auth()
    recipes = dao.recipes.list()
    return recipes

def admin_get_recipe (recipe_id):
    """ Look up and return a single recipe for the admin page
    @param recipe_id: the hash id for the saved recipe
    @returns: a Recipe object
    """
    admin_auth()
    recipe = dao.recipes.read(recipe_id)
    return recipe

def do_admin_login (password):
    """ POST action: log into admin functions 
    @param password: the text of the admin password
    """
    expected_passhash = app.config.get('ADMIN_PASSWORD_MD5')
    actual_passhash = hashlib.md5(password.encode("utf-8")).hexdigest()
    if expected_passhash == actual_passhash:
        session['is_admin'] = True
    else:
        flash("Wrong password")
        raise exceptions.Redirect('/admin/login')

def do_admin_logout ():
    """ POST action: log out of admin functions """
    session['is_admin'] = False
