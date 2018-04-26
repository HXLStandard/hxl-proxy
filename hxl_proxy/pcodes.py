"""Special data sources"""
import csv, logging, re, requests, sys, werkzeug

logger = logging.getLogger(__name__)

#
# Constants
#

COUNTRY_URL_PATTERN = 'http://gistmaps.itos.uga.edu/arcgis/rest/services/COD_External/{country}_pcode/MapServer/layers?f=pjson'

PCODES_URL_PATTERN = 'http://gistmaps.itos.uga.edu/arcgis/rest/services/COD_External/{country}_pcode/MapServer/{level}/query?where=1%3D1&outFields=*&returnGeometry=false&f=pjson'
"""Pattern for constructing an iTOS query URL."""

PCODE_HEADER_PATTERNS = {
    r'^admin0RefName$': '#country+name+ref',
    r'^admin0Name_([a-z]{2})$': '#country+i_\\1+name',
    r'^admin0Pcode$': '#country+code+iso2',
    r'^admin([1-9])RefName$': '#adm\\1+name+ref',
    r'^admin([1-9])Name_([a-z]{2})$': '#adm\\1+i_\\2+name',
    r'^admin([1-9])Pcode$': '#adm\\1+code',
}
"""Regular expressions mapping iTOS headers to HXL hashtags"""

PCODE_LEVELS = {
    "country": 1,
    "adm1": 2,
    "adm2": 3,
    "adm3": 4,
    "adm4": 5,
    "adm5": 6,
}

def get_country_levels(country):
    """Look up the admin levels available for a country."""
    levels = {}
    country = country.upper()
    url = COUNTRY_URL_PATTERN.format(country=country)
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


#
# Functions
#
def extract_pcodes(country, level, fp):
    """Extract P-codes to HXL-hashtagged CSV
    @param country: an ISO3 country code
    @param level: the admin level (1=country)
    @param fp: a file-like object (with a .write() method)
    """

    country = country.upper()
    level = level.lower()

    if not level in PCODE_LEVELS:
        raise werkzeug.exceptions.NotFound("Unrecognized P-code level: {}".format(level))

    url = PCODES_URL_PATTERN.format(country=country, level=PCODE_LEVELS[level])

    with requests.get(url) as result:
        output = csv.writer(fp)
        data = result.json()

        if "error" in data:
            message = data['error']['message']
            if message.startswith('Service COD_External/'):
                raise werkzeug.exceptions.NotFound('No P-codes found for country {}'.format(country))
            elif message.startswith('Invalid or missing input parameters'):
                raise werkzeug.exceptions.NotFound('No P-codes found at level {} for country {}'.format(level, country))
            else:
                raise werkzeug.exceptions.NotFound(data['error']['message'])

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
            raise werkzeug.exceptions.NotFound('no P-codes available for this admin level')

        # Print the headers and hashtags
        output.writerow(headers)
        output.writerow(hashtags)

        # Process the rows
        for entry in data['features']:
            row = []
            for header in headers:
                # only fields in the header row get included
                if header in entry['attributes']:
                    row.append(entry['attributes'][header])
            output.writerow(row)

# end
