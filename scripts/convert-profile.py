#!/usr/bin/python3
"""
Convert recipes from the old shelve to sqlite3
"""

import sys, sqlite3, shelve, json

#
# Usage
#
if len(sys.argv) != 3:
    print("Usage: convert-profile <shelve file> <sqlite3 file>")
    exit(2)

shelve_file = sys.argv[1]
sqlite3_file = sys.argv[2]


#
# Leave out old, leaky args, and any empty values
#
IGNORE_ARGS = ['stub', 'key', 'cloneable', 'format', 'filter_count', 'password', 'password-repeat', 'name', 'description']

def clean_args(args_in):
    """Clean the args"""
    args_out = {}
    for name in args_in:
        if name not in IGNORE_ARGS and args_in[name]:
            args_out[name] = args_in[name]
    return args_out


#
# Copy the args
#
shelf = shelve.open(shelve_file, 'r');

connection = sqlite3.connect(sqlite3_file);
cursor = connection.cursor()

cursor.execute('delete from Recipes')

user_id ='david.megginson@gmail.com_1448562216195'
    
for recipe_id in shelf:
    if hasattr(shelf[recipe_id], 'passhash'):
        profile = shelf[recipe_id]
        args = {key: profile.args.get(key) for key in profile.args}

        name = profile.name or "Anonymous recipe"
        description = profile.description
        cloneable = profile.cloneable
        passhash = profile.passhash
        if not passhash:
            passhash = args.get('passhash')
        if hasattr(profile, 'url'):
            args['url'] = profile.url
        if hasattr(profile, 'schema_url'):
            args['schema_url'] = profile.schema_url
        if hasattr(profile, 'stub'):
            stub = profile.stub
        else:
            stub = None

        if passhash:
            cursor.execute(
                "insert into Recipes "
                "(recipe_id, passhash, name, description, cloneable, stub, args, date_created, date_modified) "
                "values (?, ?, ?, ?, ?, ?, ?, date('now'), date('now'))",
                (recipe_id, passhash, name, description, cloneable, stub, json.dumps(clean_args(args)),)
            )
        else:
            print("Skipping {}".format(recipe_id))
    
connection.commit()
connection.close()
shelf.close()

# end
