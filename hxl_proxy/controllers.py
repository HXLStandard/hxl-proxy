"""
HTTP controllers for the HXL Proxy
David Megginson
January 2015

License: Public Domain
Documentation: http://hxlstandard.org
"""

import flask, hxl, io, json, logging, requests, requests_cache, urllib, werkzeug, datetime

from io import StringIO

from . import app, auth, cache, dao, filters, preview, pcodes, util, exceptions, __version__

logger = logging.getLogger(__name__)


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

def handle_exception(e, format='html'):
    """Default error page."""
    if isinstance(e, IOError) or isinstance(e, OSError):
        # probably tried to open an inappropriate URL
        status = 403
    elif isinstance(e, werkzeug.exceptions.HTTPException):
        status = e.code
    elif isinstance(e, requests.exceptions.HTTPError):
        status = 404
    else:
        status = 500
    if flask.g.output_format != 'html':
        response = flask.Response(util.make_json_error(e, status), mimetype='application/json', status=status)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    else:
        return flask.render_template('error.html', e=e, category=type(e)), status        

if not app.config.get('DEBUG'):
    app.register_error_handler(Exception, handle_exception)


def handle_redirect_exception(e):
    """ Exception to force a redirect to a different page
    """
    if e.message:
        flask.flash(e.message)
    return flask.redirect(e.target_url, e.http_code)

app.register_error_handler(exceptions.RedirectException, handle_redirect_exception)


# Source dataset requires authorisation

def handle_authorization_exception(e):
    """ Exception when authorisation fails on the source resource
    """
    if e.message:
        flask.flash(e.message)
    recipe = util.get_recipe(recipe_id=flask.g.recipe_id)
    extras = {
        'need_token': 'on'
    }
    if e.is_ckan:
        extras['is_ckan'] = 'on'
    return flask.redirect(util.data_url_for('data_save', recipe=recipe, extras=extras), 302)

app.register_error_handler(hxl.io.HXLAuthorizationException, handle_authorization_exception)


#
# SSL errors
#
def handle_ssl_error(e):
    flask.flash("SSL error. If you understand the risks, you can check \"Don't verify SSL certificates\" to continue.")
    return flask.redirect(util.data_url_for('data_source', recipe=util.get_recipe()), 302)

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
    flask.g.output_format='html' # default format is HTML, unless a controller changes it


#
# Redirects for deprecated URL patterns
#

@app.route("/")
def home():
    # home isn't moved permanently
    # note: not using data_url_for because this is outside data pages
    return flask.redirect(flask.url_for("data_source", **flask.request.args) , 302)

#
# Primary controllers
#

@app.route("/about.html")
def about():
    # releases to list
    releases = {
        'hxl-proxy': __version__,
        'libhxl': hxl.__version__,
        'flask': flask.__version__,
        'requests': requests.__version__
    }
    return flask.render_template('about.html', releases=releases)

@app.route("/data/<recipe_id>/login")
def data_login(recipe_id):
    recipe = util.get_recipe(recipe_id)
    return flask.render_template('data-login.html', recipe=recipe)

@app.route("/data/source")
@app.route("/data/<recipe_id>/source")
def data_source(recipe_id=None):
    """Choose a new data source."""

    try:
        recipe = util.get_recipe(recipe_id, auth=True)
    except werkzeug.exceptions.Unauthorized as e:
        return flask.redirect(util.data_url_for('data_login', recipe_id=recipe_id), 303)

    return flask.render_template('data-source.html', recipe=recipe)


@app.route("/data/tagger")
@app.route("/data/<recipe_id>/tagger")
def data_tagger(recipe_id=None):
    """Add HXL tags to an untagged dataset."""

    flask.g.recipe_id = recipe_id

    try:
        recipe = util.get_recipe(recipe_id, auth=True)
    except werkzeug.exceptions.Unauthorized as e:
        return flask.redirect(util.data_url_for('data_login', recipe_id=recipe_id), 303)

    header_row = recipe['args'].get('header-row')
    if header_row is not None:
        header_row = int(header_row)

    if not recipe['args'].get('url'):
        flask.flash('Please choose a data source first.')
        return flask.redirect(util.data_url_for('data_source', recipe), 303)

    try:
        sheet_index = int(recipe['args'].get('sheet', 0))
    except:
        sheet_index = 0

    selector = recipe['args'].get('selector', None)

    preview = []
    i = 0
    http_headers = {
        'User-Agent': 'hxl-proxy/tagger'
    }
    if recipe['args'].get('authorization_token'):
        http_headers['Authorization'] = recipe['args']['authorization_token']
    for row in hxl.io.make_input(
            recipe['args'].get('url'),
            sheet_index=sheet_index,
            selector=selector,
            verify_ssl=util.check_verify_ssl(recipe['args']),
            http_headers=http_headers
    ):
        if i >= 25:
            break
        else:
            i = i + 1
        if row:
            preview.append(row)
        
    return flask.render_template('data-tagger.html', recipe=recipe, preview=preview, header_row=header_row)


