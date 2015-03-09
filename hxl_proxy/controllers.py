"""
Controllers for the HXL Proxy
David Megginson
January 2015

License: Public Domain
Documentation: http://hxlstandard.org
"""

from urllib2 import urlopen
import sys
import copy

from flask import Response, request, render_template, stream_with_context, redirect

from hxl_proxy import app, stream_template, munge_url
from hxl_proxy.profiles import add_profile, update_profile, get_profile, make_profile
from hxl_proxy.data import setup_filters

from hxl.model import TagPattern
from hxl.io import URLInput, HXLReader, genHXL, genJSON
from hxl.schema import readSchema

#@app.errorhandler(Exception)
def error(e):
    if app.config.get('DEBUG'):
        raise e
    else:
        return render_template('error.html', message=str(e))

@app.route("/")
def home():
    return render_template('home.html')
    
@app.route("/filters/new")
@app.route("/data/<key>/edit", methods=['POST'])
def edit_filter(key=None):
    if key:
        profile = get_profile(str(key))
        password = request.form.get('password')
        if not profile.check_password(password):
            raise Exception("Wrong password")
    else:
        profile = make_profile(request.args)
    source = None
    if profile.args.get('url'):
        source = setup_filters(profile)
    return render_template('view-edit.html', key=key, profile=profile, source=source)

@app.route("/actions/save-filter", methods=['POST'])
def save_filter():
    key = request.form.get('key')
    name = request.form.get('name')
    description = request.form.get('description')
    password = request.form.get('password')
    new_password = request.form.get('new-password')
    password_repeat = request.form.get('password-repeat')
    cloneable = (request.form.get('cloneable') == 'on')

    if key:
        profile = get_profile(key)
        profile.args = request.form
    else:
        profile = make_profile(request.form)
    profile.name = name
    profile.description = description
    profile.cloneable = cloneable

    if key:
        if not profile.check_password(password):
            raise Exception("Wrong password")
        if new_password:
            if new_password == password_repeat:
                profile.set_password(new_password)
            else:
                raise Exception("Passwords don't match")
        update_profile(str(key), profile)
    else:
        if password == password_repeat:
            profile.set_password(password)
        else:
            raise Exception("Passwords don't match")
        key = add_profile(profile)

    return redirect("/data/" + key, 303)

@app.route("/validate")
def validate():
    format = 'html' # fixme
    url = request.args.get('url', None)
    schema_url = request.args.get('schema_url', None)
    show_all = (request.args.get('show_all') == 'on')
    source = None
    if url:
        source = HXLReader(URLInput(munge_url(url)))
        schema_source = None
        if schema_url:
            schema = readSchema(HXLReader(URLInput(munge_url(schema_url))))
        else:
            schema = readSchema()
        source = ValidateFilter(source=source, schema=schema, show_all=show_all)
        
    if format == 'json':
        return Response(genJSON(source), mimetype='application/json')
    elif format == 'html':
        return Response(stream_with_context(stream_template('validate.html', url=url, schema_url=schema_url, show_all=show_all, source=source)))
    else:
        return Response(genHXL(source), mimetype='text/csv')

@app.route("/filters/preview")
@app.route("/data/<key>")
@app.route("/data/<key>.<format>")
def filter(key=None, format="html"):

    if key:
        # look up a saved filter
        profile = get_profile(str(key))
    else:
        # use GET parameters
        profile = make_profile(request.args)

    name = profile.args.get('name', 'Filtered HXL dataset')

    source = setup_filters(profile)

    show_headers = (profile.args.get('strip-headers') != 'on')

    if format == 'json':
        response = Response(genJSON(source, showHeaders=show_headers), mimetype='application/json')
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    elif format == 'html':
        return render_template('view-preview.html', title=name, source=source, profile=profile, key=key, show_headers=show_headers)
    else:
        response = Response(genHXL(source, showHeaders=show_headers), mimetype='text/csv')
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response

@app.route('/data/<key>/chart')
def chart(key):
    profile = get_profile(key)
    tag = request.args.get('tag')
    if tag:
            tag = TagPattern.parse(tag);
    label = request.args.get('label')
    if label:
            label = TagPattern.parse(label);
    type = request.args.get('type', 'pie')
    return render_template('chart.html', key=key, args=profile.args, tag=tag, label=label, filter=filter, type=type)

@app.route('/data/<key>/map')
def map(key):
    profile = get_profile(key)
    layer_tag = TagPattern.parse(request.args.get('layer', 'adm1'))
    return render_template('map.html', key=key, args=profile.args, layer_tag=layer_tag)
