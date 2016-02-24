"""
HTTP controllers for the HXL Proxy
David Megginson
January 2015

License: Public Domain
Documentation: http://hxlstandard.org
"""

import flask, hxl, urllib, werkzeug

from . import app, auth, cache, dao, filters, preview, util, validate


# FIXME - move somewhere else
RECIPE_ARG_BLACKLIST = [
    'cloneable',
    'description',
    'details'
    'name',
    'passhash',
    'password',
    'password-repeat',
    'recipe_id',
    'severity',
    'stub',
]
"""Properties that should never appear in a recipe's args dictionary"""


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
    return flask.render_template('error.html', e=e, category=type(e)), status

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
    flask.request.parameter_storage_class = werkzeug.datastructures.ImmutableOrderedMultiDict
    flask.g.member = flask.session.get('member_info')


#
# Redirects for deprecated URL patterns
#

@app.route("/")
def redirect_home():
    # home isn't moved permanently
    return flask.redirect("/data/source?" + urllib.parse.urlencode(flask.request.args) , 302)


#
# Primary controllers
#

@app.route("/data/<recipe_id>/login")
def show_data_login(recipe_id):
    recipe = util.get_recipe(recipe_id)
    return flask.render_template('data-login.html', recipe=recipe)

@app.route("/data/source")
@app.route("/data/<recipe_id>/source")
def show_data_source(recipe_id=None):
    """Choose a new data source."""

    try:
        recipe = util.get_recipe(recipe_id, auth=True)
    except werkzeug.exceptions.Forbidden as e:
        return flask.redirect(util.make_data_url(recipe_id=recipe_id, facet='login'), 303)

    return flask.render_template('data-source.html', recipe=recipe)


@app.route("/data/tagger")
@app.route("/data/<recipe_id>/tagger")
def show_data_tag(recipe_id=None):
    """Add HXL tags to an untagged dataset."""

    try:
        recipe = util.get_recipe(recipe_id, auth=True)
    except werkzeug.exceptions.Forbidden as e:
        return flask.redirect(util.make_data_url(recipe_id=recipe_id, facet='login'), 303)

    header_row = flask.request.args.get('header-row')
    if header_row:
        header_row = int(header_row)

    if not recipe['args'].get('url'):
        flask.flash('Please choose a data source first.')
        return flask.redirect(util.make_data_url(recipe, facet='source'), 303)

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
        
    return flask.render_template('data-tagger.html', recipe=recipe, preview=preview, header_row=header_row)


@app.route("/data/edit")
@app.route("/data/<recipe_id>/edit", methods=['GET', 'POST'])
def show_data_edit(recipe_id=None):
    """Create or edit a filter pipeline."""

    try:
        recipe = util.get_recipe(recipe_id, auth=True)
    except werkzeug.exceptions.Forbidden as e:
        return flask.redirect(util.make_data_url(recipe_id=recipe_id, facet='login'), 303)


    if recipe['args'].get('url'):
        # show only a short preview
        try:
            source = preview.PreviewFilter(filters.setup_filters(recipe), max_rows=5)
            source.columns # force-trigger an exception if not tagged
        except:
            flask.flash('No HXL tags found')
            return flask.redirect(util.make_data_url(recipe, facet='tagger'), 303)
    else:
        flask.flash('Please choose a data source first.')
        return flask.redirect(util.make_data_url(recipe, facet='source'), 303)

    # Figure out how many filter forms to show
    filter_count = 0
    for n in range(1, filters.MAX_FILTER_COUNT):
        if recipe['args'].get('filter%02d' % n):
            filter_count = n
    if filter_count < filters.MAX_FILTER_COUNT:
        filter_count += 1

    show_headers = (recipe['args'].get('strip-headers') != 'on')

    return flask.render_template('data-recipe.html', recipe=recipe, source=source, show_headers=show_headers, filter_count=filter_count)

@app.route("/data/recipe")
@app.route("/data/<recipe_id>/recipe")
def show_data_recipe(recipe_id=None):
    """Show form to save a recipe."""

    try:
        recipe = util.get_recipe(recipe_id, auth=True)
    except werkzeug.exceptions.Forbidden as e:
        return flask.redirect(util.make_data_url(recipe_id=recipe_id, facet='login'), 303)

    if not recipe or not recipe['args'].get('url'):
        return flask.redirect('/data/source', 303)

    return flask.render_template('data-about.html', recipe=recipe)

