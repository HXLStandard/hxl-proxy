"""Database access functions and classes."""

import sqlite3, json, os, random, time, base64, hashlib
from flask import g, request
from werkzeug.exceptions import Forbidden, NotFound

from hxl_proxy import app, util


SCHEMA_FILE = os.path.join(os.path.dirname(__file__), 'schema.sql')
"""The filename of the SQL schema."""


_database = None
"""The persistent database connection."""


def get_db(db_file=None):
    """Get the database."""
    global _database
    if _database is None:
        if db_file is None:
            db_file = app.config.get('DB_FILE', '/tmp/hxl-proxy.db')
        _database = sqlite3.connect(db_file)
        _database.row_factory = sqlite3.Row
    return _database

@app.teardown_appcontext
def close_db(exception):
    """Close the connection at the end of the request."""
    if _database is not None:
        _database.close()

def execute_statement(statement, params=(), commit=False):
    """Execute a single statement."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute(statement, params)
    if commit:
        db.commit()
    return cursor

def fetchone(statement, params=()):
    """Fetch a single row."""
    row = execute_statement(statement, params, commit=False).fetchone()
    if row:
        return dict(row)
    else:
        return None

def fetchall(statement, params=()):
    """Fetch multiple rows."""
    return [dict(row) for row in execute_statement(statement, params, commit=False).fetchall()]

def execute_script(sql_statements, commit=True):
    """Execute a script of statements, and commit if requested."""
    db = get_db()
    cursor = db.cursor()
    cursor.executescript(sql_statements)
    if commit:
        db.commit()
    return cursor

def execute_file(filename, commit=True):
    """Open a SQL file and execute it as a script."""
    with open(filename, 'r') as input:
        return execute_script(input.read(), commit)

def _make_md5(s):
    """Return an MD5 hash for a string."""
    return hashlib.md5(s.encode('utf-8')).digest()

def _gen_key():
    """
    Generate a pseudo-random, 6-character hash for use as a key.
    """
    salt = str(time.time() * random.random())
    encoded_hash = base64.urlsafe_b64encode(_make_md5(salt))
    return encoded_hash[:6].decode('ascii')

def create_db():
    """Create a new database, erasing the current one."""
    execute_file(SCHEMA_FILE)


class user(object):
    """Manage user records in the database."""

    @staticmethod
    def create(user):
        """Add a new user."""
        return execute_statement(
            "insert into Users"
            " (user_id, email, name, name_given, name_family, last_login)"
            " values (?, ?, ?, ?, ?, datetime('now'))",
            (user.get('user_id'), user.get('email'), user.get('name'), user.get('name_given'), user.get('name_family'),),
            commit=True
        )

    @staticmethod
    def read(user_id):
        """Look up a user by id."""
        return fetchone(
            'select * from Users where user_id=?',
            (user_id,)
        )

    @staticmethod
    def update(user):
        """Update an existing user."""
        return execute_statement(
            "update Users"
            " set email=?, name=?, name_given=?, name_family=?, last_login=datetime('now')"
            " where user_id=?",
            (user.get('email'), user.get('name'), user.get('name_given'), user.get('name_family'), user.get('user_id')),
            commit=True
        )

    @staticmethod
    def delete(user_id):
        """Delete an existing user."""
        return execute_statement(
            "delete from Users where user_id=?",
            (user_id,),
            commit=True
        )


class recipe(object):
    """Manage user records in the database."""

    @staticmethod
    def create(recipe):
        """Add a new recipe."""
        return execute_statement(
            "insert into Recipes"
            " (recipe_id, user_id, name, description, cloneable, stub, args, date_created, date_modified)"
            " values (?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))",
            (recipe.get('recipe_id'), recipe.get('user_id'), recipe.get('name'), recipe.get('description'), recipe.get('cloneable'),
             recipe.get('stub'), json.dumps(recipe.get('args', {})),),
            commit=True
        )

    @staticmethod
    def read(recipe_id):
        """Look up a recipe by id."""
        recipe = fetchone(
            'select * from Recipes where recipe_id=?',
            (recipe_id,)
        )
        if recipe:
            recipe['args'] = json.loads(recipe.get('args'))
        return recipe

    @staticmethod
    def update(recipe):
        """Update an existing recipe."""
        return execute_statement(
            "update Recipes"
            " set name=?, description=?, cloneable=?, stub=?, args=?, "
            " date_modified=datetime('now')"
            " where recipe_id=?",
            (recipe.get('name'), recipe.get('description'), recipe.get('cloneable'),
             recipe.get('stub'), json.dumps(recipe.get('args', {})), recipe.get('recipe_id'), ),
            commit=True
        )

    @staticmethod
    def delete(recipe_id):
        """Delete an existing recipe."""
        return execute_statement(
            "delete from Recipes where recipe_id=?",
            (recipe_id,),
            commit=True
        )
