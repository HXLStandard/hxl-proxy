"""
Validation support
"""

from hxl.io import HXLReader
from hxl.schema import read_schema
from hxl_proxy import make_input

def do_validate(source, schema_url=None):
    """Validate a source, and return a list of errors."""
    errors = []
    def callback(error):
        # FIXME - saving the full row
        errors.append(error)
    schema = make_schema(schema_url)
    schema.callback = callback
    result = schema.validate(source)
    return errors

def make_schema(schema_url=None):
    """Get a schema object for validation."""
    if schema_url:
        # return a custom schema
        return read_schema(HXLReader(make_input(schema_url)))
    else:
        # return the built-in default schema
        return read_schema()

# end
