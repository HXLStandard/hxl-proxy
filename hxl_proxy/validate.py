"""
Validation support
"""

from hxl.io import URLInput, HXLReader
from hxl.schema import readSchema
from hxl_proxy import munge_url

def do_validate(source, schema_url=None):
    """Validate a source, and return a list of errors."""
    errors = []
    def callback(error):
        errors.append(error)
    schema = make_schema(schema_url)
    schema.callback = callback
    result = schema.validate(source)
    return errors

def make_schema(schema_url=None):
    """Get a schema object for validation."""
    if schema_url:
        # return a custom schema
        return readSchema(HXLReader(URLInput(munge_url(schema_url))))
    else:
        # return the built-in default schema
        return readSchema()

# end
