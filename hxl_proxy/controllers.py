"""
HTTP controllers for the HXL Proxy
David Megginson
January 2015

License: Public Domain
Documentation: http://hxlstandard.org
"""

import flask, hxl, json, requests, requests_cache, urllib, werkzeug

from . import app, auth, cache, dao, filters, preview, util, validate, exceptions


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

def handle_exception(e):
    """Default error page."""
    if isinstance(e, IOError):
        # probably tried to open an inappropriate URL
        status = 403
    else:
        status = 500
    return flask.render_template('error.html', e=e, category=type(e)), status

app.register_error_handler(Exception, handle_exception)

#
# Redirects
#
def handle_redirect_exception(e):
    if e.message:
        flask.flash(e.message)
    return flask.redirect(e.target_url, e.http_code)

app.register_error_handler(exceptions.RedirectException, handle_redirect_exception)

#
# SSL errors
#
def handle_ssl_error(e):
    flask.flash("SSL error. If you understand the risks, you can check \"Don't verify SSL certificates\" to continue.")
    return flask.redirect(util.make_data_url(recipe=util.get_recipe(), facet='source'), 302)

app.register_error_handler(requests.exceptions.SSLError, handle_ssl_error)

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

    header_row = recipe['args'].get('header-row')
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
    for row in hxl.io.make_input(recipe['args'].get('url'), sheet_index=sheet_index, verify_ssl=util.check_verify_ssl(recipe['args'])):
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
        max_rows = recipe['args'].get('max-rows', None)
        max_rows = min(int(max_rows), 25) if max_rows is not None else 25
        source = preview.PreviewFilter(filters.setup_filters(recipe), max_rows=max_rows)
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

@app.route("/data/save")
@app.route("/data/<recipe_id>/save")
def show_data_recipe(recipe_id=None):
    """Show form to save a recipe."""

    try:
        recipe = util.get_recipe(recipe_id, auth=True)
    except werkzeug.exceptions.Forbidden as e:
        return flask.redirect(util.make_data_url(recipe_id=recipe_id, facet='login'), 303)

    if not recipe or not recipe['args'].get('url'):
        return flask.redirect('/data/source', 303)

    return flask.render_template('data-save.html', recipe=recipe)


@app.route('/data/<recipe_id>/chart')
@app.route('/data/chart')
def show_data_chart(recipe_id=None):
    """Show a chart visualisation for the data."""

    recipe = util.get_recipe(recipe_id)
    if not recipe or not recipe['args'].get('url'):
        return flask.redirect('/data/source', 303)

    source = filters.setup_filters(recipe)

    args = flask.request.args

    value_pattern = args.get('value_tag')
    value_col = None
    if value_pattern:
        value_pattern = hxl.TagPattern.parse(value_pattern)
        value_col = value_pattern.find_column(source.columns)

    label_pattern = args.get('label_tag')
    label_col = None
    if label_pattern:
        label_pattern = hxl.TagPattern.parse(label_pattern)
        label_col = label_pattern.find_column(source.columns)

    filter_pattern = args.get('filter_tag')
    filter_col = None
    filter_value = args.get('filter_value')
    filter_values = set()
    if filter_pattern:
        filter_pattern = hxl.TagPattern.parse(filter_pattern)
        filter_col = filter_pattern.find_column(source.columns)
        filter_values = source.get_value_set(filter_pattern)

    count_pattern = args.get('count_tag')
    count_col = None
    if count_pattern:
        count_pattern = hxl.TagPattern.parse(count_pattern)
        count_col = count_pattern.find_column(source.columns)
        
    type = args.get('type', 'bar')
    
    return flask.render_template(
        'visualise-chart.html',
        recipe_id=recipe_id, recipe=recipe, type=type, source=source,
        value_tag=value_pattern, value_col=value_col,
        label_tag=label_pattern, label_col=label_col,
        count_tag=count_pattern, count_col=count_col,
        filter_tag=filter_pattern, filter_col=filter_col,
        filter_values=sorted(filter_values), filter_value=filter_value
    )


@app.route('/data/<recipe_id>/map')
@app.route('/data/map')
def show_visualise_map(recipe_id=None):
    """Show a map visualisation for the data."""

    # Set up the data source
    recipe = util.get_recipe(recipe_id)
    if not recipe or not recipe['args'].get('url'):
        return flask.redirect('/data/source', 303)
    source = filters.setup_filters(recipe)

    # Get arguments to control map display.
    args = flask.request.args
    default_country = args.get('default_country')

    pcode_pattern = args.get('pcode_tag')
    if pcode_pattern:
        pcode_pattern = hxl.TagPattern.parse(pcode_pattern)
        pcode_col = pcode_pattern.find_column(source.columns)

    value_pattern = args.get('value_tag')
    if value_pattern:
        value_pattern = hxl.TagPattern.parse(value_pattern)
        value_col = value_pattern.find_column(source.columns)

    layer_pattern = args.get('layer_tag')
    if layer_pattern:
        layer_pattern = hxl.TagPattern.parse(layer_pattern)
        layer_col = layer_pattern.find_column(source.columns)

    # Show the map.
    return flask.render_template(
        'visualise-map.html', recipe=recipe,
        default_country=default_country, pcode_tag=pcode_pattern, layer_tag=layer_pattern, value_tag=value_pattern, source=source
    )


@app.route("/data/validate")
@app.route("/data/<recipe_id>/validate")
def show_validate(recipe_id=None):
    """Run a validation and show the result in a dashboard."""

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

@app.route("/data/<recipe_id>/advanced")
@app.route("/data/advanced")
def show_advanced(recipe_id=None):
    """Advanced form for direct JSON entry."""
    recipe = util.get_recipe(recipe_id, auth=True)
    return flask.render_template("data-advanced.html", recipe=recipe)

