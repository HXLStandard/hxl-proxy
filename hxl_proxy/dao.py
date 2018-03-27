"""Database access functions.

This module contains all database dependencies for the HXL Proxy. It
uses three classes as submodules: L{db} for low-level access, L{user}
for managing user records, and L{recipe} for managing recipe
records. L{user} and L{recipe} both have the standard CRUD (create,
read, update, and delete) functions.  Example:

  from hxl_proxy import dao

  user = dao.users.read('user@example.org')
  user['name_given'] = 'Fred'
  dao.users.update(user)

Database access usually has to happen inside a Flask request context,
and the database connection exists only for the scope of the request;
however, there is a kludge to keep the connection as a local variable
outside a request context for unit testing.

The name of the database is in the Flask config option C{DB_FILE}. The
SQL schema is in the hxl_proxy module directory as C{schema.sql} (see
that file for the properties of each record type).

"""

import sqlite3, mysql.connector, json, os, random, time, base64, hashlib, flask
import hxl_proxy


class db:
    """Low-level database functions"""

    TEST_SCHEMA_FILE = os.path.join(os.path.dirname(__file__), 'schema-sqlite3.sql')
    """The filename of the SQL schema."""

    type = hxl_proxy.app.config.get('DB_TYPE', 'sqlite3')


    _database = None
    """Internal connection, for testing use outside a request context."""


    @staticmethod
    def connect():
        """Get a database connection 

        Will reuse the same connection throughout a request
        context. Uses the C{DB_FILE} Flask config option for the
        location of SQLite3 file.

        @return: a SQLite3 database connection
        """
        if flask.has_request_context(): #FIXME - this is an ugly dependency
            database = getattr(flask.g, '_database', None)
        else:
            database = db._database
        if database is None:
            if db.type == 'sqlite3':
                file = hxl_proxy.app.config.get('DB_FILE', ':memory:')
                database = sqlite3.dbapi2.connect(file)
                database.row_factory = sqlite3.Row
            elif db.type == 'mysql':
                database = mysql.connector.connect(
                    host=hxl_proxy.app.config.get('DB_HOST', 'localhost'),
                    port=hxl_proxy.app.config.get('DB_PORT', 3306),
                    database=hxl_proxy.app.config.get('DB_DATABASE', 'hxl_proxy'),
                    user=hxl_proxy.app.config.get('DB_USERNAME'),
                    password=hxl_proxy.app.config.get('DB_PASSWORD'),
                )
            else:
                raise Exception('Unknown database type: {}'.format(db.DB_TYPE))
            if flask.has_request_context():
                flask.g._database = database
            else:
                db._database = database
        return database

    @hxl_proxy.app.teardown_appcontext
    def close(exception):
        """Close the connection at the end of the request."""
        database = getattr(flask.g, '_database', None)
        if database is not None:
            database.close()

    @staticmethod
    def cursor():
        database = db.connect()
        if db.type == 'mysql':
            return database.cursor(dictionary=True)
        else:
            return database.cursor()

    @staticmethod
    def commit():
        db.connect().commit()
        
    @staticmethod
    def execute_statement(statement, params=(), commit=False):
        """Execute a single SQL statement, and optionally commit.

        @param statement: the SQL statement to execute.
        @param params: sequence of values for any C{%s} placeholders in the statement.
        @param commit: if True, autocommit at the end of the statement (default: False)
        @return: a SQLite3 cursor object.
        """
        cursor = db.cursor()
        cursor.execute(db.fix_params(statement), params)
        if commit:
            db.commit()
        return cursor

    @staticmethod
    def execute_script(sql_statements, commit=True):
        """Execute a script of statements, and optionally commit.
        @param sql_statements: a string containing multiple SQL statements, separated by ';'
        @param commit: if True, autocommit after executing the statements (default: True)
        @return: a SQLite3 cursor object.
        """
        cursor = db.cursor()
        cursor.executescript(sql_statements)
        if commit:
            db.commit()
        return cursor

    @staticmethod
    def execute_file(filename, commit=True):
        """Open a SQL file and execute it as a script.
        @param filename: path to a file containing SQL statements, separated by ';'
        @param commit: if True, autocommit after executing the statments (default: True)
        @return: a SQLite3 cursor object.
        """
        with open(filename, 'r') as input:
            return db.execute_script(input.read(), commit)

    @staticmethod
    def fetchone(statement, params=()):
        """Fetch a single row of data.
        @param statement: the SQL statement to execute.
        @param params: sequence of values for any placeholders in the statement.
        @return: a single row as a dict.
        @see: L{db.execute_statement}
        """
        row = db.execute_statement(statement, params, commit=False).fetchone()
        if row:
            return dict(row)
        else:
            return None

    @staticmethod
    def fetchall(statement, params=()):
        """Fetch a multiple rows of data.
        @param statement: the SQL statement to execute.
        @param params: sequence of values for any C{%s} placeholders in the statement.
        @return: multiple rows as a list of dicts.
        @see: L{db.execute_statement}
        """
        return [dict(row) for row in db.execute_statement(statement, params, commit=False).fetchall()]

    @staticmethod
    def create_db():
        """Create a new database, erasing the current one.
        Use this method only for temporary databases in unit testing. Uses L{db.TEST_SCHEMA_FILE} to create
        the temporary database.
        """
        db.execute_file(db.TEST_SCHEMA_FILE)

    @staticmethod
    def fix_params(statement):
        if db.type == 'sqlite3':
            statement = statement.replace('%s', '?')
        return statement