@app.route('/data/<recipe_id>/chart')
@app.route('/data/chart')
def show_data_chart(recipe_id=None):
    """Show a chart visualisation for the data."""

    def find_column(source, pattern):
        for column in source.columns:
            if pattern.match(column):
                return column
        return None
    
    recipe = util.get_recipe(recipe_id)
    if not recipe or not recipe['args'].get('url'):
        return flask.redirect('/data/source', 303)

    source = filters.setup_filters(recipe)

    args = flask.request.args

    value_tag = args.get('value_tag')
    value_col = None
    if value_tag:
        value_tag = hxl.TagPattern.parse(value_tag)
        value_col = find_column(source, value_tag)

    label_tag = args.get('label_tag')
    label_col = None
    if label_tag:
        label_tag = hxl.TagPattern.parse(label_tag)
        label_col = find_column(source, label_tag)

    filter_tag = args.get('filter_tag')
    filter_col = None
    filter_value = args.get('filter_value')
    filter_values = set()
    if filter_tag:
        filter_tag = hxl.TagPattern.parse(filter_tag)
        filter_col = find_column(source, filter_tag)
        filter_values = source.get_value_set(filter_tag)

    count_tag = args.get('count_tag')
    count_col = None
    if count_tag:
        count_tag = hxl.TagPattern.parse(count_tag)
        count_col = find_column(source, count_tag)
        
    type = args.get('type', 'bar')
    
    return flask.render_template(
        'visualise-chart.html',
        recipe_id=recipe_id, recipe=recipe, type=type, source=source,
        value_tag=value_tag, value_col=value_col,
        label_tag=label_tag, label_col=label_col,
        count_tag=count_tag, count_col=count_col,
        filter_tag=filter_tag, filter_col=filter_col,
        filter_values=sorted(filter_values), filter_value=filter_value
    )

@app.route('/data/<recipe_id>/map')
@app.route('/data/map')
def show_data_map(recipe_id=None):
    """Show a map visualisation for the data."""
    recipe = util.get_recipe(recipe_id)
    if not recipe or not recipe['args'].get('url'):
        return flask.redirect('/data/source', 303)
    layer_tag = hxl.TagPattern.parse(flask.request.args.get('layer', 'adm1'))
    return flask.render_template('visualise-map.html', recipe=recipe, layer_tag=layer_tag)

@app.route("/data/validate")
@app.route("/data/<recipe_id>/validate")
def show_validate(recipe_id=None):
    """Validate the data."""

    # Get the recipe
    recipe = util.get_recipe(recipe_id)
    if not recipe or not recipe['args'].get('url'):
        return flask.redirect('/data/source', 303)

    # Get the parameters
    url = recipe['args'].get('url')
    args = flask.request.args
    if args.get('schema_url'):
        schema_url = args.get('schema_url', None)
    else:
        schema_url = recipe['args'].get('schema_url', None)

    severity_level = args.get('severity', 'info')

    detail_hash = args.get('details', None)

    # If we have a URL, validate the data.
    if url:
        errors = validate.do_validate(filters.setup_filters(recipe), schema_url, severity_level)

    return flask.render_template(
        'validate-summary.html',
        recipe=recipe, schema_url=schema_url, errors=errors, detail_hash=detail_hash, severity=severity_level
    )

@app.route("/data/<recipe_id>.<format>")
@app.route("/data/<recipe_id>/download/<stub>.<format>")
@app.route("/data.<format>")
@app.route("/data")
@app.route("/data/<recipe_id>") # must come last, or it will steal earlier patterns
@cache.cached(key_prefix=util.make_cache_key, unless=util.skip_cache_p)
def show_data(recipe_id=None, format="html", stub=None):

    def get_result (recipe_id, format):
        recipe = util.get_recipe(recipe_id, auth=False)
        if not recipe or not recipe['args'].get('url'):
            return flask.redirect('/data/source', 303)

        source = filters.setup_filters(recipe)
        show_headers = (recipe['args'].get('strip-headers') != 'on')

        if format == 'html':
            return flask.render_template('data-view.html', source=source, recipe=recipe, show_headers=show_headers)
        elif format == 'json':
            response = flask.Response(list(source.gen_json(show_headers=show_headers)), mimetype='application/json')
            response.headers['Access-Control-Allow-Origin'] = '*'
            if recipe.get('stub'):
                response.headers['Content-Disposition'] = 'attachment; filename={}.json'.format(recipe['stub'])
            return response
        else:
            response = flask.Response(list(source.gen_csv(show_headers=show_headers)), mimetype='text/csv')
            response.headers['Access-Control-Allow-Origin'] = '*'
            if recipe.get('stub'):
                response.headers['Content-Disposition'] = 'attachment; filename={}.csv'.format(recipe['stub'])
            return response

    result = get_result(recipe_id, format)
    if util.skip_cache_p():
        # Want to store the new value, but can't get the key to work
        # Clearing the whole cache for now (heavy-handed)
        cache.set(show_data.make_cache_key(), result)
    return result

