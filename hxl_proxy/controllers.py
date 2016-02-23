"""
Controllers for the HXL Proxy
David Megginson
January 2015

License: Public Domain
Documentation: http://hxlstandard.org
"""

import os
import sys
import copy
import base64
import urllib
import tempfile

import werkzeug
from werkzeug import secure_filename
from werkzeug.exceptions import BadRequest, Unauthorized, Forbidden, NotFound

from flask import Response, flash, request, render_template, redirect, make_response, session, g, url_for

import hxl

from hxl_proxy import app, cache, dao
from hxl_proxy.util import get_recipe, check_auth, make_data_url, make_cache_key, skip_cache_p, urlencode_utf8, make_md5, make_recipe_id
from hxl_proxy.filters import setup_filters, MAX_FILTER_COUNT
from hxl_proxy.validate import do_validate
from hxl_proxy.hdx import get_hdx_datasets
from hxl_proxy.preview import PreviewFilter
from hxl_proxy.auth import get_hid_login_url, get_hid_user

BLACKLIST = ['password', 'password-repeat', 'name', 'description', 'cloneable', 'stub', 'recipe_id']

#
# Error handling
#

def error(e):
    """Default error page."""
    if isinstance(e, IOError):
        # probably tried to open an inappropriate URL
        status = 403
    else:
        status = 500
    return render_template('error.html', e=e, category=type(e)), status

if not app.config.get('DEBUG'):
    # Register only if not in DEBUG mode
    app.register_error_handler(BaseException, error)


#
# Meta handlers
#

@app.before_request
def before_request():
    """Code to run immediately before the request"""
    app.secret_key = app.config['SECRET_KEY']
    request.parameter_storage_class = werkzeug.datastructures.ImmutableOrderedMultiDict
    g.member = session.get('member_info')

#
# Redirects for deprecated URL patterns
#

@app.route("/")
def redirect_home():
    # home isn't moved permanently
    return redirect("/data/source?" + urllib.parse.urlencode(request.args) , 302)

#
# Primary controllers
#

@app.route("/data/<recipe_id>/login")
def show_data_login(recipe_id):
    recipe = get_recipe(recipe_id)
    return render_template('data-login.html', recipe_id=recipe_id, recipe=recipe)

@app.route("/data/source")
@app.route("/data/<recipe_id>/source")
def show_data_source(recipe_id=None):
    """Choose a new data source."""

    try:
        recipe = get_recipe(recipe_id, auth=True)
    except Forbidden as e:
        return redirect(make_data_url(recipe_id=recipe_id, facet='login'), 303)

    return render_template('data-source.html', recipe_id=recipe_id, recipe=recipe)


@app.route("/data/tagger")
@app.route("/data/<recipe_id>/tagger")
def show_data_tag(recipe_id=None):
    """Add HXL tags to an untagged dataset."""

    try:
        recipe = get_recipe(recipe_id, auth=True)
    except Forbidden as e:
        return redirect(make_data_url(recipe_id=recipe_id, facet='login'), 303)

    header_row = request.args.get('header-row')
    if header_row:
        header_row = int(header_row)

    if not recipe['args'].get('url'):
        flash('Please choose a data source first.')
        return redirect(make_data_url(recipe, facet='source'), 303)

    try:
        sheet_index = int(recipe['args'].get('sheet', 0))
    except:
        sheet_index = 0

    preview = []
    i = 0
    for row in hxl.io.make_input(recipe['args'].get('url'), sheet_index=0):
        if i >= 25:
            break
        else:
            i = i + 1
        if row:
            preview.append(row)
        
    return render_template('data-tagger.html', recipe_id=recipe_id, recipe=recipe, preview=preview, header_row=header_row)


@app.route("/data/edit")
@app.route("/data/<recipe_id>/edit", methods=['GET', 'POST'])
def show_data_edit(recipe_id=None):
    """Create or edit a filter pipeline."""

    try:
        recipe = get_recipe(recipe_id, auth=True)
    except Forbidden as e:
        return redirect(make_data_url(recipe_id=recipe_id, facet='login'), 303)


    if recipe['args'].get('url'):
        # show only a short preview
        try:
            source = PreviewFilter(setup_filters(recipe), max_rows=5)
            source.columns # force-trigger an exception if not tagged
        except:
            flash('No HXL tags found')
            return redirect(make_data_url(recipe, facet='tagger'), 303)
    else:
        flash('Please choose a data source first.')
        return redirect(make_data_url(recipe, facet='source'), 303)

    # Figure out how many filter forms to show
    filter_count = 0
    for n in range(1, MAX_FILTER_COUNT):
        if recipe['args'].get('filter%02d' % n):
            filter_count = n
    if filter_count < MAX_FILTER_COUNT:
        filter_count += 1

    show_headers = (recipe['args'].get('strip-headers') != 'on')

    return render_template('data-recipe.html', recipe_id=recipe_id, recipe=recipe, source=source, show_headers=show_headers, filter_count=filter_count)