class users:
    """Functions for managing database records for users."""

    @staticmethod
    def create(user, commit=True):
        """Add a new user record and optionally commit.
        @param user: a dict of properties for a user.
        @param commit: if True, autocommit after adding the user record (default: True).
        @return: a SQLite3 cursor object.
        """
        return db.execute_statement(
            "insert into Users"
            " (user_id, email, name, name_given, name_family, last_login)"
            " values (%s, %s, %s, %s, %s, %s)",
            (
                user.get('user_id'),
                user.get('email'),
                user.get('name'),
                user.get('name_given'),
                user.get('name_family'),
                time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime()),
            ),
            commit=commit
        )

    @staticmethod
    def read(user_id):
        """Look up a user record by id.
        @param user_id: the user's unique identifier in the database.
        @return: a dict of user properties, or None if the record doesn't exist.
        """
        return db.fetchone(
            'select * from Users where user_id=%s',
            (user_id,)
        )

    @staticmethod
    def update(user, commit=True):
        """Update an existing user record.
        @param user: a dict of user properties, including the C{user_id}.
        @param commit: if True, autocommit after updating the user record (default: True).
        @return: a SQLite3 cursor object.
        """
        return db.execute_statement(
            "update Users"
            " set email=%s, name=%s, name_given=%s, name_family=%s, last_login=%s"
            " where user_id=%s",
            (
                user.get('email'),
                user.get('name'),
                user.get('name_given'),
                user.get('name_family'),
                time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime()),
                user.get('user_id'),
            ),
            commit=commit
        )

    @staticmethod
    def delete(user_id, commit=True):
        """Delete an existing user record and optionally commit.
        @param user_id: the user's unique identifier in the database.
        @param commit: if True, autocommit after deleting the user record (default: True).
        @return: a SQLite3 cursor object.
        """
        return db.execute_statement(
            "delete from Users where user_id=%s",
            (user_id,),
            commit=commit
        )


class recipes:
    """Database recipe records"""

    @staticmethod
    def create(recipe, commit=True):
        """Add a new recipe record and optionally commit.
        @param recipe: a dict of properties for a recipe.
        @param commit: if True, autocommit after adding the recipe record (default: True).
        @return: a SQLite3 cursor object.
        """
        return db.execute_statement(
            "insert into Recipes"
            " (recipe_id, passhash, name, description, cloneable, stub, args, date_created, date_modified)"
            " values (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (
                recipe.get('recipe_id'),
                recipe.get('passhash'),
                recipe.get('name'),
                recipe.get('description'),
                recipe.get('cloneable'),
                recipe.get('stub'),
                json.dumps(recipe.get('args', {})),
                time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime()),
                time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime()),
            ),
            commit=commit
        )

    @staticmethod
    def read(recipe_id):
        """Look up a recipe record by id.
        @param recipe_id: the recipe's unique identifier in the database.
        @return: a dict of recipe properties, or None if the record doesn't exist.
        """
        recipe = db.fetchone(
            'select * from Recipes where recipe_id=%s',
            (recipe_id,)
        )
        if recipe:
            recipe['args'] = json.loads(recipe.get('args'))
        return recipe

    @staticmethod
    def update(recipe, commit=True):
        """Update an existing recipe record.
        @param recipe: a dict of recipe properties, including the C{recipe_id}.
        @param commit: if True, autocommit after updating the recipe record (default: True).
        @return: a SQLite3 cursor object.
        """
        return db.execute_statement(
            "update Recipes"
            " set passhash=%s, name=%s, description=%s, cloneable=%s, stub=%s, args=%s, "
            " date_modified=%s"
            " where recipe_id=%s",
            (
                recipe.get('passhash'),
                recipe.get('name'),
                recipe.get('description'),
                recipe.get('cloneable'),
                recipe.get('stub'),
                json.dumps(recipe.get('args', {})),
                time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime()),
                recipe.get('recipe_id'),
            ),
            commit=commit
        )

    @staticmethod
    def delete(recipe_id, commit=True):
        """Delete an existing recipe record and optionally commit.
        @param recipe_id: the recipe's unique identifier in the database.
        @param commit: if True, autocommit after deleting the recipe record (default: True).
        @return: a SQLite3 cursor object.
        """
        return db.execute_statement(
            "delete from Recipes where recipe_id=%s",
            (recipe_id,),
            commit=commit
        )
