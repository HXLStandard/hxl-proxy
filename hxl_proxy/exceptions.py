"""Exception classes.
The proxy uses exceptions sometimes for non-local gotos, such as forcing a redirect.
"""

class RedirectException(Exception):

    def __init__(self, target_url, http_code=302, message=None):
        self.target_url = target_url
        self.http_code = http_code
        self.message = message

# end