@app.route("/data/edit")
@app.route("/data/<recipe_id>/edit", methods=['GET', 'POST'])
def data_edit(recipe_id=None):
    """Create or edit a filter pipeline."""

    flask.g.recipe_id = recipe_id

    try:
        recipe = util.get_recipe(recipe_id, auth=True)
    except werkzeug.exceptions.Unauthorized as e:
        return flask.redirect(util.data_url_for('data_login', recipe_id=recipe_id), 303)

    error = None
    if recipe['args'].get('url'):
        # show only a short preview
        max_rows = recipe['args'].get('max-rows', None)
        max_rows = min(int(max_rows), 25) if max_rows is not None else 25
        try:
            source = preview.PreviewFilter(filters.setup_filters(recipe), max_rows=max_rows)
            source.columns
        except exceptions.RedirectException as e1:
            raise e1
        except hxl.io.HXLAuthorizationException as e2:
            raise e2
        except Exception as e3:
            error = e3
            source = None
    else:
        flask.flash('Please choose a data source first.')
        return flask.redirect(util.data_url_for('data_source', recipe), 303)

    # Figure out how many filter forms to show
    filter_count = 0
    for n in range(1, filters.MAX_FILTER_COUNT):
        if recipe['args'].get('filter%02d' % n):
            filter_count = n
    if filter_count < filters.MAX_FILTER_COUNT:
        filter_count += 1

    show_headers = (recipe['args'].get('strip-headers') != 'on')

    return flask.render_template(
        'data-recipe.html',
        recipe=recipe,
        source=source,
        error=error,
        show_headers=show_headers,
        filter_count=filter_count
    )

@app.route("/data/save")
@app.route("/data/<recipe_id>/save")
def data_save(recipe_id=None):
    """Show form to save a recipe."""

    try:
        recipe = util.get_recipe(recipe_id, auth=True)
    except werkzeug.exceptions.Unauthorized as e:
        return flask.redirect(util.data_url_for('data_login', recipe_id=recipe_id), 303)

    need_token = flask.request.args.get('need_token')
    is_ckan = flask.request.args.get('is_ckan')

    if not recipe or not recipe['args'].get('url'):
        return flask.redirect(util.data_url_for('data_source', recipe), 303)

    return flask.render_template('data-save.html', recipe=recipe, need_token=need_token, is_ckan=is_ckan)


@app.route("/data/validate")
@app.route("/data/validate.<format>")
@app.route("/data/<recipe_id>/validate")
@app.route("/data/<recipe_id>/validate.<format>")
def data_validate(recipe_id=None, format='html'):
    """Run a validation and show the result in a dashboard."""

    flask.g.recipe_id = recipe_id

    # Save the data format
    flask.g.output_format = format

    # Get the recipe
    recipe = util.get_recipe(recipe_id)
    if not recipe or not recipe['args'].get('url'):
        return flask.redirect(util.data_url_for('data_source', recipe), 303)

    # Get the parameters
    schema_url = recipe['args'].get('schema_url', None)
    severity_level = recipe['args'].get('severity', 'info')
    detail_hash = recipe['args'].get('details', None)

    # set up the schema
    schema_source = None
    if schema_url:
        schema_source = hxl.data(
            schema_url,
            verify_ssl=util.check_verify_ssl(recipe['args']),
            http_headers={'User-Agent': 'hxl-proxy/validation'}
        )

    # run the validation
    error_report = hxl.validate(
        filters.setup_filters(recipe),
        schema_source
    )

    # return the results
    if format == 'json':
        return flask.Response(
            json.dumps(error_report, indent=4),
            mimetype="application/json"
        )
    else:
        # issue to highlight (HTML only)
        template_name = 'validate-summary.html'
        selected_issue = None
        if detail_hash:
            template_name = 'validate-issue.html'
            for issue in error_report['issues']:
                if issue['rule_id'] == detail_hash:
                    selected_issue = issue
                    break

        return flask.render_template(
            template_name,
            recipe=recipe,
            schema_url=schema_url,
            error_report=error_report,
            issue=selected_issue,
            severity=severity_level
        )

@app.route("/data/<recipe_id>/advanced")
@app.route("/data/advanced")
def show_advanced(recipe_id=None):
    """Advanced form for direct JSON entry."""
    flask.g.recipe_id = recipe_id
    recipe = util.get_recipe(recipe_id, auth=True)
    return flask.render_template("data-advanced.html", recipe=recipe)

