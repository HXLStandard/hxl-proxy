"""
Services for retrieving P-code lists from iTOS
David Megginson
Started April 2018

License: Public Domain
Documentation: https://github.com/HXLStandard/hxl-proxy/wiki
"""

import csv, logging, re, requests, requests_cache, sys, werkzeug

from . import app

logger = logging.getLogger(__name__)

#
# Constants
#
COUNTRY_URL_PATTERN = 'http://gistmaps.itos.uga.edu/arcgis/rest/services/COD_External/{country}_pcode/MapServer/layers?f=pjson'
"""Pattern for constructing an iTOS URL for country metadata"""

PCODES_URL_PATTERN = 'http://gistmaps.itos.uga.edu/arcgis/rest/services/COD_External/{country}_pcode/MapServer/{level}/query?where=1%3D1&outFields=*&returnGeometry=false&f=pjson'
"""Pattern for constructing an iTOS URL for P-codes"""

PCODE_HEADER_PATTERNS = {
    r'^admin0RefName$': '#country+name+ref',
    r'^admin0Name_([a-z]{2})$': '#country+i_\\1+name',
    r'^admin0Pcode$': '#country+code+iso2',
    r'^admin([1-9])RefName$': '#adm\\1+name+ref',
    r'^admin([1-9])Name_([a-z]{2})$': '#adm\\1+i_\\2+name',
    r'^admin([1-9])Pcode$': '#adm\\1+code',
}
"""Regular expressions mapping iTOS headers to HXL hashtags"""


#
# Functions
#
def get_country_levels(country):
    """Look up the admin levels available for a country from the iTOS service.
    @param country: the ISO3 country code (e.g. "GIN")
    @returns: a dict of HXL admin-level names and iTOS levels
    """
    levels = {}
    country = country.upper()
    url = COUNTRY_URL_PATTERN.format(country=country)

    with requests_cache.enabled(
            app.config.get('REQUEST_CACHE', '/tmp/hxl_proxy_requests'), 
            expire_after=app.config.get('PCODE_CACHE_TIMEOUT_SECONDS', 604800)
    ):
        with requests.get(url) as result:
            data = result.json()

    if 'error' in data:
        raise werkzeug.exceptions.NotFound("iTOS P-code service does not support country: {}".format(country))
    for layer in result.json().get('layers'):
        result = re.match(r'^Admin(\d)$', layer['name'])
        if result:
            id = layer['id']
            l = result.group(1)
            if result == 0:
                levels['country'] = id
            else:
                levels['adm{}'.format(l)] = id
    return levels


def extract_pcodes(country, level, fp):
    """Extract P-codes to HXL-hashtagged CSV
    @param country: an ISO3 country code
    @param level: the admin level (1=country)
    @param fp: a file-like object (with a .write() method)
    """

    country = country.upper()
    level = level.lower()

    country_levels = get_country_levels(country)
    if not level in country_levels:
        raise werkzeug.exceptions.NotFound("iTOS P-code service does support admin level {} for {}".format(level, country))

    # Read the data from iTOS
    url = PCODES_URL_PATTERN.format(country=country, level=country_levels[level])
    with requests_cache.enabled(
            app.config.get('REQUEST_CACHE', '/tmp/hxl_proxy_requests'), 
            expire_after=app.config.get('PCODE_CACHE_TIMEOUT_SECONDS', 604800)
    ):
        with requests.get(url) as result:
            data = result.json()
    if "error" in data:
        raise werkzeug.exceptions.BadGateway('Unexpected iTOS P-code service error (try again)')

    # Set up the header and hashtag rows
    headers = []
    hashtags = []
    for field in data['fields']:
        header = field['name']
        for pattern in PCODE_HEADER_PATTERNS:
            if re.fullmatch(pattern, header):
                hashtag = re.sub(pattern, PCODE_HEADER_PATTERNS[pattern], header)
                headers.append(header)
                hashtags.append(hashtag)
                break

    # If we didn't get any columns, it's bad data
    if len(hashtags) == 0:
        raise werkzeug.exceptions.BadGateway('Unexpected iTOS P-code service error (try again)')

    # Generate the CSV headers and hashtags
    output = csv.writer(fp)
    output.writerow(headers)
    output.writerow(hashtags)

    # Generate the CSV data rows
    for entry in data['features']:
        row = []
        for header in headers:
            # only fields in the header row get included
            if header in entry['attributes']:
                row.append(entry['attributes'][header])
        output.writerow(row)

# end
