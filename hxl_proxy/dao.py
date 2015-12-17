"""
Database access

Started by David Megginson, December 2015
"""

import psycopg2
from psycopg2.extras import DictCursor
from hxl_proxy import app

# Set up the connection
connection = psycopg2.connect("host='{host}' dbname='{dbname}' user='{user}' password='{password}'".format(
    host=app.config.get('DB_HOSTNAME', 'localhost'),
    port=app.config.get('DB_PORT', '5432'),
    dbname=app.config.get('DB_DATABASE', 'proxy'),
    user=app.config.get('DB_USERNAME'),
    password=app.config.get('DB_PASSWORD')
))

def create_member(member):
    with connection:
        with connection.cursor() as cursor:
            cursor.execute('insert into Members '
                           '(hid_id, hid_name_family, hid_name_given, hid_email, hid_active)'
                           'values (%(hid_id)s, %(hid_name_family)s, %(hid_name_given)s, %(hid_email)s, %(hid_active)s)'
                           'returning member',
                           member)
            return cursor.fetchone()[0] # return the new id

def get_member(id=None, hid_id=None):
    with connection:
        with connection.cursor(cursor_factory=DictCursor) as cursor:
            if id is not None:
                cursor.execute('select * from Members where member=%s;', (id,))
            elif hid_id is not None:
                cursor.execute('select * from Members where hid_id=%s;', (hid_id,))
            else:
                raise Exception("Must provide id or hid_id")
            return cursor.fetchone()
    