@app.route("/data/<recipe_id>.<format>")
@app.route("/data/<recipe_id>/download/<stub>.<format>")
@app.route("/data.<format>")
@app.route("/data")
@app.route("/data/download/<stub>.<format>")
@app.route("/data/<recipe_id>") # must come last, or it will steal earlier patterns
@cache.cached(key_prefix=util.make_cache_key, unless=util.skip_cache_p)
def show_data(recipe_id=None, format="html", stub=None):
    """Show full result dataset in HTML, CSV, or JSON (as requested)."""

    def get_result ():
        """Closure to generate the output."""

        # Set up the data source from the recipe
        recipe = util.get_recipe(recipe_id, auth=False)
        if not recipe or not recipe['args'].get('url'):
            return flask.redirect('/data/source', 303)

        # Use caching if requested
        if util.skip_cache_p():
            source = filters.setup_filters(recipe)
        else:
            with requests_cache.enabled(
                    app.config.get('REQUEST_CACHE', '/tmp/hxl_proxy_requests'), 
                    expire_after=app.config.get('REQUEST_CACHE_TIMEOUT_SECONDS', 3600)
            ):
                source = filters.setup_filters(recipe)

        # Output parameters
        show_headers = (recipe['args'].get('strip-headers') != 'on')
        max_rows = recipe['args'].get('max-rows', None)

        # Return a generator based on the format requested
        if format == 'html':
            max_rows = min(int(max_rows), 5000) if max_rows is not None else 5000
            return flask.render_template('data-view.html', source=preview.PreviewFilter(source, max_rows=max_rows), recipe=recipe, show_headers=show_headers)

        # Data formats from here on ...

        if max_rows is not None:
            source = preview.PreviewFilter(source, max_rows=int(max_rows))
            
        if format == 'json':
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

    # Get the result and update the cache manually if we're skipping caching.
    result = get_result()
    if util.skip_cache_p():
        cache.set(show_data.make_cache_key(), result)
    return result

@app.route("/hxl-test.<format>")
@app.route("/hxl-test")
def show_test(format='html'):
    """Test if a URL points to HXL-tagged data.
    @param format: the format for rendering the result.
    """

    url = flask.request.args.get('url')
    
    if not url and (format != 'html'):
        raise ValueError("&url parameter required")

    result = {
        'status': False,
        'url': url
    }

    def record_exception(e):
        result['exception'] = e.__class__.__name__
        result['args'] = [str(arg) for arg in e.args]

    if url:
        try:
            hxl.data(url, verify_ssl=util.check_verify_ssl(flask.request.args)).columns
            result['status'] = True
            result['message'] = 'Dataset has HXL hashtags'
        except IOError as e1:
            result['message'] = 'Cannot load dataset'
            record_exception(e1)
        except hxl.io.HXLTagsNotFoundException as e2:
            result['message'] = 'Dataset does not have HXL hashtags'
            record_exception(e2)
        except BaseException as e3:
            result['message'] = 'Undefined error'
            record_exception(e3)
    else:
        result = None

    if format == 'json':
        return flask.Response(json.dumps(result), mimetype='application/json')
    else:
        return flask.render_template('hxl-test.html', result=result)


@app.route('/settings/user')
def do_user_settings():
    """Show the user settings page (if authorised)."""
    if flask.g.member:
        return flask.render_template('settings-user.html', member=flask.g.member)
    else:
        # redirect back to the settings page after login
        return flask.redirect('/login?from=/settings/user', 303)


@app.route("/actions/login", methods=['POST'])
def do_data_login():
    """POST handler: authenticate for a specific recipe (will disappear soon)."""

    # Note origin page
    destination = flask.request.form.get('from')
    if not destination:
        destination = '/data'

    # Just save the password hash, but don't do anything with it
    password = flask.request.form.get('password')
    flask.session['passhash'] = util.make_md5(password)

    # Try opening the original page again, with auth token in the cookie.
    return flask.redirect(destination, 303)


@app.route("/actions/save-recipe", methods=['POST'])
def do_data_save():
    """POST handler: start a new saved recipe, or update an existing one."""

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


@app.route('/login')
def do_login():
    """Log the user using OAuth2 via the IdP (Humanitarian.ID), and set a cookie."""
    flask.session['login_redirect'] = flask.request.args.get('from', '/')
    return flask.redirect(auth.get_hid_login_url(), 303)


@app.route('/logout')
def do_logout():
    """Kill the login cookie (and any others)."""
    path = flask.request.args.get('from', '/') # original path where user choose to log out
    flask.session.clear()
    flask.flash("Disconnected from your Humanitarian.ID account (browsing anonymously).")
    return flask.redirect(path, 303)


@app.route('/oauth/authorized2/1')
def do_hid_authorisation():
    """Handle OAuth2 token sent back from IdP (Humanitarian.ID) after remote authentication."""

    # Check if we really sent the request, and save the auth token
    code = flask.request.args.get('code')
    state = flask.request.args.get('state')
    if state != flask.session.get('state'):
        raise Exception("Security violation: inconsistent state returned from humanitarian.id login request")
    else:
        flask.session['state'] = None

    # Look up extra info from Humanitarian.ID
    user_info = auth.get_hid_user(code) # look up user info from Humanitarian.ID
    flask.session['member_info'] = user_info
    flask.flash("Connected to your Humanitarian.ID account as {}".format(user_info.get('name')))

    # Try to bring the user back where s/he started.
    redirect_path = flask.session.get('login_redirect', '/')
    del flask.session['login_redirect']
    return flask.redirect(redirect_path, 303)

# end
