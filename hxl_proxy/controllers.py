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

from werkzeug import secure_filename
from werkzeug.exceptions import BadRequest, Unauthorized, Forbidden, NotFound

from flask import Response, request, render_template, redirect, make_response, session, g

from hxl_proxy import app
from hxl_proxy.util import get_profile, check_auth, make_data_url
from hxl_proxy.filters import setup_filters
from hxl_proxy.validate import do_validate
from hxl_proxy.analysis import Analysis
from hxl_proxy.hdx import get_hdx_datasets
from hxl_proxy.preview import PreviewFilter

from hxl.model import TagPattern


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
    return render_template('error.html', message=str(e)), status

if not app.config.get('DEBUG'):
    # Register only if not in DEBUG mode
    app.register_error_handler(Exception, error)


#
# Redirects for deprecated URL patterns
#

@app.route("/")
def redirect_home():
    # home isn't moved permanently
    return redirect("/data?" + urllib.urlencode(request.args) , 302)

@app.route("/filters/new") # deprecated
def redirect_edit():
    return redirect("/data/edit?" + urllib.urlencode(request.args) , 301)

@app.route("/filters/preview") # deprecated
@app.route("/data/preview")
def redirect_data():
    return redirect("/data?" + urllib.urlencode(request.args) , 301)


#
# Primary controllers
#

@app.route("/data/<key>/login")
def show_data_login(key):
    profile = get_profile(key)
    return render_template('data-login.html', key=key, profile=profile)

@app.route("/data/upload")
def show_data_upload():
    """Form for uploading a HXL file."""
    profile = get_profile(None)
    return render_template('data-upload.html', profile=profile)

@app.route("/data/edit")
@app.route("/data/<key>/edit", methods=['GET', 'POST'])
def show_data_edit(key=None):
    """Create or edit a filter pipeline."""

    try:
        profile = get_profile(key, auth=True)
    except Forbidden as e:
        return redirect(make_data_url(None, key=key, facet='login'))

    source = None
    datasets = None
    if profile.args.get('url'):
        # show only a short preview
        source = PreviewFilter(setup_filters(profile), max_rows=5)

    show_headers = (profile.args.get('strip-headers') != 'on')

    return render_template('data-edit.html', key=key, profile=profile, source=source, show_headers=show_headers)

@app.route("/data/edit/hdx-datasets")
def show_data_hdx_datasets():
    "Show a picklist of HDX datasets."
    datasets = get_hdx_datasets()
    return render_template('data-edit-hdx-datasets.html', datasets=datasets)

@app.route("/data/save")
def show_data_save():
    """Show form to save a profile."""
    profile = get_profile(key=None)
    if not profile or not profile.args.get('url'):
        return redirect('/data/edit', 303)
    return render_template('data-save.html', profile=profile)

@app.route('/data/<key>/chart')
@app.route('/data/chart')
def show_data_chart(key=None):
    """Show a chart visualisation for the data."""
    profile = get_profile(key)
    if not profile or not profile.args.get('url'):
        return redirect('/data/edit', 303)
    tag = request.args.get('tag')
    if tag:
        tag = TagPattern.parse(tag);
    label = request.args.get('label')
    if label:
        label = TagPattern.parse(label);
    type = request.args.get('type', 'pie')
    return render_template('data-chart.html', key=key, profile=profile, tag=tag, label=label, filter=filter, type=type)

@app.route('/data/<key>/map')
@app.route('/data/map')
def show_data_map(key=None):
    """Show a map visualisation for the data."""
    profile = get_profile(key)
    if not profile or not profile.args.get('url'):
        return redirect('/data/edit', 303)
    layer_tag = TagPattern.parse(request.args.get('layer', 'adm1'))
    return render_template('data-map.html', key=key, profile=profile, layer_tag=layer_tag)

@app.route("/data/validate")
@app.route("/data/<key>/validate")
def show_validate(key=None):
    """Validate the data."""

    # Get the profile
    profile = get_profile(key)
    if not profile or not profile.args.get('url'):
        return redirect('/data/edit', 303)

    # Get the parameters
    url = profile.args.get('url')
    if request.args.get('schema_url'):
        schema_url = request.args.get('schema_url', None)
    else:
        schema_url = profile.args.get('schema_url', None)

    severity_level = request.args.get('severity', None)

    # If we have a URL, validate the data.
    if url:
        errors = do_validate(setup_filters(profile), schema_url, severity_level)
        
    return render_template('data-validate.html', key=key, profile=profile, schema_url=schema_url, errors=errors)

