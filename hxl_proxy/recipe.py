import flask, hxl_proxy, werkzeug


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
        self.recipe_id = str(recipe_id)
        self.args = None
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
            if not recipe:
                raise werkzeug.exceptions.NotFound("No saved recipe for {}".format(recipe_id))

            # check if this page requires authorisation
            if auth and not self.check_auth():
                raise werkzeug.exceptions.Unauthorized("Wrong or missing password.")

            # default args are from the saved recipe
            self.args = recipe.get("args")

            # grab some top-level properties
            self.passhash = recipe.get("passhash")
            self.stub = recipe.get("stub", recipe.args.get("stub"))

            # allow overrides *only* if we're not using a private dataset
            # (not sending an HTTP Authorization: header)
            if "authorization_token" not in args:
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
            if passhash == session_passhash:
                return True
            else:
                session['passhash'] = None
                flask.flash("Wrong password")
                return False

        # no password required, so always OK
        else:
            return True
        


