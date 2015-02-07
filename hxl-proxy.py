from urllib2 import urlopen
import sys
from flask import Flask, Response, request, render_template, url_for, stream_with_context
from hxl.parser import HXLReader, genHXL, genJSON, genHTML
from hxl.filters import parse_tags
from hxl.filters.count import HXLCountFilter
from hxl.filters.norm import HXLNormFilter
from hxl.filters.sort import HXLSortFilter
from hxl.filters.cut import HXLCutFilter
from hxl.filters.select import HXLSelectFilter, parse_query

app = Flask(__name__)

@app.route("/")
def home():
    url = request.args.get('url', None)
    return render_template('home.html', url=url)

@app.route("/filter")
def filter():
    url = request.args['url']
    format = request.args.get('format', 'csv')
    
    input = urlopen(url)
    source = HXLReader(input)
    for n in range(1,5):
        filter = request.args.get('filter%02d' % n)
        if filter == 'count':
            tags = parse_tags(request.args.get('tags%02d' % n, ''))
            source = HXLCountFilter(source, tags=tags)
        elif filter == 'sort':
            tags = parse_tags(request.args.get('tags%02d' % n, ''))
            reverse = (request.args.get('sort%02d' % n, 'asc') == 'desc')
            source = HXLSortFilter(source, tags=tags, reverse=reverse)
        elif filter == 'norm':
            source = HXLNormFilter(source)
        elif filter == 'cut':
            tags = parse_tags(request.args.get('tags%02d' % n, ''))
            source = HXLCutFilter(source, include_tags=tags)
        elif filter == 'select':
            query = parse_query(request.args['query%02d' % n])
            source = HXLSelectFilter(source, queries=[query])

    if format == 'json':
        return Response(genJSON(source), mimetype='application/json')
    elif format == 'html':
        return Response(stream_with_context(stream_template('filter.html', source=source)))
    else:
        return Response(genHXL(source), mimetype='text/csv')

app.jinja_env.globals['static'] = (
    lambda filename: url_for('static', filename=filename)
)

def decode(s):
    try:
        return unicode(s, 'utf-8')
    except:
        return s

app.jinja_env.globals['unicode'] = (
    decode
)

def stream_template(template_name, **context):
    """From the flask docs - stream a long template result."""
    app.update_template_context(context)
    t = app.jinja_env.get_template(template_name)
    rv = t.stream(context)
    rv.enable_buffering(5)
    return rv

if __name__ == "__main__":
    app.run(debug=True)