@app.route("/data/<key>.<format>")
@app.route("/data.<format>")
@app.route("/data")
@app.route("/data/<key>") # must come last, or it will steal earlier patterns
def show_data(key=None, format="html"):

    profile = get_profile(key, auth=False)
    if not profile or not profile.args.get('url'):
        return redirect('/data/edit', 303)

    source = setup_filters(profile)
    show_headers = (profile.args.get('strip-headers') != 'on')

    if format == 'json':
        response = Response(source.gen_json(show_headers=show_headers), mimetype='application/json')
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    elif format == 'html':
        return render_template('data.html', source=source, profile=profile, key=key, show_headers=show_headers)
    else:
        response = Response(source.gen_csv(show_headers=show_headers), mimetype='text/csv')
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response

@app.route('/analysis')
def show_analysis_form():
    url = request.args.get('url')
    return render_template('analysis-form.html', url=url)

@app.route('/analysis/hdx')
def show_analysis_hdx():
    datasets = get_hdx_datasets()
    return render_template('analysis-hdx.html', datasets=datasets)

@app.route('/analysis/overview')
def show_analysis_overview():
    if request.args.get('url'):
        analysis = Analysis(args=request.args)
        return render_template('analysis-overview.html', analysis=analysis)
    else:
        return redirect("/analysis", 301)

@app.route('/analysis/data')
@app.route('/analysis/data.<format>')
def show_analysis_data(format=None):
    if request.args.get('url'):
        analysis = Analysis(args=request.args)
        if format == 'csv':
            response = Response(gen_csv(analysis.source), mimetype='text/csv')
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
        elif format == 'json':
            response = Response(gen_json(analysis.source), mimetype='application/json')
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
        else:
            return render_template('analysis-data.html', analysis=analysis)
    else:
        return redirect("/analysis", 301)

@app.route('/analysis/tag/<tag_pattern>')
def show_analysis_tag(tag_pattern):
    if request.args.get('url'):
        analysis = Analysis(args=request.args)
        tag_pattern = TagPattern.parse(tag_pattern)
        return render_template('analysis-tag.html', analysis=analysis, tag_pattern=tag_pattern)
    else:
        return redirect("/analysis", 301)

@app.route("/actions/save-profile", methods=['POST'])
def do_data_save():
    """
    Start a new saved pipeline, or update an existing one.

    Can be called from the full pipeline-edit form, or from
    the mini popup for a pipeline that the user is saving
    for the first time.
    """

    # We will have a key if we're updating an existing pipeline
    key = request.form.get('key')

    profile = get_profile(key, auth=True, args=request.form)

    name = request.form.get('name')
    description = request.form.get('description')
    password = request.form.get('password')
    new_password = request.form.get('new-password')
    password_repeat = request.form.get('password-repeat')
    cloneable = (request.form.get('cloneable') == 'on')

    # Update profile information
    profile.name = name
    profile.description = description
    profile.cloneable = cloneable

    if key:
        # Updating an existing profile.
        if new_password:
            if new_password == password_repeat:
                profile.set_password(new_password)
            else:
                raise BadRequest("Passwords don't match")
        # copy in the new args
        profile.args = request.form.copy()
        g.profiles.update_profile(str(key), profile)
    else:
        # Creating a new profile.
        if password == password_repeat:
            profile.set_password(password)
        else:
            raise BadRequest("Passwords don't match")
        key = g.profiles.add_profile(profile)
        # FIXME other auth information is in __init__.py
        session['passhash'] = profile.passhash

    return redirect(make_data_url(profile, key=key, facet='edit'), 303)

@app.route("/actions/upload", methods=['POST'])
def do_data_upload():
    file = request.files.get('file')
    if file:
        upload = g.uploads.create_upload(file.filename)
        print(upload)
        file.save(upload.get_path())
        #return redirect('/data/edit?url=' + urllib.quote_plus(upload.get_url()), 303)
        return upload.get_url()
    else:
        return "No file"

# end
