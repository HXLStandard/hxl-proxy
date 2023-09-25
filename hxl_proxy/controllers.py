""" HTTP controllers for the HXL Proxy

All of the Flask controllers are in this module.

See unit tests in tests/test_controllers.py

Started January 2015 by David Megginson
License: Public Domain
"""

import hxl_proxy
from hxl.input import HXLIOException

from hxl_proxy import app, cache, caching, exceptions, filters, pcodes, preview, recipes, util, validate

import datetime, flask, hxl, importlib, io, json, logging, requests, requests_cache, signal, werkzeug, csv, urllib

from hxl.util import logup

logger = logging.getLogger(__name__)
""" Python logger for this module """

from structlog import contextvars, get_logger, wrap_logger
input_logger = wrap_logger(logging.getLogger('hxl.REMOTE_ACCESS'))

SHEET_MAX_NO = 20


########################################################################
# Asynchronous signal handlers
########################################################################

def handle_alarm_signal(signum, frame):
    """ Raise a TimeoutError when there's an alarm """
    logging.warning("Request timed out")
    logup('Request timed out', level='info')
    raise TimeoutError()

# signal.signal(signal.SIGALRM, handle_alarm_signal) # temporarily deactivated



########################################################################
# Error handlers
#
# These functions handle exceptions that make it to the top level, as
# well as a timeout.
#
# The HXL Proxy uses exceptions for special purposes like redirections
########################################################################

def handle_default_exception(e):
    """ Error handler: display an error page with various HTTP status codes
    This handler applies to any exception that doesn't have a more-specific
    handler below.
    @param e: the exception being handled
    """

    key_error = {'error_type': type(e).__name__}
    # log a warning for the error/exception that we're handling
    if hasattr(e, 'message'):
        key_error['message'] = e.message
        logger.warning('%s: %s', type(e).__name__, e.message)
    else:
        logger.warning(type(e).__name__)
    logup('Error', key_error, "warning")


    if isinstance(e, requests.exceptions.HTTPError) or isinstance(e, hxl.input.HXLHTMLException):
        status = 404
        e = exceptions.RemoteDataException(e)
    elif isinstance(e, TimeoutError): # more specific than the following
        status = 408 # HTTP timeout
    elif isinstance(e, IOError) or isinstance(e, OSError):
        # probably tried to open an inappropriate URL
        status = 403
    elif isinstance(e, werkzeug.exceptions.HTTPException):
        status = e.code
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
if not app.debug:
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

    # set the timeout for the request
    try:
        timeout = int(app.config.get('TIMEOUT', 30))
    except ValueError:
        timeout = 30
    # signal.alarm(timeout) # temporarily deactivated
    



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
        'hxl_proxy': hxl_proxy.__version__,
    }
    for package in ['libhxl', 'flask', 'flask-caching', 'redis', 'requests', 'requests_cache', 'structlog', 'urllib3',]:
        try:
            releases[package] = importlib.metadata.version(package)
        except Exception as e:
            releases[package] = str(e)

    # draw the web page
    return flask.render_template('about.html', releases=releases)



########################################################################
# /data GET controllers
########################################################################

# has tests
@app.route("/data/source")
@util.structlogged
def data_source():
    """ Flask controller: choose a new source URL """
    recipe = recipes.Recipe()
    return flask.render_template('data-source.html', recipe=recipe)

