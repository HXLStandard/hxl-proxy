"""Database access functions and classes."""

import sqlite3, json, os, random, time, base64, hashlib
from flask import g, request
from werkzeug.exceptions import Forbidden, NotFound

from hxl_proxy import app, util


DB_FILE = app.config.get('DB_FILE', '/tmp/hxl-proxy.db')
"""The filename of the SQLite3 database."""

SCHEMA_FILE = os.path.join(os.path.dirname(__file__), 'schema.sql')
"""The filename of the SQL schema."""


class db(object):

    @staticmethod
    def get(db_file=None):
        """Get the database."""
        database = getattr(g, '_database', None)
        if database is None:
            database = g._database = sqlite3.connect(DB_FILE)
            database.row_factory = sqlite3.Row
        return database

    @app.teardown_appcontext
    def close(exception):
        """Close the connection at the end of the request."""
        database = getattr(g, '_database', None)
        if database is not None:
            database.close()

    @staticmethod
    def execute_statement(statement, params=(), commit=False):
        """Execute a single statement."""
        database = db.get()
        cursor = database.cursor()
        cursor.execute(statement, params)
        if commit:
            database.commit()
        return cursor

    @staticmethod
    def execute_script(sql_statements, commit=True):
        """Execute a script of statements, and commit if requested."""
        database = db.get()
        cursor = database.cursor()
        cursor.executescript(sql_statements)
        if commit:
            database.commit()
        return cursor

    @staticmethod
    def execute_file(filename, commit=True):
        """Open a SQL file and execute it as a script."""
        with open(filename, 'r') as input:
            return db.execute_script(input.read(), commit)

    @staticmethod
    def fetchone(statement, params=()):
        """Fetch a single row."""
        row = db.execute_statement(statement, params, commit=False).fetchone()
        if row:
            return dict(row)
        else:
            return None

    @staticmethod
    def fetchall(statement, params=()):
        """Fetch multiple rows."""
        return [dict(row) for row in db.execute_statement(statement, params, commit=False).fetchall()]

    @staticmethod
    def create_db():
        """Create a new database, erasing the current one."""
        db.execute_file(SCHEMA_FILE)


class users(object):
    """Manage user records in the database."""

    @staticmethod
    def create(user):
        """Add a new user."""
        return db.execute_statement(
            "insert into Users"
            " (user_id, email, name, name_given, name_family, last_login)"
            " values (?, ?, ?, ?, ?, datetime('now'))",
            (user.get('user_id'), user.get('email'), user.get('name'), user.get('name_given'), user.get('name_family'),),
            commit=True
        )

    @staticmethod
    def read(user_id):
        """Look up a user by id."""
        return db.fetchone(
            'select * from Users where user_id=?',
            (user_id,)
        )

    @staticmethod
    def update(user):
        """Update an existing user."""
        return db.execute_statement(
            "update Users"
            " set email=?, name=?, name_given=?, name_family=?, last_login=datetime('now')"
            " where user_id=?",
            (user.get('email'), user.get('name'), user.get('name_given'), user.get('name_family'), user.get('user_id')),
            commit=True
        )

    @staticmethod
    def delete(user_id):
        """Delete an existing user."""
        return db.execute_statement(
            "delete from Users where user_id=?",
            (user_id,),
            commit=True
        )


class recipes(object):
    """Manage user records in the database."""

    @staticmethod
    def create(recipe):
        """Add a new recipe."""
        return db.execute_statement(
            "insert into Recipes"
            " (recipe_id, passhash, name, description, cloneable, stub, args, date_created, date_modified)"
            " values (?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))",
            (recipe.get('recipe_id'), recipe.get('passhash'), recipe.get('name'), recipe.get('description'),
             recipe.get('cloneable'), recipe.get('stub'), json.dumps(recipe.get('args', {})),),
            commit=True
        )

    @staticmethod
    def read(recipe_id):
        """Look up a recipe by id."""
        recipe = db.fetchone(
            'select * from Recipes where recipe_id=?',
            (recipe_id,)
        )
        if recipe:
            recipe['args'] = json.loads(recipe.get('args'))
        return recipe

    @staticmethod
    def update(recipe):
        """Update an existing recipe."""
        return db.execute_statement(
            "update Recipes"
            " set passhash=?, name=?, description=?, cloneable=?, stub=?, args=?, "
            " date_modified=datetime('now')"
            " where recipe_id=?",
            (recipe.get('passhash'), recipe.get('name'), recipe.get('description'), recipe.get('cloneable'),
             recipe.get('stub'), json.dumps(recipe.get('args', {})), recipe.get('recipe_id'), ),
            commit=True
        )

    @staticmethod
    def delete(recipe_id):
        """Delete an existing recipe."""
        return db.execute_statement(
            "delete from Recipes where recipe_id=?",
            (recipe_id,),
            commit=True
        )
