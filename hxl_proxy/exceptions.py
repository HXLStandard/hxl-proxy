"""Exception classes.
The proxy uses exceptions sometimes for non-local gotos, such as forcing a redirect.
"""

class RedirectException(Exception):
    """ Exception caught internally for workflow when we need to redirect to a different page
    """

    def __init__(self, target_url, http_code=302, message=None):
        self.target_url = target_url
        self.http_code = http_code
        self.message = message

        
class ForbiddenContentException(Exception):
    """ Exception raised for forbidden content (e.g., URLs or markup in a description)
    """

    def __init__(self, value, reason, field_name=None):
        self.reason = reason
        self.field_name = field_name

    @property
    def human(self):
        return "One of the form fields you submitted had content that is not allowed."

    @property
    def message(self):
        if self.field_name:
            return "Forbidden value for {}: {}".format(self.field_name, self.reason)
        else:
            return "Forbidden value: {}".format(self.reason)

        
class DomainNotAllowedError (IOError):
    """ Error for when a domain is not in the allowed list.
    """

    def __init__ (self, message):
        super().__init__(message)


class RemoteDataException:
    """ 
    Wrapper exception to hide information about a remote data-access failure.
    This prevents a bad actor from using the HXL Proxy to ping a remote
    website (for example).

    """

    def __init__ (self, e):
        self.url = None
        if hasattr(e, 'url'):
            self.url = e.url

    @property
    def human (self):
        return "Sorry, we can't find the remote data you want to process."

    @property
    def message (self):
        if self.url:
            return "No usable data found at {}".format(self.url)
        else:
            return "No usable data found at remote URL"



# end
