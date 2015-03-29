"""
Controllers for the HXL Proxy
David Megginson
January 2015

License: Public Domain
Documentation: http://hxlstandard.org
"""

import sys
import copy
import base64
import urllib

from werkzeug.exceptions import BadRequest, Unauthorized, Forbidden, NotFound

from flask import Response, request, render_template, redirect, make_response, session

from hxl_proxy import app, profiles, get_profile, check_auth, make_data_url
from hxl_proxy.filters import setup_filters
from hxl_proxy.validate import do_validate
from hxl_proxy.hdx import get_hdx_datasets
from hxl_proxy.preview import PreviewFilter

from hxl.model import TagPattern
from hxl.io import gen_hxl, gen_json


#
# Error handling
#

def error(e):
    """Default error page."""
    return render_template('error.html', message=str(e))

if not app.config.get('DEBUG'):
    # Register only if not in DEBUG mode
    app.register_error_handler(Exception, error)


#
# Redirects for deprecated URL patterns
#

@app.route("/")
def redirect_home():
    # home isn't moved permanently
    return redirect("/data/edit?" + urllib.urlencode(request.args) , 302)

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

@app.route("/data/edit")
@app.route("/data/<key>/edit", methods=['GET', 'POST'])
def show_data_edit(key=None):
    """Create or edit a filter pipeline."""

    try:
        profile = get_profile(key, auth=True)
    except Forbidden, e:
        return redirect(make_data_url(None, key=key, facet='login'))

    source = None
    datasets = None
    if profile.args.get('url'):
        # show only a short preview
        source = PreviewFilter(setup_filters(profile), max_rows=5)
    else:
        # pass a list of HDX datasets tagged "hxl"
        datasets = get_hdx_datasets()

    show_headers = (profile.args.get('strip-headers') != 'on')

    return render_template('data-edit.html', key=key, profile=profile, source=source, datasets=datasets, show_headers=show_headers)

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

    # If we have a URL, validate the data.
    if url:
        errors = do_validate(setup_filters(profile), schema_url)
        
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
        response = Response(gen_json(source, show_headers=show_headers), mimetype='application/json')
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    elif format == 'html':
        return render_template('data.html', source=source, profile=profile, key=key, show_headers=show_headers)
    else:
        response = Response(gen_hxl(source, show_headers=show_headers), mimetype='text/csv')
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response

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
        profiles.update_profile(str(key), profile)
    else:
        # Creating a new profile.
        if password == password_repeat:
            profile.set_password(password)
        else:
            raise BadRequest("Passwords don't match")
        key = profiles.add_profile(profile)
        # FIXME other auth information is in __init__.py
        session['passhash'] = profile.passhash

    return redirect(make_data_url(profile, key=key, facet='edit'), 303)

# end
