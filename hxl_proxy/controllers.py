""" HTTP controllers for the HXL Proxy

All of the Flask controllers are in this module.

See unit tests in tests/test_controllers.py

Started January 2015 by David Megginson
License: Public Domain
"""

import hxl_proxy
from hxl.io import HXLIOException

from hxl_proxy import admin, app, auth, cache, caching, dao, exceptions, filters, pcodes, preview, recipes, util, validate

import datetime, flask, hxl, io, json, logging, requests, requests_cache, werkzeug, csv, urllib


logger = logging.getLogger(__name__)
""" Python logger for this module """

SHEET_MAX_NO = 20


########################################################################
# Error handlers
#
# These functions handle exceptions that make it to the top level.
#
# The HXL Proxy uses exceptions for special purposes like redirections
# or authorisation as well as errors.
########################################################################

def handle_default_exception(e):
    """ Error handler: display an error page with various HTTP status codes
    This handler applies to any exception that doesn't have a more-specific
    handler below.
    @param e: the exception being handled
    """
    if isinstance(e, IOError) or isinstance(e, OSError):
        # probably tried to open an inappropriate URL
        status = 403
    elif isinstance(e, werkzeug.exceptions.HTTPException):
        status = e.code
    elif isinstance(e, requests.exceptions.HTTPError):
        status = 404
    else:
        status = 500

    # Check the global output_format variable to see if it's HTML or JSON/CSV
    # Use a JSON error format if not HTML
    if flask.g.output_format != 'html':
        response = flask.Response(util.make_json_error(e, status), mimetype='application/json', status=status)
        # add CORS header
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    else:
        # Generic HTML error page
        return flask.render_template('error.html', e=e, category=type(e)), status        

# Register the general error handler UNLESS we're in debug mode
if not app.config.get('DEBUG'):
    app.register_error_handler(Exception, handle_default_exception)


def handle_redirect_exception(e):
    """ Error handler: catch a redirection exception
    Different parts of the code throw exceptions.RedirectException
    when they need the HXL Proxy to jump to a different page. This is especially
    important for workflow (e.g. if there's no URL, jump to /data/source)
    @param e: the exception being handled
    """
    if e.message:
        flask.flash(e.message)
    return flask.redirect(e.target_url, e.http_code)

# Register the redirect exception handler
app.register_error_handler(exceptions.RedirectException, handle_redirect_exception)


def handle_source_authorization_exception(e):
    """ Error handler: the data source requires authorisation
    This will be triggered when opening a private HDX dataset before
    the user has supplied their authorisation token.
    @param e: the exception being handled
    """
    if e.message:
        flask.flash(e.message)

    # we're using flask.g.recipe_id to handle the case where a saved recipe
    # points to a formerly-public dataset that has suddenly become private
    # normally, it will be None (because there's no saved recipe yet)
    recipe = recipes.Recipe(recipe_id=flask.g.recipe_id)

    # add an extra parameter for the /data/save form to indicate that we
    # want the user to provide an authorisation token
    extras = {
        'need_token': 'on'
    }

    # note whether the resource looked like it came from HDX
    if e.is_ckan:
        extras['is_ckan'] = 'on'

    # redirect to the /data/save page to ask the user for a token
    return flask.redirect(util.data_url_for('data_save', recipe=recipe, extras=extras), 302)

# register the source authorisation handler
app.register_error_handler(hxl.io.HXLAuthorizationException, handle_source_authorization_exception)


def handle_password_required_exception(e):
    """ Error handler: the HXL Proxy saved recipe requires a password login
    Note that this handler triggers on a recipe basis, not a user basis; each
    each saved recipe can potentially have a different password.
    @param e: the exception being handled
    """
    flask.flash("Login required")
    if flask.g.recipe_id:
        destination = flask.request.path
        args = dict(flask.request.args)
        if args:
            destination += "?" + urllib.parse.urlencode(args)
        return flask.redirect(util.data_url_for('data_login', recipe_id=flask.g.recipe_id, extras={"from": destination}), 303)
    else:
        raise Exception("Internal error: login but no saved recipe")

# register the password required handler
app.register_error_handler(werkzeug.exceptions.Unauthorized, handle_password_required_exception)
    

def handle_ssl_certificate_error(e):
    """ Error handler: SSL certificate error
    Give the user an option to disable SSL certificate verification by redirecting to the /data/source page.
    @param e: the exception being handled
    """
    if flask.g.output_format == "html":
        flask.flash("SSL error. If you understand the risks, you can check \"Don't verify SSL certificates\" to continue.")
        return flask.redirect(util.data_url_for('data_source', recipe=recipes.Recipe()), 302)
    else:
        response = flask.Response(util.make_json_error(e, 400), mimetype='application/json', status=400)
        # add CORS header
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response

# register the SSL certificate verification handler
app.register_error_handler(requests.exceptions.SSLError, handle_ssl_certificate_error)



########################################################################
# Global pre-/post-controller functions
########################################################################

@app.before_request
def before_request():
    """Code to run immediately before the request"""

    # grab the secret key
    app.secret_key = app.config['SECRET_KEY']

    # choose the parameter storage class before parsing the GET parameters
    flask.request.parameter_storage_class = werkzeug.datastructures.ImmutableOrderedMultiDict

    # grab the member error for Humanitarian.ID (not currently used)
    flask.g.member = flask.session.get('member_info')

    # select the default output format (controllers may change it)
    flask.g.output_format='html'



########################################################################
# Top-level page controllers
########################################################################

