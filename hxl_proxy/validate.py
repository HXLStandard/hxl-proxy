"""
Validation support
"""

from hxl import hxl, hxl_schema
from hxl_proxy.util import make_input

def do_validate(source, schema_url=None):
    """Validate a source, and return a list of errors."""
    errors = []
    def callback(error):
        # FIXME - saving the full row
        errors.append(error)
    schema = hxl_schema(schema_url)
    result = schema.validate(source, callback)
    return errors


# end