@app.route("/data/recipe")
@app.route("/data/<recipe_id>/recipe")
def show_data_recipe(recipe_id=None):
    """Show form to save a recipe."""

    try:
        recipe = get_recipe(recipe_id, auth=True)
    except Forbidden as e:
        return redirect(make_data_url(recipe_id=recipe_id, facet='login'), 303)

    if not recipe or not recipe['args'].get('url'):
        return redirect('/data/source', 303)

    return render_template('data-about.html', recipe_id=recipe_id, recipe=recipe)

@app.route('/data/<recipe_id>/chart')
@app.route('/data/chart')
def show_data_chart(recipe_id=None):
    """Show a chart visualisation for the data."""
    recipe = get_recipe(recipe_id)
    if not recipe or not recipe['args'].get('url'):
        return redirect('/data/source', 303)

    source = setup_filters(recipe)

    value_tag = request.args.get('value_tag')
    if value_tag:
        value_tag = hxl.TagPattern.parse(value_tag)

    label_tag = request.args.get('label_tag')
    if label_tag:
        label_tag = hxl.TagPattern.parse(label_tag)

    filter_tag = request.args.get('filter_tag')
    filter_value = request.args.get('filter_value')
    filter_values = set()
    if filter_tag:
        filter_tag = hxl.TagPattern.parse(filter_tag)
        filter_values = source.get_value_set(filter_tag)

    count_tag = request.args.get('count_tag')
    if count_tag:
        count_tag = hxl.TagPattern.parse(count_tag)
        
    type = request.args.get('type', 'bar')
    
    return render_template(
        'visualise-chart.html',
        recipe_id=recipe_id, recipe=recipe, type=type, source=source,
        value_tag=value_tag, label_tag=label_tag, count_tag=count_tag,
        filter_tag=filter_tag, filter_values=sorted(filter_values), filter_value=filter_value
    )

@app.route('/data/<recipe_id>/map')
@app.route('/data/map')
def show_data_map(recipe_id=None):
    """Show a map visualisation for the data."""
    recipe = get_recipe(recipe_id)
    if not recipe or not recipe['args'].get('url'):
        return redirect('/data/source', 303)
    layer_tag = hxl.TagPattern.parse(request.args.get('layer', 'adm1'))
    return render_template('visualise-map.html', recipe_id=recipe_id, recipe=recipe, layer_tag=layer_tag)

@app.route("/data/validate")
@app.route("/data/<recipe_id>/validate")
def show_validate(recipe_id=None):
    """Validate the data."""

    # Get the recipe
    recipe = get_recipe(recipe_id)
    if not recipe or not recipe['args'].get('url'):
        return redirect('/data/source', 303)

    # Get the parameters
    url = recipe['args'].get('url')
    if request.args.get('schema_url'):
        schema_url = request.args.get('schema_url', None)
    else:
        schema_url = recipe['args'].get('schema_url', None)

    severity_level = request.args.get('severity', 'info')

    detail_hash = request.args.get('details', None)

    # If we have a URL, validate the data.
    if url:
        errors = do_validate(setup_filters(recipe), schema_url, severity_level)

    return render_template('validate-summary.html', recipe_id=recipe_id, recipe=recipe, schema_url=schema_url, errors=errors, detail_hash=detail_hash, severity=severity_level)

