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

from werkzeug.exceptions import BadRequest, Unauthorized, Forbidden, NotFound

from flask import Response, request, render_template, redirect, make_response

from hxl_proxy import app, profiles, munge_url, get_profile, check_auth
from hxl_proxy.filters import setup_filters
from hxl_proxy.validate import do_validate

from hxl.model import TagPattern
from hxl.io import genHXL, genJSON

def error(e):
    return render_template('error.html', message=str(e))

if not app.config.get('DEBUG'):
    app.register_error_handler(Exception, error)

@app.route("/")
def show_home():
    """Home page."""
    return render_template('home.html')
    
@app.route("/filters/new") # deprecated
@app.route("/data/edit")
@app.route("/data/<key>/edit", methods=['GET', 'POST'])
def show_edit_profile(key=None):
    """Create or edit a filter pipeline."""
    profile = get_profile(key, auth=True)
    source = None
    if profile.args.get('url'):
        source = setup_filters(profile)
    show_headers = (profile.args.get('strip-headers') != 'on')

    response = make_response(render_template('profile-edit.html', key=key, profile=profile, source=source, show_headers=show_headers))
    if key:
        response.set_cookie('hxl', base64.b64encode(profile.passhash))
    return response

@app.route("/actions/save-profile", methods=['POST'])
def do_save_profile():
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
        profiles.update_profile(str(key), profile)
    else:
        # Creating a new profile.
        if password == password_repeat:
            profile.set_password(password)
        else:
            raise BadRequest("Passwords don't match")
        key = profiles.add_profile(profile)

    return redirect("/data/" + key, 303)

@app.route("/filters/preview") # deprecated
@app.route("/data/preview")
@app.route("/data/<key>")
@app.route("/data/<key>.<format>")
def show_preview_data(key=None, format="html"):
    profile = get_profile(key, auth=False)
    if key:
        is_authorised = check_auth(profile)
    else:
        is_authorised = False

    name = profile.args.get('name', 'Filtered HXL dataset')
    source = setup_filters(profile)
    show_headers = (profile.args.get('strip-headers') != 'on')
    if format == 'json':
        response = Response(genJSON(source, showHeaders=show_headers), mimetype='application/json')
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    elif format == 'html':
        return render_template('data-preview.html', title=name, source=source, profile=profile, key=key,
                               show_headers=show_headers, is_authorised=is_authorised)
    else:
        response = Response(genHXL(source, showHeaders=show_headers), mimetype='text/csv')
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response

@app.route('/data/<key>/chart')
def show_chart(key):
    """Show a chart visualisation for the data."""
    profile = get_profile(key)
    tag = request.args.get('tag')
    if tag:
            tag = TagPattern.parse(tag);
    label = request.args.get('label')
    if label:
            label = TagPattern.parse(label);
    type = request.args.get('type', 'pie')
    return render_template('chart.html', key=key, profile=profile, tag=tag, label=label, filter=filter, type=type)

@app.route('/data/<key>/map')
def show_map(key):
    """Show a map visualisation for the data."""
    profile = get_profile(key)
    layer_tag = TagPattern.parse(request.args.get('layer', 'adm1'))
    return render_template('map.html', key=key, profile=profile, layer_tag=layer_tag)

@app.route("/data/validate")
@app.route("/data/<key>/validate")
def show_validate(key):
    """Validate the data."""

    # Get the profile
    profile = get_profile(key)

    # Get the parameters
    url = profile.args.get('url')
    schema_url = profile.args.get('schema_url', None)

    # If we have a URL, validate the data.
    if url:
        errors = do_validate(setup_filters(profile), schema_url)
        
    return render_template('validate.html', key=key, profile=profile, errors=errors)

# end
