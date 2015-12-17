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

from flask import Response, flash, request, render_template, redirect, make_response, session, g

import hxl

from hxl_proxy import app, cache
from hxl_proxy.util import get_profile, check_auth, make_data_url, make_cache_key, skip_cache_p, urlencode_utf8
from hxl_proxy.filters import setup_filters, MAX_FILTER_COUNT
from hxl_proxy.validate import do_validate
from hxl_proxy.analysis import Analysis
from hxl_proxy.hdx import get_hdx_datasets
from hxl_proxy.preview import PreviewFilter
from hxl_proxy.auth import get_hid_login_url, get_hid_user
from hxl_proxy.profiles import ProfileManager
from hxl_proxy import dao

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
    g.profiles = ProfileManager(app.config['PROFILE_FILE'])
    g.member = None
    if session.get('member_id'):
        try:
            g.member = dao.get_member(id=session.get('member_id'))
        except:
            # TODO some kind of error message
            pass

#
# Redirects for deprecated URL patterns
#

@app.route("/")
def redirect_home():
    # home isn't moved permanently
    return redirect("/data/source?" + urllib.parse.urlencode(request.args) , 302)

@app.route("/filters/new") # deprecated
def redirect_edit():
    return redirect("/data/source?" + urllib.parse.urlencode(request.args) , 301)

@app.route("/filters/preview") # deprecated
@app.route("/data/preview")
def redirect_data():
    return redirect("/data?" + urllib.parse.urlencode(request.args) , 301)


#
# Primary controllers
#

@app.route("/data/<key>/login")
def show_data_login(key):
    profile = get_profile(key)
    return render_template('data-login.html', key=key, profile=profile)

@app.route("/data/source")
@app.route("/data/<key>/source")
def show_data_source(key=None):
    """Choose a new data source."""

    try:
        profile = get_profile(key, auth=True)
    except Forbidden as e:
        return redirect(make_data_url(None, key=key, facet='login'))

    return render_template('data-source.html', key=key, profile=profile)


@app.route("/data/tagger")
@app.route("/data/<key>/tagger")
def show_data_tag(key=None):
    """Add HXL tags to an untagged dataset."""

    try:
        profile = get_profile(key, auth=True)
    except Forbidden as e:
        return redirect(make_data_url(None, key=key, facet='login'))

    header_row = request.args.get('header-row')
    if header_row:
        header_row = int(header_row)

    if not profile.args.get('url'):
        flash('Please choose a data source first.')
        return redirect(make_data_url(profile, key, 'source'))

    preview = []
    i = 0
    for row in hxl.io.make_input(profile.args.get('url')):
        if i >= 25:
            break
        else:
            i = i + 1
        if row:
            preview.append(row)
        
    return render_template('data-tag.html', key=key, profile=profile, preview=preview, header_row=header_row)


@app.route("/data/edit")
@app.route("/data/<key>/edit", methods=['GET', 'POST'])
def show_data_edit(key=None):
    """Create or edit a filter pipeline."""

    try:
        profile = get_profile(key, auth=True)
    except Forbidden as e:
        return redirect(make_data_url(None, key=key, facet='login'))

    if profile.args.get('url'):
        # show only a short preview
        try:
            source = PreviewFilter(setup_filters(profile), max_rows=5)
            source.columns # force-trigger an exception if not tagged
        except:
            flash('No HXL tags found')
            return redirect(make_data_url(profile, key, 'tagger'))
    else:
        flash('Please choose a data source first.')
        return redirect(make_data_url(profile, key, 'source'))

    # Figure out how many filter forms to show
    filter_count = 0
    for n in range(1, MAX_FILTER_COUNT):
        if profile.args.get('filter%02d' % n):
            filter_count = n
    if filter_count < MAX_FILTER_COUNT:
        filter_count += 1

    show_headers = (profile.args.get('strip-headers') != 'on')

    return render_template('data-filters.html', key=key, profile=profile, source=source, show_headers=show_headers, filter_count=filter_count)

@app.route("/data/profile")
@app.route("/data/<key>/profile")
def show_data_profile(key=None):
    """Show form to save a profile."""

    try:
        profile = get_profile(key, auth=True)
    except Forbidden as e:
        return redirect(make_data_url(None, key=key, facet='login'))

    if not profile or not profile.args.get('url'):
        return redirect('/data/source', 303)

    return render_template('data-profile.html', key=key, profile=profile)

@app.route('/data/<key>/chart')
@app.route('/data/chart')
def show_data_chart(key=None):
    """Show a chart visualisation for the data."""
    profile = get_profile(key)
    if not profile or not profile.args.get('url'):
        return redirect('/data/source', 303)

    source = setup_filters(profile)
    tag = request.args.get('tag')
    if tag:
        tag = hxl.TagPattern.parse(tag);
    label = request.args.get('label')
    if label:
        label = hxl.TagPattern.parse(label);
    type = request.args.get('type', 'bar')
    return render_template('data-chart.html', key=key, profile=profile, tag=tag, label=label, filter=filter, type=type, source=source)

