"""
Validation support
"""

from hxl import hxl, hxl_schema
from hxl_proxy.util import make_input, munge_url

def do_validate(source, schema_url=None):
    """Validate a source, and return a list of errors."""
    errors = []
    def callback(error):
        # FIXME - saving the full row
        errors.append(error)
    schema = hxl_schema(munge_url(schema_url), callback)
    result = schema.validate(source)
    return errors


# end