@app.route("/actions/login", methods=['POST'])
def do_data_login():
    destination = flask.request.form.get('from')
    if not destination:
        destination = '/data'
    password = flask.request.form.get('password')
    flask.session['passhash'] = util.make_md5(password)
    return flask.redirect(destination, 303)

@app.route("/actions/save-recipe", methods=['POST'])
def do_data_save():
    """
    Start a new saved pipeline, or update an existing one.

    Can be called from the full pipeline-edit form, or from
    the mini popup for a pipeline that the user is saving
    for the first time.
    """

    # We will have a recipe_id if we're updating an existing pipeline
    recipe_id = flask.request.form.get('recipe_id')
    try:
        recipe = util.get_recipe(recipe_id, auth=True, args=flask.request.form)
    except werkzeug.exceptions.Forbidden as e:
        return flask.redirect(util.make_data_url(recipe_id=recipe_id, facet='login'), 303)

    # Update recipe metadata
    if 'name' in flask.request.form:
        recipe['name'] = flask.request.form['name']
    if 'description' in flask.request.form:
        recipe['description'] = flask.request.form['description']
    if 'cloneable' in flask.request.form:
        recipe['cloneable'] = (flask.request.form['cloneable'] == 'on')
    if 'stub' in flask.request.form:
        recipe['stub'] = flask.request.form['stub']

    # merge args
    recipe['args'] = {}
    for name in flask.request.form:
        if flask.request.form.get(name) and name not in RECIPE_ARG_BLACKLIST:
            recipe['args'][name] = flask.request.form.get(name)

    # check for a password change
    password = flask.request.form.get('password')
    password_repeat = flask.request.form.get('password-repeat')

    if recipe_id:
        # Updating an existing recipe.
        if password:
            if password == password_repeat:
                recipe['passhash'] = util.make_md5(password)
                flask.session['passhash'] = recipe['passhash']
            else:
                raise werkzeug.exceptions.BadRequest("Passwords don't match")
        dao.recipes.update(recipe)
    else:
        # Creating a new recipe.
        if password == password_repeat:
            recipe['passhash'] = util.make_md5(password)
            flask.session['passhash'] = recipe['passhash']
        else:
            raise werkzeug.exceptions.BadRequest("Passwords don't match")
        recipe_id = util.make_recipe_id()
        recipe['recipe_id'] = recipe_id
        dao.recipes.create(recipe)
        # FIXME other auth information is in __init__.py
        flask.session['passhash'] = recipe['passhash']

    # TODO be more specific about what we clear
    cache.clear()

    return flask.redirect(util.make_data_url(recipe), 303)

@app.route('/settings/user')
def do_user_settings():
    if flask.g.member:
        return flask.render_template('settings-user.html', member=flask.g.member)
    else:
        return flask.redirect('/login', 303)

@app.route('/login')
def do_login():
    flask.session['login_redirect'] = flask.request.args.get('from', '/')
    return flask.redirect(auth.get_hid_login_url(), 303)

@app.route('/logout')
def do_logout():
    path = flask.request.args.get('from', '/')
    flask.session.clear()
    flask.flash("Disconnected from your Humanitarian.ID account (browsing anonymously).")
    return flask.redirect(path, 303)

@app.route('/oauth/authorized2/1')
def do_hid_authorisation():
    # now needs to submit the access token to H.ID to get more info
    code = flask.request.args.get('code')
    state = flask.request.args.get('state')
    if state != flask.session.get('state'):
        raise Exception("Security violation: inconsistent state returned from humanitarian.id login request")
    else:
        flask.session['state'] = None
    user_info = auth.get_hid_user(code)
    redirect_path = flask.session.get('login_redirect', '/')
    del flask.session['login_redirect']
    flask.session['member_info'] = user_info
    flask.flash("Connected to your Humanitarian.ID account as {}".format(user_info.get('name')))
    return flask.redirect(redirect_path, 303)

# end
