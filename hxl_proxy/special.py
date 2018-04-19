"""Special data sources"""
import csv, logging, requests, sys, werkzeug

logger = logging.getLogger(__name__)

#
# Constants
#

PCODES_URL_PATTERN = 'http://gistmaps.itos.uga.edu/arcgis/rest/services/COD_External/{country}_pcode/MapServer/{level}/query?where=1%3D1&outFields=*&returnGeometry=false&f=pjson'
"""Pattern for constructing an iTOS query URL."""

PCODE_COLUMN_SPECS = {
    "admin0RefName": "#country+name+i_en",
    "admin0Name_fr": "#country+name+i_fr",
    "admin0Pcode": "#country+code",
    "admin1RefName": "#adm1+name+i_en",
    "admin1Name_fr": "#adm1+name+i_fr",
    "admin1Pcode": "#adm1+code",
    "admin2RefName": "#adm2+name+i_en",
    "admin2Name_fr": "#adm2+name+i_fr",
    "admin2Pcode": "#adm2+code",
    "admin3RefName": "#adm3+name+i_en",
    "admin3Name_fr": "#adm3+name+i_fr",
    "admin3Pcode": "#adm3+code",
    "admin4RefName": "#adm4+name+i_en",
    "admin4Name_fr": "#adm4+name+i_fr",
    "admin4Pcode": "#adm4+code",
    "admin5RefName": "#adm5+name+i_en",
    "admin5Name_fr": "#adm5+name+i_fr",
    "admin5Pcode": "#adm5+code",
}
"""Map of iTOS headers to HXL hashtags."""

PCODE_LEVELS = {
    "country": 1,
    "adm1": 2,
    "adm2": 3,
    "adm3": 4,
    "adm4": 5,
    "adm5": 6,
}

#
# Functions
#
def extract_pcodes(country, level, fp):
    """Extract P-codes to HXL-hashtagged CSV
    @param country: an ISO3 country code
    @param level: the admin level (1=country)
    @param fp: a file-like object (with a .write() method)
    """

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
        for header in PCODE_COLUMN_SPECS:
            for field in data['fields']:
                if field['name'] == header:
                    headers.append(header)
        hashtags = [PCODE_COLUMN_SPECS[header] for header in headers]

        # Print the headers and hashtags
        output.writerow(headers)
        output.writerow(hashtags)

        # Process the rows
        for entry in data['features']:
            row = []
            for header in PCODE_COLUMN_SPECS:
                # only fields in the header row get included
                if header in entry['attributes']:
                    row.append(entry['attributes'][header])
            output.writerow(row)

# end
