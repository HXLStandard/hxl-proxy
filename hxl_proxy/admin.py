""" Admin functions """

from hxl_proxy import app
from flask import flash, session
from hxl_proxy import dao, exceptions, util

import hashlib, json



########################################################################
# Authentication and authorisation
########################################################################

def admin_auth ():
    """ Check authorisation for admin tasks
    Will redirect to a login page if not authorised.
    ADMIN_PASSWORD_MD5 must be set in the config file
    """
    if not session.get('is_admin'):
        flash("Password required for admin functions")
        raise exceptions.RedirectException('/admin/login')


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
    admin_auth()
    session['is_admin'] = False



########################################################################
# Admin functions for recipes
########################################################################

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


def do_admin_update_recipe (fields):
    """ POST action: force-update a saved recipe """

    admin_auth()

    # original data fields
    data_fields = dao.recipes.read(fields['recipe_id'])

    # try parsing the JSON args string
    try:
        fields['args'] = json.loads(fields['args'])
    except:
        flash("Parsing error in JSON arguments; restoring old values")
        raise exceptions.RedirectException("/admin/recipes/{}/edit.html".format(fields['recipe_id']))

    # munge the checkbox value
    if fields.get('cloneable') == 'on':
        if 'authorization_token' in fields['args']:
            flash("Cannot make recipe cloneable (contains authorisation token)")
            fields['cloneable'] = False
        else:
            fields['cloneable'] = True
    else:
        fields['cloneable'] = False

    # see if there's a new password
    if fields.get('password'):
        flash("Updated recipe password")
        fields['passhash'] = util.make_md5(fields['password'])
        del fields['password']

    # copy over the new fields
    for key in fields:
        data_fields[key] = fields[key]

    # save to the database
    dao.recipes.update(data_fields)

    
def do_admin_delete_recipe (recipe_id):
    admin_auth()
    dao.recipes.delete(recipe_id)
    
