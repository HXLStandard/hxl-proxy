"""
Validation support
"""

from hxl import hxl, hxl_schema
from hxl_proxy.util import make_input, munge_url

SEVERITY_LEVELS = {
    'info': 1,
    'warning': 2,
    'error': 3
}

def do_validate(source, schema_url=None, severity_level=None):
    """Validate a source, and return a list of errors."""
    min_severity = SEVERITY_LEVELS.get(severity_level, -1)
    errors = []
    def callback(error):
        if SEVERITY_LEVELS.get(error.rule.severity, 0) >= min_severity:
            errors.append(error)
    schema = hxl_schema(munge_url(schema_url), callback)
    result = schema.validate(source)
    return errors


# end