# has tests
@app.route("/about.html")
def about():
    """ Flask controller: show the about page
    Includes version information for major packages, so that
    we can tell easily what's deployed.
    """
    # include version information for these packages
    releases = {
        'hxl-proxy': hxl_proxy.__version__,
        'libhxl': hxl.__version__,
        'flask': flask.__version__,
        'requests': requests.__version__
    }

    # draw the web page
    return flask.render_template('about.html', releases=releases)



########################################################################
# /data GET controllers
########################################################################

# has tests
@app.route("/data/<recipe_id>/login")
def data_login(recipe_id):
    """ Flask controller: log in to work on a saved recipe
    The user will end up here only if they tried to alter a saved
    recipe. They will have to enter the recipe's password to
    continue.
    @param recipe_id: the hash for a saved recipe (or None if working from the command line)
    """
    flask.g.recipe_id = recipe_id # for error handling
    recipe = recipes.Recipe(recipe_id)
    destination = flask.request.args.get('from')
    if not destination:
        destination = util.data_url_for('data_edit', recipe)
    return flask.render_template('data-login.html', recipe=recipe, destination=destination)

# has tests
@app.route("/data/source")
@app.route("/data/<recipe_id>/source")
def data_source(recipe_id=None):
    """ Flask controller: choose a new source URL
    @param recipe_id: the hash for a saved recipe (or None if working from the command line)
    """
    flask.g.recipe_id = recipe_id # for error handling
    recipe = recipes.Recipe(recipe_id, auth=True)
    return flask.render_template('data-source.html', recipe=recipe)

# has tests
@app.route("/data/tagger")
@app.route("/data/<recipe_id>/tagger")
def data_tagger(recipe_id=None):
    """ Flask controller: add HXL tags to an untagged dataset
    The template will render differently depending on whether the user has selected the 
    last row of text headers yet (&header_row), so this is actually two different workflow
    steps.
    @param recipe_id: the hash for a saved recipe (or None if working from the command line)
    """
    flask.g.recipe_id = recipe_id # for error handling

    # Build the recipe from the GET params and/or the database
    recipe = recipes.Recipe(recipe_id, auth=True)

    # Workflow: if there's no source URL, redirect the user to /data/source
    if not recipe.url:
        logger.info("No URL supplied for /data/tagger; redirecting to /data/source")
        flask.flash('Please choose a data source first.')
        return flask.redirect(util.data_url_for('data_source', recipe), 303)

    # We have to collect the following properties manually, because we don't have a complete
    # HXLated recipe to open yet
    header_row = recipe.args.get('header-row')
    if header_row is not None:
        header_row = int(header_row)
        
    try:
        sheet_index = int(recipe.args.get('sheet', 0))
    except:
        logger.info("Assuming sheet 0, since none specified")
        sheet_index = 0

    selector = recipe.args.get('selector', None)

    # Set up a 25-row raw-data preview, using make_input from libhxl-python
    preview = []
    i = 0
    http_headers = {
        'User-Agent': 'hxl-proxy/tagger'
    }
    if 'authorization_token' in recipe.args: # private dataset
        http_headers['Authorization'] = recipe.args['authorization_token']
    for row in hxl.io.make_input(
            recipe.url,
            sheet_index=sheet_index,
            selector=selector,
            verify_ssl=util.check_verify_ssl(recipe.args),
            http_headers=http_headers
    ):
        # Stop if we get to 25 rows
        if i >= 25:
            break
        else:
            i = i + 1
        if row:
            preview.append(row)

    if header_row is not None:
        mappings = util.clean_tagger_mappings(preview[header_row-1], recipe)
        mappings += [["", ""]] # room for an extra header in the form
    else:
        mappings = []

    # Draw the web page
    return flask.render_template('data-tagger.html', recipe=recipe, preview=preview, header_row=header_row, mappings=mappings)


# has tests
@app.route("/data/edit")
@app.route("/data/<recipe_id>/edit", methods=['GET', 'POST'])
def data_edit(recipe_id=None):
    """Flask controller: create or edit a filter pipeline.
    Output for this page is never cached, but input may be.
    @param recipe_id: the hash for a saved recipe (or None if working from the command line)
    """
    flask.g.recipe_id = recipe_id # for error handling

    # Build the recipe from the GET params and/or the database
    recipe = recipes.Recipe(recipe_id, auth=True)

    # Workflow: if there's no source URL, redirect the user to /data/source
    if not recipe.url:
        flask.flash('Please choose a data source first.')
        logger.info("No URL supplied for /data/edit; redirecting to /data/source")
        return flask.redirect(util.data_url_for('data_source', recipe), 303)
    
    # show only a short preview
    max_rows = recipe.args.get('max-rows')
    max_rows = min(int(max_rows), 25) if max_rows is not None else 25

    # check whether we're stripping headers
    show_headers = (recipe.args.get('strip-headers') != 'on')

    # Special handling: if the user has introduced an error in the filters,
    # catch it so that they have an opportunity to change the filters and try to
    # fix it.
    error = None
    try:
        source = preview.PreviewFilter(filters.setup_filters(recipe), max_rows=max_rows)
        source.columns
    except exceptions.RedirectException as e1:
        # always pass through a redirect exception
        raise e1
    except hxl.io.HXLAuthorizationException as e2:
        # always pass through an authorization exception
        raise e2
    except Exception as e3:
        logger.exception(e3)
        error = e3
        source = None

    # Figure out how many filter forms to show
    filter_count = 0
    for n in range(1, filters.MAX_FILTER_COUNT):
        if recipe.args.get('filter%02d' % n):
            filter_count = n
    if filter_count < filters.MAX_FILTER_COUNT:
        filter_count += 1

    # Draw the web page
    return flask.render_template(
        'data-recipe.html',
        recipe=recipe,
        source=source,
        error=error,
        show_headers=show_headers,
        filter_count=filter_count
    )