@app.route('/data/<key>/map')
@app.route('/data/map')
def show_data_map(key=None):
    """Show a map visualisation for the data."""
    profile = get_profile(key)
    if not profile or not profile.args.get('url'):
        return redirect('/data/source', 303)
    layer_tag = hxl.TagPattern.parse(request.args.get('layer', 'adm1'))
    return render_template('data-map.html', key=key, profile=profile, layer_tag=layer_tag)

@app.route("/data/validate")
@app.route("/data/<key>/validate")
def show_validate(key=None):
    """Validate the data."""

    # Get the profile
    profile = get_profile(key)
    if not profile or not profile.args.get('url'):
        return redirect('/data/source', 303)

    # Get the parameters
    url = profile.args.get('url')
    if request.args.get('schema_url'):
        schema_url = request.args.get('schema_url', None)
    else:
        schema_url = profile.args.get('schema_url', None)

    severity_level = request.args.get('severity', 'info')

    detail_hash = request.args.get('details', None)

    # If we have a URL, validate the data.
    if url:
        errors = do_validate(setup_filters(profile), schema_url, severity_level)

    return render_template('data-validate.html', key=key, profile=profile, schema_url=schema_url, errors=errors, detail_hash=detail_hash, severity=severity_level)

@app.route("/data/<key>.<format>")
@app.route("/data/<key>/download/<stub>.<format>")
@app.route("/data.<format>")
@app.route("/data")
@app.route("/data/<key>") # must come last, or it will steal earlier patterns
@cache.cached(key_prefix=make_cache_key, unless=skip_cache_p)
def show_data(key=None, format="html", stub=None):

    def get_result (key, format):
        profile = get_profile(key, auth=False)
        if not profile or not profile.args.get('url'):
            return redirect('/data/source', 303)

        source = setup_filters(profile)
        show_headers = (profile.args.get('strip-headers') != 'on')

        if format == 'html':
            return render_template('data.html', source=source, profile=profile, key=key, show_headers=show_headers)
        elif format == 'json':
            response = Response(list(source.gen_json(show_headers=show_headers)), mimetype='application/json')
            response.headers['Access-Control-Allow-Origin'] = '*'
            if hasattr(profile, 'stub') and profile.stub:
                response.headers['Content-Disposition'] = 'attachment; filename={}.json'.format(profile.stub)
            return response
        else:
            response = Response(list(source.gen_csv(show_headers=show_headers)), mimetype='text/csv')
            response.headers['Access-Control-Allow-Origin'] = '*'
            if hasattr(profile, 'stub') and profile.stub:
                response.headers['Content-Disposition'] = 'attachment; filename={}.csv'.format(profile.stub)
            return response

    result = get_result(key, format)
    if skip_cache_p():
        # Want to store the new value, but can't get the key to work
        # Clearing the whole cache for now (heavy-handed)
        cache.set(show_data.make_cache_key(), result)
    return result

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
        return redirect("/analysis", 303)

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
        tag_pattern = hxl.TagPattern.parse(tag_pattern)
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
    if key:
        try:
            profile = get_profile(key, auth=True)
        except Forbidden as e:
            return redirect(make_data_url(None, key=key, facet='login'))
    else:
        profile = get_profile(key, auth=True, args=request.form)

    name = request.form.get('name')
    description = request.form.get('description')
    password = request.form.get('password')
    password_repeat = request.form.get('password-repeat')
    stub = request.form.get('stub')
    cloneable = (request.form.get('cloneable') == 'on')

    # Update profile information
    profile.name = name
    profile.description = description
    profile.cloneable = cloneable
    profile.stub = stub

    if key:
        # Updating an existing profile.
        if password:
            if password == password_repeat:
                profile.set_password(password)
            else:
                raise BadRequest("Passwords don't match")
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

    return redirect(make_data_url(profile, key=key), 303)

@app.route('/settings/user')
def do_user_settings():
    if g.member:
        return render_template('settings-user.html', member=g.member)
    else:
        return redirect('/login')

@app.route('/login')
def do_login():
    return redirect(get_hid_login_url())

@app.route('/logout')
def do_logout():
    session.clear()
    flash("Disconnected from your Humanitarian.ID account (browsing anonymously).")
    return redirect('/')

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
    member = dao.get_member(hid_id=user_info['user_id'])
    if member:
        session['member_id'] = member[0]
    else:
        # TODO show a welcome/setup page for the first visit
        # TODO this logic belongs somewhere else
        member_id = dao.create_member({
            'hid_id': user_info.get('user_id'),
            'hid_name_family': user_info.get('name_family'),
            'hid_name_given': user_info.get('name_given'),
            'hid_email': user_info.get('email'),
            'hid_active': True if user_info.get('active') else False
        })
        session['member_id'] = member_id
    flash("Connected to your Humanitarian.ID account.")
    return redirect('/')

# end