@app.route("/data")
@app.route("/data.<flavour>.<format>")
@app.route("/data.<format>")
@app.route("/data/download/<stub>.<flavour>.<format>")
@app.route("/data/download/<stub>.<format>")
@app.route("/data/<recipe_id>.<flavour>.<format>")
@app.route("/data/<recipe_id>.<format>")
@app.route("/data/<recipe_id>/download/<stub>.<flavour>.<format>")
@app.route("/data/<recipe_id>/download/<stub>.<format>")
@app.route("/data/<recipe_id>") # must come last, or it will steal earlier patterns
@cache.cached(key_prefix=util.make_cache_key, unless=util.skip_cache_p)
def data_view(recipe_id=None, format="html", stub=None, flavour=None):
    """Show full result dataset in HTML, CSV, or JSON (as requested)."""

    flask.g.recipe_id = recipe_id

    def get_result ():
        """Closure to generate the output."""

        # Save the data format
        flask.g.output_format = format

        # Set up the data source from the recipe
        recipe = util.get_recipe(recipe_id, auth=False)
        if not recipe or not recipe['args'].get('url'):
            return flask.redirect(util.data_url_for('data_source', recipe), 303)

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
            return flask.render_template(
                'data-view.html',
                source=preview.PreviewFilter(source, max_rows=max_rows),
                recipe=recipe,
                show_headers=show_headers
            )

        # Data formats from here on ...

        if max_rows is not None:
            source = preview.PreviewFilter(source, max_rows=int(max_rows))
            
        if format == 'json':
            use_objects = False
            if flavour == 'objects':
                use_objects = True
            response = flask.Response(list(source.gen_json(show_headers=show_headers, use_objects=use_objects)), mimetype='application/json')
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
        cache.set(util.make_cache_key(), result)
    return result

@app.route('/settings/user')
def user_settings():
    """Show the user settings page (if authorised)."""
    if flask.g.member:
        return flask.render_template('settings-user.html', member=flask.g.member)
    else:
        # redirect back to the settings page after login
        # ('from' is reserved, so we need a bit of a workaround)
        args = { 'from': util.data_url_for('user_settings') }
        return flask.redirect(url_for('login', **args), 303)

@app.route('/actions/json-spec', methods=['POST'])
def do_json_recipe():
    """POST handler to execute a JSON recipe
    """

    recipe = flask.request.files.get('recipe', None)

    format = flask.request.form.get('format', 'csv')
    show_headers = False if flask.request.form.get('show_headers', None) is None else True
    use_objects = False if flask.request.form.get('use_objects', None) is None else True
    stub = flask.request.form.get('stub', 'data')

    flask.g.output_format = 'format'

    if recipe is None:
        raise werkzeug.exceptions.BadRequest("Parameter 'recipe' is required")

    spec = json.load(recipe.stream)

    source = hxl.io.from_spec(spec)

    if format == 'json':
        response = flask.Response(
            source.gen_json(show_headers=show_headers, use_objects=use_objects),
            mimetype='application/json'
        )
    else:
        response = flask.Response(
            source.gen_csv(show_headers=show_headers),
            mimetype='text/csv'
        )

    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Content-Disposition'] = 'attachment; filename={}.{}'.format(stub, format)

    return response