# has tests
@app.route("/data/tagger")
@util.structlogged
def data_tagger():
    """ Flask controller: add HXL tags to an untagged dataset
    The template will render differently depending on whether the user has selected the
    last row of text headers yet (&header_row), so this is actually two different workflow
    steps.

    """

    # Build the recipe from the GET params and/or the database
    recipe = recipes.Recipe()

    # Workflow: if there's no source URL, redirect the user to /data/source
    if not recipe.url:
        logup('No URL supplied for /data/tagger; redirecting to /data/source', level='info')
        logger.info("No URL supplied for /data/tagger; redirecting to /data/source")
        flask.flash('Please choose a data source first.')
        return flask.redirect(util.data_url_for('data_source', recipe), 303)

    # We have to collect the following properties manually, because we don't have a complete
    # HXLated recipe to open yet
    header_row = recipe.args.get('header-row')
    if header_row is not None:
        header_row = int(header_row)

    # Set up a 25-row raw-data preview, using make_input from libhxl-python
    preview = []
    i = 0
    for row in util.hxl_make_input(recipe.url, util.make_input_options(recipe.args)):
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
@util.structlogged
def data_edit():
    """Flask controller: create or edit a filter pipeline.
    Output for this page is never cached, but input may be.

    """

    # Build the recipe from the GET params and/or the database
    recipe = recipes.Recipe()

    # Workflow: if there's no source URL, redirect the user to /data/source
    if not recipe.url:
        flask.flash('Please choose a data source first.')
        logup('No URL supplied for /data/edit; redirecting to /data/source', level="info")
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
    except (
            requests.RequestException,
            exceptions.RedirectException,
            hxl.input.HXLHTMLException
    ) as e1:
        # always pass through these exceptions
        raise e1
    except Exception as e2:
        # logger.exception(e2)
        error = e2
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
@app.route("/data/validate")
@app.route("/data/validate.<format>")
@util.structlogged
def data_validate(format='html'):
    """ Flask controller: validate a HXL dataset and show the results
    Output options include a web-based HTML dashboard or JSON.
    Output for this page is never cached, but input may be.
    @param format: the selected output format (json or html)

    """

    # Set global variables
    flask.g.output_format = format # requested output format

    # Get the recipe
    recipe = recipes.Recipe()

    # Workflow: if there's no source URL, redirect the user to /data/source
    if not recipe.url:
        flask.flash('Please choose a data source first.')
        logup('No URL supplied for /data/validate; redirecting to /data/source', level="info")
        logger.info("No URL supplied for /data/validate; redirecting to /data/source")
        return flask.redirect(util.data_url_for('data_source', recipe), 303)

    # Set up the HXL validation schema
    schema_source = None
    if recipe.schema_url:
        schema_source = util.hxl_data(recipe.schema_url, util.make_input_options(recipe.args))
        logup('Using HXL validation schema', {"schema": recipe.schema_url}, level="info")
        logger.info("Using HXL validation schema at %s", recipe.schema_url)
    else:
        logup('No HXL validation schema specified; using default schema', level="info")
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
            logup('Showing validation-report detail', level="info")
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
@util.structlogged
def show_advanced():
    """ Flask controller: developer page for entering a JSON recipe directly
    This page isn't linked from the HXML Proxy validation, but it's a convenient
    place to experiment with creating JSON-encoded recipes, as described at
    https://github.com/HXLStandard/hxl-proxy/wiki/JSON-recipes
    """
    recipe = recipes.Recipe()
    return flask.render_template("data-advanced.html", recipe=recipe)


# no tests
@app.route("/data/logs")
@util.structlogged
def data_logs():
    """ Flask controller: show logs for a recipe
    """
    level = flask.request.args.get('level', 'WARNING').upper()
    recipe = recipes.Recipe()
    return flask.render_template("data-logs.html", recipe=recipe, level=level, in_logger=True)