@app.route("/data/<recipe_id>.<format>")
@app.route("/data/<recipe_id>/download/<stub>.<format>")
@app.route("/data.<format>")
@app.route("/data")
@app.route("/data/<recipe_id>") # must come last, or it will steal earlier patterns
@cache.cached(key_prefix=make_cache_key, unless=skip_cache_p)
def show_data(recipe_id=None, format="html", stub=None):

    def get_result (recipe_id, format):
        recipe = get_recipe(recipe_id, auth=False)
        if not recipe or not recipe['args'].get('url'):
            return redirect('/data/source', 303)

        source = setup_filters(recipe)
        show_headers = (recipe['args'].get('strip-headers') != 'on')

        if format == 'html':
            return render_template('data-view.html', source=source, recipe=recipe, recipe_id=recipe_id, show_headers=show_headers)
        elif format == 'json':
            response = Response(list(source.gen_json(show_headers=show_headers)), mimetype='application/json')
            response.headers['Access-Control-Allow-Origin'] = '*'
            if recipe.get('stub'):
                response.headers['Content-Disposition'] = 'attachment; filename={}.json'.format(recipe['stub'])
            return response
        else:
            response = Response(list(source.gen_csv(show_headers=show_headers)), mimetype='text/csv')
            response.headers['Access-Control-Allow-Origin'] = '*'
            if recipe.get('stub'):
                response.headers['Content-Disposition'] = 'attachment; filename={}.csv'.format(recipe['stub'])
            return response

    result = get_result(recipe_id, format)
    if skip_cache_p():
        # Want to store the new value, but can't get the key to work
        # Clearing the whole cache for now (heavy-handed)
        cache.set(show_data.make_cache_key(), result)
    return result

@app.route("/actions/login", methods=['POST'])
def do_data_login():
    destination = request.form.get('from')
    if not destination:
        destination = '/data'
    password = request.form.get('password')
    session['passhash'] = make_md5(password)
    return redirect(destination, 303)

@app.route("/actions/save-recipe", methods=['POST'])
def do_data_save():
    """
    Start a new saved pipeline, or update an existing one.

    Can be called from the full pipeline-edit form, or from
    the mini popup for a pipeline that the user is saving
    for the first time.
    """

    # We will have a recipe_id if we're updating an existing pipeline
    recipe_id = request.form.get('recipe_id')
    try:
        recipe = get_recipe(recipe_id, auth=True, args=request.form)
    except Forbidden as e:
        return redirect(make_data_url(recipe_id=recipe_id, facet='login'), 303)

    # Update recipe metadata
    if 'name' in request.form:
        recipe['name'] = request.form['name']
    if 'description' in request.form:
        recipe['description'] = request.form['description']
    if 'cloneable' in request.form:
        recipe['cloneable'] = (request.form['cloneable'] == 'on')
    if 'stub' in request.form:
        recipe['stub'] = request.form['stub']

    # merge args
    recipe['args'] = {}
    for name in request.form:
        if request.form.get(name) and name not in BLACKLIST:
            recipe['args'][name] = request.form.get(name)

    # check for a password change
    password = request.form.get('password')
    password_repeat = request.form.get('password-repeat')

    if recipe_id:
        # Updating an existing recipe.
        if password:
            if password == password_repeat:
                recipe['passhash'] = make_md5(password)
                session['passhash'] = recipe['passhash']
            else:
                raise BadRequest("Passwords don't match")
        dao.recipes.update(recipe)
    else:
        # Creating a new recipe.
        if password == password_repeat:
            recipe['passhash'] = make_md5(password)
            session['passhash'] = recipe['passhash']
        else:
            raise BadRequest("Passwords don't match")
        recipe_id = make_recipe_id()
        recipe['recipe_id'] = recipe_id
        dao.recipes.create(recipe)
        # FIXME other auth information is in __init__.py
        session['passhash'] = recipe['passhash']

    # TODO be more specific about what we clear
    cache.clear()

    return redirect(make_data_url(recipe), 303)

@app.route('/settings/user')
def do_user_settings():
    if g.member:
        return render_template('settings-user.html', member=g.member)
    else:
        return redirect('/login', 303)

@app.route('/login')
def do_login():
    session['login_redirect'] = request.args.get('from', '/')
    return redirect(get_hid_login_url(), 303)

@app.route('/logout')
def do_logout():
    path = request.args.get('from', '/')
    session.clear()
    flash("Disconnected from your Humanitarian.ID account (browsing anonymously).")
    return redirect(path, 303)

@app.route('/oauth/authorized2/1')
def do_hid_authorisation():
    # now needs to submit the access token to H.ID to get more info
    code = request.args.get('code')
    state = request.args.get('state')
    if state != session.get('state'):
        raise Exception("Security violation: inconsistent state returned from humanitarian.id login request")
    else:
        session['state'] = None
    user_info = get_hid_user(code)
    redirect_path = session.get('login_redirect', '/')
    del session['login_redirect']
    session['member_info'] = user_info
    flash("Connected to your Humanitarian.ID account as {}".format(user_info.get('name')))
    return redirect(redirect_path, 303)

# end
