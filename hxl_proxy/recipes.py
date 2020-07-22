""" Manage a data-transformation recipe
Started April 2019 by David Megginson
License: Public Domain
"""

import flask, hxl_proxy, hxl_proxy.dao, hxl_proxy.filters, logging, werkzeug


class Recipe:
    """ Class to hold a HXL Proxy recipe.
    The recipe can come either from the request parameters, or from a saved recipe
    in the database. For a saved recipe, it's still possible to override
    certain properties (especially the URL) with the request parameters, so that
    you can use the same recipe with multiple source URLs (disabled for private
    datasets with authentication tokens).
    """

    RECIPE_OVERRIDES = ['url', 'schema_url', 'stub']
    """ Properties that may be overridden in a saved recipe """


    def __init__(self, recipe_id=None, auth=False, request_args=None):
        """ Recipe constructor
        @param recipe_id: the hash identifier of an existing saved recipe
        @param auth: if true, the user needs to authenticate to use the recipe
        @param request_args: custom args to substitute for the current Flask request
        """

        # initialise the properties
        self.recipe_id = str(recipe_id) if recipe_id is not None else None
        self.args = None
        self.name = None
        self.description = None
        self.cloneable = True
        self.passhash = None
        self.stub = None

        self.overridden = False
        self.auth = auth

        # default to the request GET parameters
        if request_args is None:
            request_args = flask.request.args

        # do we have a saved recipe? if so, then populate from the saved data
        if recipe_id is not None:

            # read the recipe from the database
            saved_recipe = hxl_proxy.dao.recipes.read(self.recipe_id)

            if not saved_recipe:
                raise werkzeug.exceptions.NotFound("No saved recipe for {}".format(recipe_id))

            # populate the class from the saved recipe dict
            self.fromDict(saved_recipe)

            # check if this page requires authorisation
            if auth and not self.check_auth():
                raise werkzeug.exceptions.Unauthorized("Wrong or missing password.")

            # allow overrides *only* if we're not using a private dataset
            # (not sending an HTTP Authorization: header)
            if "authorization_token" not in self.args:
                for key in self.RECIPE_OVERRIDES:
                    if key in request_args:
                        self.overridden = True
                        self.args[key] = request_args[key]

        # we don't have a saved recipe: use the HTTP GET parameters
        else:
            self.args = request_args
            self.stub = request_args.get("stub")


    @property
    def url(self):
        return self.args.get("url")

    
    @property
    def schema_url(self):
        return self.args.get("schema_url")

    
    def fromDict(self, props):
        """ Deserialise this object from a dict """
        self.recipe_id = props.get("recipe_id")
        self.name = props.get("name")
        self.description = props.get("description")
        self.cloneable = props.get("cloneable")
        self.passhash = props.get("passhash")
        self.stub = props.get("stub")
        self.date_created = props.get('date_created')
        self.date_modified = props.get('date_modified')
        self.args = dict(props.get("args"))

        
    def toDict(self):
        """ Serialise this object to a dict """
        return {
            "recipe_id": self.recipe_id,
            "name": self.name,
            "description": self.description,
            "cloneable": self.cloneable,
            "passhash": self.passhash,
            "stub": self.stub,
            "args": self.args,
        }


    def logs(self, level="WARNING"):
        handler = Recipe.LogHandler(level)
        logging.getLogger('hxl').addHandler(handler)
        logging.getLogger('hxl_proxy').addHandler(handler)
        source = hxl_proxy.filters.setup_filters(self)
        try:
            for row in source:
                pass
        except:
            pass
        return handler.messages
            

    def check_auth(self, password=None):
        """ Check whether a users is authorised to access this page.
        @param password: a cleartext password
        @returns: True if the user is authorised.
        """

        # does this recipe require a password?
        if self.passhash:
            # do we have a clear-text password?
            if password:
                session_passhash = hxl_proxy.util.make_md5(password)
                flask.session['passhash'] = session_passhash
            # no password, so look in the session token
            else:
                session_passhash = flask.session.get('passhash')

            # do the password hashes match?
            if self.passhash == session_passhash:
                return True
            else:
                flask.session['passhash'] = None
                flask.flash("Wrong password")
                return False

        # no password required, so always OK
        else:
            return True


    class LogHandler(logging.Handler):

        def __init__(self, level):
            super().__init__(level)
            self.messages = []

        def handle(self, record):
            self.messages.append(record)
        