# has tests
@app.route("/data/save")
@app.route("/data/<recipe_id>/save")
def data_save(recipe_id=None):
    """ Flask controller: create or update a saved dataset (with a short URL)
    The user will get redirected here automatically if they attempt to open a private
    dataset on HDX (or anywhere else that requires an "Authorization:" HTTP header.
    The controller creates a form that submits the recipe information to be saved
    in the database and identified with a short hash.
    @param recipe_id: the hash for a saved recipe (or None if working from the command line)
    """
    flask.g.recipe_id = recipe_id # for error handling

    # Build the recipe from the GET params and/or the database
    recipe = recipes.Recipe(recipe_id, auth=True)

    # Workflow: if there's no source URL, redirect the user to /data/source
    if not recipe.url:
        flask.flash('Please choose a data source first.')
        logger.info("No URL supplied for /data/save; redirecting to /data/source")
        return flask.redirect(util.data_url_for('data_source', recipe), 303)

    # Grab controller-specific properties for the template
    need_token = flask.request.args.get('need_token') # we need an authentication token
    is_ckan = flask.request.args.get('is_ckan') # the source looks like CKAN

    # Draw the web page
    return flask.render_template('data-save.html', recipe=recipe, need_token=need_token, is_ckan=is_ckan)

# has tests
@app.route("/data/validate")
@app.route("/data/validate.<format>")
@app.route("/data/<recipe_id>/validate")
@app.route("/data/<recipe_id>/validate.<format>")
def data_validate(recipe_id=None, format='html'):
    """ Flask controller: validate a HXL dataset and show the results
    Output options include a web-based HTML dashboard or JSON.
    Output for this page is never cached, but input may be.
    @param recipe_id: the hash for a saved recipe (or None if working from the command line)
    @param format: the selected output format (json or html)
    """
    # Set global variables
    flask.g.recipe_id = recipe_id # for error handling
    flask.g.output_format = format # requested output format

    # Get the recipe
    recipe = recipes.Recipe(recipe_id)

    # Workflow: if there's no source URL, redirect the user to /data/source
    if not recipe.url:
        flask.flash('Please choose a data source first.')
        logger.info("No URL supplied for /data/validate; redirecting to /data/source")
        return flask.redirect(util.data_url_for('data_source', recipe), 303)

    # Set up the HXL validation schema
    schema_source = None
    if recipe.schema_url:
        schema_source = hxl.data(
            recipe.schema_url,
            verify_ssl=util.check_verify_ssl(recipe.args),
            http_headers={'User-Agent': 'hxl-proxy/validation'}
        )
        logger.info("Using HXL validation schema at %s", recipe.schema_url)
    else:
        logger.info("No HXL validation schema specified; using default schema")

    # Run the validation and get a JSON report from libhxl-python
    error_report = hxl.validate(
        filters.setup_filters(recipe),
        schema_source
    )

    # Render the validation results in JSON
    if format == 'json':
        return flask.Response(
            json.dumps(error_report, indent=4),
            mimetype="application/json"
        )

    # Render the validation results in HTML
    else:
        # issue to highlight (HTML only)
        template_name = 'validate-summary.html'
        selected_issue = None

        # Special GET parameters for controlling validation
        severity_level = flask.request.args.get('severity', 'info')
        detail_hash = flask.request.args.get('details', None)

        # if there's a detail_hash, show just that detail in the report
        if detail_hash:
            logger.info("Showing validation-report detail")
            template_name = 'validate-issue.html'
            for issue in error_report['issues']:
                if issue['rule_id'] == detail_hash:
                    selected_issue = issue
                    break

        # draw the web page
        return flask.render_template(
            template_name,
            recipe=recipe,
            schema_url=recipe.schema_url,
            error_report=error_report,
            issue=selected_issue,
            severity=severity_level
        )


# has tests
@app.route("/data/advanced")
@app.route("/data/<recipe_id>/advanced")
def show_advanced(recipe_id=None):
    """ Flask controller: developer page for entering a JSON recipe directly
    This page isn't linked from the HXML Proxy validation, but it's a convenient
    place to experiment with creating JSON-encoded recipes, as described at 
    https://github.com/HXLStandard/hxl-proxy/wiki/JSON-recipes
    """
    recipe = recipes.Recipe(recipe_id)
    return flask.render_template("data-advanced.html", recipe=recipe)


# no tests
@app.route("/data/logs")
@app.route("/data/<recipe_id>/logs")
def data_logs(recipe_id=None):
    """ Flask controller: show logs for a recipe
    """
    level = flask.request.args.get('level', 'WARNING').upper()
    recipe = recipes.Recipe(recipe_id)
    return flask.render_template("data-logs.html", recipe=recipe, level=level, in_logger=True)