@app.route("/actions/validate", methods=['POST'])
def do_validate():
    """POST handler: validate a dataset against the provided schema, and return a JSON report
    This method does not apply filters, tagger, etc, but simply takes the following parameters:
    * url | content - the data to validate
    * schema_url | schema_content - the schema to use (optional)
    """

    # signal that the output will be JSON (for error reporting)
    flask.g.output_format = 'json'

    # get the POST params: url, content, sheet_index, selector, schema_url, schema_content, schema_sheet_index, include_dataset
    # (url or content is required)
    url = flask.request.form.get('url')
    content_hash = None
    content = flask.request.files.get('content')
    if content is not None:
        # need a hash of the content for caching
        content_hash = util.make_file_hash(content)
    sheet_index = flask.request.form.get('sheet', None)
    if sheet_index is not None:
        try:
            sheet_index = int(sheet_index)
        except:
            logger.warning("Bad sheet index: %s", flask.request.form.get('sheet'))
            sheet_index = None
    selector = flask.request.form.get('selector', None)
    schema_url = flask.request.form.get('schema_url')
    schema_content_hash = None
    schema_content = flask.request.files.get('schema_content')
    if schema_content is not None:
        # need a hash of the schema content for caching
        schema_content_hash = util.make_file_hash(schema_content)
    schema_sheet_index = flask.request.form.get('schema_sheet', None)
    if schema_sheet_index is not None:
        try:
            schema_sheet_index = int(schema_sheet_index)
        except:
            logger.warning("Bad schema_sheet index: %s", flask.request.form.get('schema_sheet'))
            schema_sheet_index = None
    include_dataset = flask.request.form.get('include_dataset', False)

    # run the validation and save a report
    # caching happens in the util.run_validation() function
    report = util.run_validation(
        url, content, content_hash, sheet_index, selector,
        schema_url, schema_content, schema_content_hash, schema_sheet_index,
        include_dataset
    )

    # return a JSON version of the validation report as an HTTP response
    # (make sure we have a CORS header)
    response = flask.Response(
        json.dumps(
            report,
            indent=4
        ),
        mimetype='application/json'
    )
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

    
@app.route("/actions/login", methods=['POST'])
def do_data_login():
    """POST handler: authenticate for a specific recipe (will disappear soon)."""

    # Note origin page
    destination = flask.request.form.get('from')
    if not destination:
        destination = util.data_url_for('data_view')

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
    except werkzeug.exceptions.Unauthorized as e:
        return flask.redirect(util.data_url_for('data_login', recipe_id=recipe_id), 303)

    # Update recipe metadata
    if 'name' in flask.request.form:
        recipe['name'] = flask.request.form['name']
    if 'description' in flask.request.form:
        recipe['description'] = flask.request.form['description']
    if 'cloneable' in flask.request.form and not 'authorization_token' in flask.request.form:
        recipe['cloneable'] = (flask.request.form['cloneable'] == 'on')
    else:
        recipe['cloneable'] = False
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

    return flask.redirect(util.data_url_for('data_view', recipe), 303)


@app.route('/login')
def hid_login():
    """Log the user using OAuth2 via the IdP (Humanitarian.ID), and set a cookie."""
    flask.session['login_redirect'] = flask.request.args.get('from', '/')
    return flask.redirect(auth.get_hid_login_url(), 303)


@app.route('/logout')
def hid_logout():
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


########################################################################
# Extra stuff tacked onto the Proxy
#
# None of this is core to the Proxy's function, but this is a convenient
# place to keep it.
########################################################################

@app.route("/hxl-test.<format>")
@app.route("/hxl-test")
def hxl_test(format='html'):
    """Test if a URL points to HXL-tagged data.
    @param format: the format for rendering the result.
    """

    # Save the data format
    flask.g.output_format = format

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
            hxl.data(
                url,
                verify_ssl=util.check_verify_ssl(flask.request.args),
                http_headers={'User-Agent': 'hxl-proxy/test'}
            ).columns
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


@app.route('/pcodes/<country>-<level>.csv')
@cache.cached(timeout=604800) # 1 week cache
def pcodes_get(country, level):
    flask.g.output_format = 'csv'
    with StringIO() as buffer:
        pcodes.extract_pcodes(country, level, buffer)
        response = flask.Response(buffer.getvalue(), mimetype='text/csv')
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

@app.route('/hash')
def make_hash():
    flask.g.output_format = 'json'
    url = flask.request.args.get('url')
    if not url:
        return flask.render_template('hash.html')
    headers_only = flask.request.args.get('headers_only')
    source = hxl.data(url)
    report = {
        'hash': source.columns_hash if headers_only else source.data_hash,
        'url': url,
        'date': datetime.datetime.utcnow().isoformat(),
        'headers_only': True if headers_only else False,
        'headers': source.headers,
        'hashtags': source.display_tags
    }
    return flask.Response(
        json.dumps(report, indent=4),
        mimetype="application/json"
    )


@app.route('/iati2hxl')
def iati_get():
    import re

    flask.g.output_format = 'csv'
    url = flask.request.args.get('url')
    if not url:
        return flask.render_template('iati2hxl.html')

    # can we pull a filename from the URL?
    filename = 'iati-data.xml'
    result = re.match(r'.*/([^/?]+)\.[xX][mM][lL]', url)
    if result:
        filename = result.group(1) + '.csv'

    response = flask.Response(util.gen_iati_hxl(url), mimetype='text/csv; charset=utf-8')
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Content-Disposition'] = 'attachment; filename={}'.format(filename)
    return response


########################################################################
# Removed features (display messages)
########################################################################

@app.route('/data/<recipe_id>/chart')
@app.route('/data/chart')
def data_chart(recipe_id=None):
    return "The HXL Proxy no longer supports basic charts. Please visit <a href='https://tools.humdata.org/'>tools.humdata.org</a>", 410

@app.route('/data/<recipe_id>/map')
@app.route('/data/map')
def data_map(recipe_id=None):
    """Show a map visualisation for the data."""
    return "The HXL Proxy no longer supports basic maps. Please visit <a href='https://tools.humdata.org/'>tools.humdata.org</a>", 410

# end