# has tests
@app.route("/data")
@app.route("/data.<flavour>.<format>")
@app.route("/data.<format>")
@app.route("/data/download/<stub>.<flavour>.<format>")
@app.route("/data/download/<stub>.<format>")
@cache.cached(key_prefix=util.make_cache_key, unless=util.skip_cache_p)
@util.structlogged
def data_view(format="html", stub=None, flavour=None):
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

    @param format: the selected output format (json or html)
    @param stub: the root filename for download, if supplied
    @param flavour: the JSON flavour, if supplied (will be "objects")

    """


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
        recipe = recipes.Recipe()

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
@util.structlogged
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


# has tests
@app.route("/actions/validate", methods=['POST'])
@util.structlogged
def do_data_validate():
    """ Flask controller: validate an uploaded file against an uploaded HXL schema
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
            logup('Bad sheet index', {"sheet": flask.request.form.get('sheet')}, level='warning')
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
            logup('Bad schema_sheet index', {"sheet": flask.request.form.get('schema_sheet')}, level='warning')
            logger.warning("Bad schema_sheet index: %s", flask.request.form.get('schema_sheet'))
            schema_sheet_index = None

    # general POST parameters
    include_dataset = flask.request.form.get('include_dataset', False)

    # run the validation and save a report
    # caching happens in the util.run_validation() function
    report = validate.run_validation(
        url, content, content_hash, sheet_index, selector,
        schema_url, schema_content, schema_content_hash, schema_sheet_index,
        include_dataset, flask.request.form
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
@util.structlogged
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
    source = hxl.input.from_spec(json_recipe)

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
# Controllers for extra API calls
#
# Migrating to /api (gradually)
#
# None of this is core to the Proxy's function, but this is a convenient
# place to keep it.
########################################################################

@app.route("/api/from-spec.<format>")
@util.structlogged
def from_spec(format="json"):
    """ Use a JSON HXL spec
    Not cached
    """

    # allow format override
    if format != "html":
        format = flask.request.args.get("format", format)
        flask.g.output_format = format

    # other args
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
            filename=filename,
            force=force,
        )
    elif spec_url and spec_json:
        raise ValueError("Must specify only one of &spec-url or &spec-json")
    elif spec_url:
        spec_response = requests.get(spec_url, headers=http_headers)
        spec_response.raise_for_status()
        spec = spec_response.json()
    elif spec_json:
        spec = json.loads(spec_json)
    else:
        raise ValueError("Either &spec-url or &spec-json required")

    # process the JSON spec
    source = hxl.input.from_spec(spec)

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
@util.structlogged
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
            util.hxl_data(url, util.make_input_options(flask.request.args)).columns
            # if we get to here, it's OK
            result['status'] = True
            result['message'] = 'Dataset has HXL hashtags'
        except IOError as e1:
            # can't open resource to check it
            result['message'] = 'Cannot load dataset'
            record_exception(e1)
        except hxl.input.HXLTagsNotFoundException as e2:
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
@util.structlogged
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

    rows = flask.request.args.get('rows', 0)
    rows = int(rows)

    filename = flask.request.args.get('filename')

    if format == "html":
        return flask.render_template('api-data-preview.html', url=url, args=flask.request.args)

    # if there's no URL, then show an interactive form
    if not url:
        return flask.redirect('/api/data-preview.html', 302)

    # make input
    if util.skip_cache_p():
        input = util.hxl_make_input(url, util.make_input_options(flask.request.args))
    else:
        with caching.input():
            input = util.hxl_make_input(url, util.make_input_options(flask.request.args))

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
@util.structlogged
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

    args = dict(flask.request.args)

    try:
        for sheet in range(0, SHEET_MAX_NO):
            args['sheet'] = sheet
            if util.skip_cache_p():
                input = util.hxl_make_input(url, util.make_input_options(args))
            else:
                with caching.input():
                    input = util.hxl_make_input(url, util.make_input_options(args))
            if isinstance(input, hxl.input.CSVInput):
                _output.append("Default")
                break
            else:
                if input._sheet and input._sheet.name:
                    _output.append(input._sheet.name)
                else:
                    _output.append(str(sheet))

    except HXLIOException as ex:
        logup("Found the last sheet of the Excel file", level='debug')
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
@util.structlogged
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
@util.structlogged
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
    source = util.hxl_data(url, util.make_input_options(flask.request.args))

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


# has tests
@app.route('/api/source-info')
@util.structlogged
def make_info():
    """ Flask controller: get info for an Excel dataset
    GET parameters:
    url - the URL of the dataset to check
    """
    flask.g.output_format = 'json' # for error reporting

    url = flask.request.args.get('url')
    if not url:
        raise ValueError("Parameter 'url' is required")

    # Open the dataset (not necessarily hxlated)
    info = hxl.input.info(util.hxl_make_input(url, util.make_input_options(flask.request.args)))
    return flask.Response(
        json.dumps(info, indent=4),
        mimetype="application/json"
    )


########################################################################
# Controllers for removed features (display error messages)
########################################################################


# needs tests
@app.route("/")
@util.structlogged
def home():
    """ Flask controller: nothing currently at root
    Redirect to the /data/source page
    """
    # home isn't moved permanently
    return flask.redirect(flask.url_for("data_source", **flask.request.args) , 302)


# end