# has tests
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
    """ Flask controller: render a transformed dataset
    This is the controller that requests will hit most of the time.
    It renders a transformed dataset as an HTML web page, a JSON
    list of lists, or a JSON list of objects, based on the URL, Note that
    the URL patterns above allow for custom-named download files
    as well as generic downloads, hence the wide variety of patterns.
    
    This controller MUST come after all the other /data controllers, or
    else Flask will get confused.

    This is a tricky controller to understand, for a few reasons:

    1. It can render output in several different formats
    2. It optionally caches the output
    3. It includes a CORS HTTP header
    4. Most of the work happens inside a nested function, to simplify caching
    5. It may specify a download file name, based on the stub property

    Grab a cup of tea, and work your way through the code slowly. :)

    @param recipe_id: the hash for a saved recipe (or None if working from the command line)
    @param format: the selected output format (json or html)
    @param stub: the root filename for download, if supplied
    @param flavour: the JSON flavour, if supplied (will be "objects")
    """
    flask.g.recipe_id = recipe_id # for error handling

    # Use an internal function to generate the output.
    # That simplifies the control flow, so that we can easily
    # capture the output regardless of chosen format, and
    # cache it as needed. Most of the controller's code
    # is inside this function.
    def get_result ():
        """ Internal output-generation function.
        @returns: a Python generator to produce the input incrementally
        """
        flask.g.output_format = format

        # Set up the data source from the recipe
        recipe = recipes.Recipe(recipe_id, auth=False)

        # Workflow: if there's no source URL, redirect the user to /data/source
        if not recipe.url:
            flask.flash('Please choose a data source first.')
            return flask.redirect(util.data_url_for('data_source', recipe), 303)

        # Use input caching if requested
        if util.skip_cache_p():
            source = filters.setup_filters(recipe)
        else:
            with caching.input():
                source = filters.setup_filters(recipe)

        # Parameters controlling the output
        show_headers = (recipe.args.get('strip-headers') != 'on')
        max_rows = recipe.args.get('max-rows', None)

        # Return a generator based on the format requested

        # Render a web page
        if format == 'html':
            # cap output at 5,000 rows for HTML
            max_rows = min(int(max_rows), 5000) if max_rows is not None else 5000
            return flask.render_template(
                'data-view.html',
                source=preview.PreviewFilter(source, max_rows=max_rows),
                recipe=recipe,
                show_headers=show_headers
            )

        # Data formats from here on ...

        # Limit the number of output rows *only* if requested
        if max_rows is not None:
            source = preview.PreviewFilter(source, max_rows=int(max_rows))

        # Render JSON output (list of lists or list of objects)
        if format == 'json':
            response = flask.Response(
                list(
                    source.gen_json(show_headers=show_headers, use_objects=(flavour=='objects'))
                ),
                mimetype='application/json'
            )

        # Render CSV output
        else:
            response = flask.Response(list(source.gen_csv(show_headers=show_headers)), mimetype='text/csv')

        # Include a CORS header for cross-origin data access
        response.headers['Access-Control-Allow-Origin'] = '*'

        # Set the file download name if &stub is present
        if recipe.stub:
            response.headers['Content-Disposition'] = 'attachment; filename={}.{}'.format(recipe.stub, format)

        # Return the response object
        return response

    # end of internal function
    
    # Get the result and update the cache manually if we're skipping caching.
    result = get_result()

    # Update the cache even if caching is turned off
    # (this might not be working yet)
    if util.skip_cache_p():
        cache.set(util.make_cache_key(), result)

    # return the response object that will render the output
    return result



#########################################################################
# Primary action POST controllers
# These are URLs that are not bookmarkable.
########################################################################

# needs tests
@app.route("/actions/login", methods=['POST'])
def do_data_login():
    """ Flask controller: log the user in for a specific dataset.
    Note that this is NOT a user login; it's a dataset login. That 
    means that the user will have to re-login if they start working
    on a dataset that has a different password.
    
    POST parameters:

    from - the origin URL (return there after login)
    password - the clear-text password
    """

    # Note origin page
    destination = flask.request.form.get('from')
    if not destination:
        destination = util.data_url_for('data_view')

    # Just save the password hash in a cookie, but don't do anything with it
    password = flask.request.form.get('password')
    flask.session['passhash'] = util.make_md5(password)

    # Try opening the original page again, with password hash token in the cookie.
    return flask.redirect(destination, 303)

# needs tests
@app.route("/actions/save-recipe", methods=['POST'])
def do_data_save():
    """ Flask controller: create or update a saved recipe
    The saved recipe has all of its parameters in the database, and is
    identified by a short hash. The user needs to supply a password
    to edit it.

    Post parameters:
    
    recipe_id - the short hash identifying the recipe (blank to create a new one)
    name - the recipe' title (optional)
    description - the recipe's long description (optional)
    cloneable - a flag indicating whether a user may clone the saved recipe (optional; defaults to "on")
    stub - a root filename for downloading (optional)
    password - a clear-text password (optional for a new saved recipe)
    password_repeat - repeated clear-text password (optional for a new saved recipe)

    (Will also include all of the other HXL Proxy recipe arguments as hidden parameters)
    """

    # FIXME - move somewhere else
    RECIPE_ARG_EXCLUDES = [
        'cloneable',
        'description',
        'dest',
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

    # We will have a recipe_id if we're updating an existing pipeline
    recipe_id = flask.request.form.get('recipe_id')
    flask.g.recipe_id = recipe_id # for error handling    
    recipe = recipes.Recipe(recipe_id, auth=True, request_args=flask.request.form)

    destination_facet = flask.request.form.get('dest', 'data_view')

    # Update recipe metadata
    # Note that an empty/unchecked value will be omitted from the form
    if 'name' in flask.request.form:
        recipe.name = flask.request.form['name']

    if 'description' in flask.request.form:
        recipe.description = flask.request.form['description']
    else:
        recipe.description = ''
        
    if 'cloneable' in flask.request.form and not flask.request.form.get('authorization_token') and flask.request.form['cloneable'] == "on":
        recipe.cloneable = True
    else:
        recipe.cloneable = False

    if 'stub' in flask.request.form:
        recipe.stub = flask.request.form['stub']
    else:
        recipe.stub = ''

    # Merge changed values
    recipe.args = {}
    for name in flask.request.form:
        if name not in RECIPE_ARG_EXCLUDES:
            recipe.args[name] = flask.request.form.get(name)

    # Check for a password change
    password = flask.request.form.get('password')
    password_repeat = flask.request.form.get('password-repeat')

    # Updating an existing recipe.
    if recipe_id:
        if password:
            if password == password_repeat:
                recipe.passhash = util.make_md5(password)
                flask.session['passhash'] = recipe.passhash
            else:
                raise werkzeug.exceptions.BadRequest("Passwords don't match")
        dao.recipes.update(recipe.toDict())

    # Creating a new recipe.
    else:
        if password == password_repeat:
            recipe.passhash = util.make_md5(password)
            flask.session['passhash'] = recipe.passhash
        else:
            raise werkzeug.exceptions.BadRequest("Passwords don't match")
        recipe_id = dao.make_recipe_id()
        recipe.recipe_id = recipe_id
        dao.recipes.create(recipe.toDict()) # FIXME move save functionality to Recipe class
        # FIXME other auth information is in __init__.py
        flask.session['passhash'] = recipe.passhash

    # Clear the entire HXL Proxy cache to avoid stale data (!!!)
    # TODO: be more targeted here
    cache.clear()

    # Redirect to the /data view page
    return flask.redirect(util.data_url_for(destination_facet, recipe), 303)

# has tests
@app.route("/actions/validate", methods=['POST'])
def do_data_validate():
    """ Flask controler: validate an uploaded file against an uploaded HXL schema
    This controller was created for HDX Data Check, which is the only known user.
    The controller returns a JSON validation report from libhxl-python.

    Post parameters:

    url - the URL of the data to validate (required unless "content" is specified)
    content - a file attachment with the HXL content (required unless "url" is specified)
    sheet_index - the 0-based index of the tab in a dataset Excel sheet
    selector - the top-level key for a JSON dataset

    schema_url - the URL of the HXL schema to use (optional; exclusive with "schema_content")
    schema_content - a file attachment with the HXL schema to use (optional; exclusive with "schema_url")
    schema_sheet_index - the 0-based index of the  tab in a schema Excel sheet

    include_dataset - if specified, include the original dataset in the JSON validation result
    """
    flask.g.output_format = 'json' # for error reporting

    # dataset-related POST parameters
    url = flask.request.form.get('url')
    content = flask.request.files.get('content')
    content_hash = None
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

    # schema-related POST parameters
    schema_url = flask.request.form.get('schema_url')
    schema_content = flask.request.files.get('schema_content')
    schema_content_hash = None
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

    # general POST parameters
    include_dataset = flask.request.form.get('include_dataset', False)

    # run the validation and save a report
    # caching happens in the util.run_validation() function
    report = validate.run_validation(
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

    # add the CORS header for cross-origin compatibility
    response.headers['Access-Control-Allow-Origin'] = '*'

    # render the JSON response
    return response


# needs tests
# NOTE: This is an experiment that's probably not used anywhere right now
# We may choose to remove it
@app.route('/actions/json-spec', methods=['POST'])
def do_json_recipe():
    """ POST handler to execute a JSON recipe
    This POST endpoint allows the user to upload a JSON HXL recipe
    and execute it. The endpoint does NOT currently allow uploading
    a file (but we should add that, to support private datasets).

    POST parameters:

    recipe - a file upload containing a JSON recipe
    format - "csv" or "json"
    show_headers - if specified, include text headers in the output
    use_objects - if specified, use JSON list of objects format
    stub - root filename for downloads

    Information on JSON recipes is available at
    https://github.com/HXLStandard/hxl-proxy/wiki/JSON-recipes
    """

    # Get the JSON recipe as a file attachment
    json_recipe_file = flask.request.files.get('recipe', None)
    if json_recipe_file is None:
        raise werkzeug.exceptions.BadRequest("Parameter 'recipe' is required")
    json_recipe = json.load(json_recipe_file.stream)

    # Other parameters
    format = flask.request.form.get('format', 'csv')
    show_headers = False if flask.request.form.get('show_headers', None) is None else True
    use_objects = False if flask.request.form.get('use_objects', None) is None else True
    stub = flask.request.form.get('stub', 'data')

    # Set global output format
    flask.g.output_format = 'format'

    # Create a HXL filter chain by parsing the JSON recipe
    source = hxl.io.from_spec(json_recipe)

    # Create a JSON or CSV response object, as requested
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

    # Add the CORS header for cross-origin compatibility
    response.headers['Access-Control-Allow-Origin'] = '*'

    # If a stub is specified, use it to define a download filename
    if stub:
        response.headers['Content-Disposition'] = 'attachment; filename={}.{}'.format(stub, format)

    # Render the output
    return response



########################################################################
# Humanitarian.ID controllers
# (not in active use as of 2019-04)
########################################################################

@app.route('/login')
def hid_login():
    """ Flask controller: display login page for Humanitarian.ID
    This is distinct from the /data/login page, which accepts a password
    for a DATASET rather than a USER.

    In the future, we can associate saved datasets with users, so they can
    manage them without individual dataset passwords.

    GET parameters:

    from - the URL of the page from which we were redirected
    """
    # set the from path in a session cookie for later use
    flask.session['login_redirect'] = flask.request.args.get('from', '/')

    # redirect to Humanitarian.ID for the actual login form
    return flask.redirect(auth.get_hid_login_url(), 303)


@app.route('/logout')
def hid_logout():
    """ Flask controller: kill the user's login session with Humanitarian.ID

    GET parameters:

    from - the URL of the page from which we were redirected
    """
    path = flask.request.args.get('from', '/') # original path where user choose to log out
    flask.session.clear() # clear the login cookie
    flask.flash("Disconnected from your Humanitarian.ID account (browsing anonymously).")
    return flask.redirect(path, 303)


# not currently in use (until we reactivate H.ID support)
@app.route('/settings/user')
def user_settings():
    """ Flask controller: show the user's settings from Humanitarian.ID
    """
    if flask.g.member:
        return flask.render_template('settings-user.html', member=flask.g.member)
    else:
        # redirect back to the settings page after login
        # ('from' is reserved, so we need a bit of a workaround)
        args = { 'from': util.data_url_for('user_settings') }
        return flask.redirect(url_for('login', **args), 303)


@app.route('/oauth/authorized2/1')
def do_hid_authorisation():
    """Flask controller: accept an OAuth2 token after successful login via Humanitarian.ID

    GET parameters:

    code - the OAuth2 token
    state - the state that we originally passed to Humanitarian.ID (for verification)
    """
    # grab the token
    code = flask.request.args.get('code')

    # grab the state and check if it's the same as the one we saved in a session cookie
    state = flask.request.args.get('state')
    if state != flask.session.get('state'):
        raise Exception("Security violation: inconsistent state returned from humanitarian.id login request")
    else:
        # if OK, clear the session cookie
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
# /admin controllers
########################################################################


# needs tests
@app.route("/admin/login")
def admin_login():
    """ Log in to use admin functions """
    return flask.render_template('admin-login.html')


# needs tests
@app.route("/admin/recipes/<recipe_id>/")
def admin_recipe_view(recipe_id):
    """ View a specific recipe """
    admin.admin_auth()
    recipe = recipes.Recipe(recipe_id, auth=False)
    if 'authorization_token' in recipe.args:
        clone_url = None
    else:
        clone_url = util.data_url_for('data_view', recipe, cloned=True)
    return flask.render_template('admin-recipe-view.html', recipe=recipe, clone_url=clone_url)


# needs tests
@app.route("/admin/recipes/<recipe_id>/edit.html")
def admin_recipe_edit(recipe_id):
    """ Edit a saved recipe """
    admin.admin_auth()
    recipe = recipes.Recipe(recipe_id, auth=False)
    args = json.dumps(recipe.args, indent=4)
    return flask.render_template('admin-recipe-edit.html', recipe=recipe, args=args)


# needs tests
@app.route("/admin/recipes/<recipe_id>/delete.html")
def admin_recipe_delete(recipe_id):
    """ Delete a saved recipe """
    admin.admin_auth()
    recipe = recipes.Recipe(recipe_id, auth=False)
    return flask.render_template('admin-recipe-delete.html', recipe=recipe)


# needs tests
@app.route("/admin/recipes/")
def admin_recipe_list():
    """ List all saved recipes """
    admin.admin_auth()
    recipes = admin.admin_get_recipes()
    return flask.render_template('admin-recipe-list.html', recipes=recipes)


# needs tests
@app.route("/admin/")
def admin_root():
    """ Root of admin pages """
    admin.admin_auth()
    return flask.render_template('admin-root.html')


# needs tests
@app.route("/admin/actions/login", methods=['POST'])
def do_admin_login():
    """ POST controller for an admin login """
    password = flask.request.form.get('password')
    admin.do_admin_login(password)
    flask.flash("Logged in as admin")
    return flask.redirect('/admin/', 303)


# needs tests
@app.route("/admin/actions/logout", methods=['POST'])
def do_admin_logout():
    """ POST controller for an admin logout """
    admin.admin_auth()
    admin.do_admin_logout()
    flask.flash("Logged out of admin functions")
    return flask.redirect('/data/source', 303)


# needs tests
@app.route("/admin/actions/update-recipe", methods=['POST'])
def do_admin_update_recipe():
    admin.admin_auth()
    recipe_id = flask.request.form.get('recipe_id')
    admin.do_admin_update_recipe(dict(flask.request.form))
    flask.flash("Updated recipe {}".format(recipe_id))
    return flask.redirect('/admin/recipes/{}/'.format(recipe_id), 303)


# needs tests
@app.route("/admin/actions/delete-recipe", methods=['POST'])
def do_admin_delete_recipe():
    admin.admin_auth()
    recipe_id = flask.request.form.get('recipe_id')
    admin.do_admin_delete_recipe(recipe_id)
    flask.flash("Deleted recipe {}".format(recipe_id))
    return flask.redirect('/admin/recipes/'.format(recipe_id), 303)



########################################################################
# Controllers for extra API calls
#
# Migrating to /api (gradually)
#
# None of this is core to the Proxy's function, but this is a convenient
# place to keep it.
########################################################################

@app.route("/api/from-spec.<format>")
def from_spec(format="json"):
    """ Use a JSON HXL spec 
    Not cached
    """

    # allow format override
    if format != "html":
        format = flask.request.args.get("format", format)
        flask.g.output_format = format

    # other args
    verify_ssl = util.check_verify_ssl(flask.request.args)
    http_headers = {
        'User-Agent': 'hxl-proxy/download'
    }
    filename = flask.request.args.get('filename')
    force = flask.request.args.get("force")

    # check arg logic
    spec_url = flask.request.args.get("spec-url")
    spec_json = flask.request.args.get("spec-json")
    spec = None

    if format == "html":
        return flask.render_template(
            'api-from-spec.html',
            spec_json=spec_json,
            spec_url=spec_url,
            verify_ssl=verify_ssl,
            filename=filename,
            force=force
        )
    elif spec_url and spec_json:
        raise ValueError("Must specify only one of &spec-url or &spec-json")
    elif spec_url:
        spec_response = requests.get(spec_url, verify=verify_ssl, headers=http_headers)
        spec_response.raise_for_status()
        spec = spec_response.json()
    elif spec_json:
        spec = json.loads(spec_json)
    else:
        raise ValueError("Either &spec-url or &spec-json required")

    # process the JSON spec
    source = hxl.io.from_spec(spec)

    # produce appropriate output
    if format == "json":
        response = flask.Response(
            source.gen_json(
                show_headers=spec.get("show_headers", True),
                show_tags=spec.get("show_tags", True),
                use_objects=False
            ),
            mimetype="application/json"
        )
    elif format == "objects.json":
        response = flask.Response(
            source.gen_json(
                show_headers=spec.get("show_headers", True),
                show_tags=spec.get("show_tags", True),
                use_objects=True
            ),
            mimetype="application/json"
        )
    elif format == "csv":
        response = flask.Response(
            source.gen_csv(
                show_headers=spec.get("show_headers", True),
                show_tags=spec.get("show_tags", True)
            ),
            mimetype="text/csv"
        )

    else:
        raise ValueError("Unsupported output format {}".format(format))

    # Add CORS header and return
    response.headers['Access-Control-Allow-Origin'] = '*'

    # Set the file download name if &filename is present
    if filename:
        response.headers['Content-Disposition'] = 'attachment; filename={}'.format(filename)

    return response
        
        

# needs tests
@app.route("/api/hxl-test.<format>")
@app.route("/api/hxl-test")
@app.route("/hxl-test.<format>") # legacy path
@app.route("/hxl-test") # legacy path
def hxl_test(format='html'):
    """ Flask controller: test if a resource is HXL hashtagged
    GET parameters:
    url - the URL of the resource th check
    @param format: the format for rendering the result.
    """
    flask.g.output_format = format # save the data format for error reporting

    # get the URL
    url = flask.request.args.get('url')
    if not url and (format != 'html'):
        # if it's a web page, show a form; otherwise, throw an error
        raise ValueError("&url parameter required")

    # start the result status report
    result = {
        'status': False,
        'url': url
    }

    # internal function: serialise an exception for inclusion in the report
    def record_exception(e):
        result['exception'] = e.__class__.__name__
        result['args'] = [str(arg) for arg in e.args]

    # if there's a URL, test the resource
    if url:
        try:
            # we grab the columns to force lazy parsing
            hxl.data(
                url,
                verify_ssl=util.check_verify_ssl(flask.request.args),
                http_headers={'User-Agent': 'hxl-proxy/test'}
            ).columns
            # if we get to here, it's OK
            result['status'] = True
            result['message'] = 'Dataset has HXL hashtags'
        except IOError as e1:
            # can't open resource to check it
            result['message'] = 'Cannot load dataset'
            record_exception(e1)
        except hxl.io.HXLTagsNotFoundException as e2:
            # not hashtagged
            result['message'] = 'Dataset does not have HXL hashtags'
            record_exception(e2)
        except BaseException as e3:
            # something else went wrong
            result['message'] = 'Undefined error'
            record_exception(e3)
    else:
        # no URL, so no result
        result = None

    if format == 'json':
        # render a JSON result
        return flask.Response(json.dumps(result), mimetype='application/json')
    else:
        # render an HTML page
        return flask.render_template('hxl-test.html', result=result)


# has tests
@app.route('/api/data-preview.<format>')
#@cache.cached(key_prefix=util.make_cache_key, unless=util.skip_cache_p) # can't cache generator output
def data_preview (format="json"):
    """ Return a raw-data preview of any data source supported by the HXL Proxy
    Does not attempt HXL processing.
    """

    def json_generator ():
        """ Generate JSON output, row by row """
        counter = 0
        yield '['
        for row in input:
            if rows > 0 and counter >= rows:
                break
            if counter == 0:
                line = "\n  "
            else:
                line = ",\n  "
            counter += 1
            line += json.dumps(row)
            yield line
        yield "\n]"

    def json_object_generator ():
        """ Generate JSON object-style output, row by row """
        counter = 0
        headers = None
        yield '['
        for row in input:
            if headers is None:
                headers = row
                continue
            if rows > 0 and counter >= rows:
                break
            if counter == 0:
                line = "\n  "
            else:
                line = ",\n  "
            counter += 1
            object = {}
            for i, header in enumerate(headers):
                if header and i < len(row):
                    object[header] = row[i]
            line += json.dumps(object)
            yield line
        yield "\n]"

    def csv_generator ():
        """ Generate CSV output, row by row """
        counter = 0
        for row in input:
            if rows > 0 and counter >= rows:
                break
            counter += 1
            output = io.StringIO()
            csv.writer(output).writerow(row)
            s = output.getvalue()
            output.close()
            yield s

    # allow overriding the format in a parameter (useful for forms)
    if "format" in flask.request.args and format != "html":
        format = flask.request.args.get("format")
    
    flask.g.output_format = format # for error reporting

    # params
    url = flask.request.args.get('url')

    sheet = flask.request.args.get('sheet')
    if sheet is not None:
        sheet = int(sheet)

    rows = flask.request.args.get('rows')
    if rows is not None:
        rows = int(rows)

    force = flask.request.args.get('force')

    filename = flask.request.args.get('filename')

    if format == "html":
        return flask.render_template('api-data-preview.html', url=url, sheet=sheet, rows=rows, filename=filename, force=force)

    # if there's no URL, then show an interactive form
    if not url:
        return flask.redirect('/api/data-preview.html', 302)

    # fix up params
    # if not sheet:
    #     sheet = -1
    #
    if not rows:
        rows = -1

    # make input
    if util.skip_cache_p():
        input = hxl.io.make_input(url, sheet_index=sheet)
    else:
        with caching.input():
            input = hxl.io.make_input(url, sheet_index=sheet)

    # Generate result
    if format == 'json':
        response = flask.Response(json_generator(), mimetype='application/json')
    elif format == 'objects.json':
        response = flask.Response(json_object_generator(), mimetype='application/json')
    elif format == 'csv':
        response = flask.Response(csv_generator(), mimetype='text/csv')
    else:
        raise ValueError("Unsupported &format {}".format(format))

    # Add CORS header and return
    response.headers['Access-Control-Allow-Origin'] = '*'

    # Set the file download name if &filename is present
    if filename:
        response.headers['Content-Disposition'] = 'attachment; filename={}'.format(filename)

    return response

# has no tests
@app.route('/api/data-preview-sheets.<format>')
# @cache.cached(key_prefix=util.make_cache_key, unless=util.skip_cache_p) # can't cache generator output
def data_preview_sheets(format="json"):
    """ Return names only for the sheets in an Excel workbook.
    In case of csv it returns one sheet name 'Default'
    You must use data_preview to get the actual sheet contents.
    """

    def json_generator():
        """ Generate JSON output, row by row """
        counter = 0
        yield '['
        for row in input:
            if rows > 0 and counter >= rows:
                break
            if counter == 0:
                line = "\n  "
            else:
                line = ",\n  "
            counter += 1
            line += json.dumps(row)
            yield line
        yield "\n]"

    def csv_generator():
        """ Generate CSV output, row by row """
        counter = 0
        for row in input:
            if rows > 0 and counter >= rows:
                break
            counter += 1
            output = io.StringIO()
            csv.writer(output).writerow([row])
            s = output.getvalue()
            output.close()
            yield s

    flask.g.output_format = format  # for error reporting

    # params
    url = flask.request.args.get('url')
    if not url:
        raise ValueError("&url parameter required")

    rows = -1

    # make input
    _output = []
    try:
        for sheet in range(0, SHEET_MAX_NO):
            if util.skip_cache_p():
                input = hxl.io.make_input(url, sheet_index=sheet)
            else:
                with caching.input():
                    input = hxl.io.make_input(url, sheet_index=sheet)
            if isinstance(input, hxl.io.CSVInput):
                _output.append("Default")
                break
            else:
                if input._sheet and input._sheet.name:
                    _output.append(input._sheet.name)
                else:
                    _output.append(str(sheet))

    except HXLIOException as ex:
        logger.debug("Found the last sheet of the Excel file")

    # Generate result
    input = _output
    if format == 'json':
        response = flask.Response(json_generator(), mimetype='application/json')
    elif format == 'csv':
        response = flask.Response(csv_generator(), mimetype='text/csv')
    else:
        raise ValueError("Unsupported &format {}".format(format))

    # Add CORS header and return
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response


# has tests
@app.route('/api/pcodes/<country>-<level>.csv')
@app.route('/pcodes/<country>-<level>.csv') # legacy path
@cache.cached(timeout=604800) # 1 week cache
def pcodes_get(country, level):
    """ Flask controller: look up a list of P-codes from iTOS
    @param country: the ISO3 country code
    @param level: the admin level (e.g. "adm2")
    """
    flask.g.output_format = 'csv' # for error reporting

    # Get the P-codes
    with io.StringIO() as buffer:
        pcodes.extract_pcodes(country, level, buffer)
        response = flask.Response(buffer.getvalue(), mimetype='text/csv')

    # Add a CORS header for cross-origin support
    response.headers['Access-Control-Allow-Origin'] = '*'

    # Render the result
    return response


# has tests
@app.route('/api/hash')
@app.route('/hash') # legacy path
def make_hash():
    """ Flask controller: hash a HXL dataset
    GET parameters:
    url - the URL of the dataset to check
    headers_only - if specified, hash only the headers, not the content
    """
    flask.g.output_format = 'json' # for error reporting

    # Get the URL; if not supplied, open an HTML form
    url = flask.request.args.get('url')
    if not url:
        return flask.render_template('hash.html')

    # Check if we're hashing only headers
    headers_only = flask.request.args.get('headers_only')

    # Open the HXL dataset
    source = hxl.data(url)

    # Generate the report
    report = {
        'hash': source.columns_hash if headers_only else source.data_hash,
        'url': url,
        'date': datetime.datetime.utcnow().isoformat(),
        'headers_only': True if headers_only else False,
        'headers': source.headers,
        'hashtags': source.display_tags
    }

    # Render the JSON response
    return flask.Response(
        json.dumps(report, indent=4),
        mimetype="application/json"
    )



########################################################################
# Controllers for removed features (display error messages)
########################################################################


# needs tests
@app.route("/")
def home():
    """ Flask controller: nothing currently at root
    Redirect to the /data/source page
    """
    # home isn't moved permanently
    return flask.redirect(flask.url_for("data_source", **flask.request.args) , 302)


# has tests
@app.route('/data/<recipe_id>/chart')
@app.route('/data/chart')
def data_chart(recipe_id=None):
    """ Flask controller: discontinued charting endpoint """
    return "The HXL Proxy no longer supports basic charts. Please visit <a href='https://tools.humdata.org/'>tools.humdata.org</a>", 410


# has tests
@app.route('/data/<recipe_id>/map')
@app.route('/data/map')
def data_map(recipe_id=None):
    """ Flask controller: discontinued mapping endpoint """
    return "The HXL Proxy no longer supports basic maps. Please visit <a href='https://tools.humdata.org/'>tools.humdata.org</a>", 410


# end
