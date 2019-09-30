import os
from typing import List, Tuple
from collections import namedtuple

from flask import Flask, current_app, request
from jinja2 import Template

import psycopg2
import sys

app = Flask(__name__)

# this stuff needs to go at the top level, rather than in the 
# "if __name__ == '__main__'" stanza. This ensures that when our code is 
# imported (eg by gunicorn), meaning that __name__ is *not* '__main__', our 
# setup still gets run.

# DATABASE_URL is the env variable that heroku uses to give us a reference to
# our postgres database in production. When developing, backend developers 
# should set it to the appropriate URL when running this app
db_URL = os.environ.get("DATABASE_URL")
if db_URL is None:
    print("DATABASE_URL not found! Exiting")
    sys.exit()
else:
    # we store the db_URL in the app config, rather than as a global variable, 
    # to ensure that it is available across requests and threads.
    app.config['db_URL'] = db_URL
    print(f"DATABASE_URL is '{db_URL}'")

# ------ ROUTES -------

@app.route('/')
def hello_world():
    with open("views/helloturtles.html", encoding="utf8") as f:
        template = Template(f.read())
    return template.render()

@app.route('/artefacts')
def artefacts():
    return view_artefacts(get_artefacts())

@app.route('/insertexample')
def insert_example():
    add_artefact(example_artefact)
    return('inserting...')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'GET':
        with open("views/login.html", encoding='utf8') as f:
            template = Template(f.read())
        return template.render()
    elif request.method == 'POST':
        print("finish doing the login stuff")
        

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'GET':
        with open("views/register.html", encoding='utf8') as f:
            template = Template(f.read())
        return template.render()

    elif request.method == 'POST':
        
        if request.form['pass'] == request.form['confirm_pass']:
            
            new_user = Credentials(request.form['email'], request.form['pass'])

            user_details = email_available(new_user)

            if (not user_details):
                # TODO: change hashing from plaintext to encrypted

                hashed_pword = ""

                new_register = Register(request.form['first_name'],
                                        request.form['surname'],
                                        request.form['family_id'],
                                        request.form['email'],
                                        request.form['location'],
                                        request.form['pass'])

                register_user(new_register)
                return "Success! 🔥😎"
            else:
                return "User Exists 😳"
        else:
            return "Different Passwords 😳"



@app.route('/uploadartefact', methods=['GET','POST'])
def upload_artefact():
    if request.method == 'GET':
        # show form
        with open('views/upload_artefact.html', encoding="utf8") as f:
            template = Template(f.read())
        return template.render()

    elif request.method == 'POST':
        # if we get a KeyError accessing the contents of request.form, flask will
        # automatically reply with 400 bad request

        # Either stored_with_user or stored_at_loc will be null in the db,
        # depending on the value of the stored_with enum. Figure out which case we
        # have.
        if request.form['stored_with'] == 'user':
            stored_at_loc = None
            try:
                # stored_with_user should be user_id
                stored_with_user = int(request.form['stored_with_user'])
            except ValueError:
                abort(400)
        elif request.form['stored_with'] == 'location':
            stored_at_loc = request.form['stored_at_loc']
            stored_with_user = None
        else:
            # any other value for the stored_with enum is invalid
            abort(400)

        new_artefact = Artefact(
                # DB will decide the id, doesn't make sense to add it here.
                # This is really a data modelling issue, need to think about this more.
                None,
                request.form['name'],
                int(request.form['owner']),
                request.form['description'],

                # same for date_stored, database will call CURRENT_TIMESTAMP
                None,
                request.form['stored_with'],
                stored_with_user,
                stored_at_loc)

        add_artefact(new_artefact)
        return "Success!"

# doing it this way allows us to do "item.text" instead of "item[1]" which 
# would mean nothing. We use this in the for loop in dummy_data_template.html
Dummy = namedtuple("Dummy", ("id", "text"))
Artefact = namedtuple("Artefact", ("artefact_id",
                                   "name",
                                   "owner",
                                   "description",
                                   "date_stored",
                                   "stored_with",
                                   "stored_with_user",
                                   "stored_at_loc"))

Credentials = namedtuple("Credentials", ("email", "password"))

Register = namedtuple("Register", ("first_name",
                                   "surname",
                                   "family_id",
                                   "email",
                                   "location",
                                   "password"))

example_artefact = Artefact(None, "Spellbook", 1, "old and spooky", None, 'user', 1, None)

# ------ DATABASE -------

'''
    sql: A select statement
'''
def pg_select(sql: str) -> List[Tuple]:
    with psycopg2.connect(current_app.config['db_URL']) as conn:
        cur = conn.cursor()
        cur.execute(sql)
        return cur.fetchall()

def get_artefacts() -> List[Artefact]:
    rows = pg_select('SELECT * FROM Artefact;')
    return [Artefact(*row) for row in rows]

def add_artefact(artefact: Artefact) -> int:
    '''returns the id of the newly inserted artefact'''
    with psycopg2.connect(current_app.config['db_URL']) as conn:
        cur = conn.cursor()
        sql = '''INSERT INTO Artefact
                 (name, owner, description, date_stored, stored_with, stored_with_user, stored_at_loc)
                 VALUES (%(name)s, %(owner)s, %(description)s, CURRENT_TIMESTAMP, %(stored_with)s, %(stored_with_user)s, %(stored_at_loc)s)
                 RETURNING artefact_id;'''

        cur.execute(sql, artefact._asdict())
        (artefact_id,) = cur.fetchone()
        return artefact_id

''' Authenticates a user when they attempt to login '''
def authenticate_user(credentials: Credentials):


    pass

''' Determines if an email is taken in the database '''
def email_available(credentials: Credentials):
    
    sql = '''SELECT *
        FROM "User"
        WHERE email=%(email)s
        LIMIT 1'''

    # Returns user, if none with email returns None
    with psycopg2.connect(current_app.config['db_URL']) as conn:
        cur = conn.cursor()
        cur.execute(sql, credentials._asdict())
        return cur.fetchone()


''' Adds new user to the Database '''
def register_user(register: Register):


    sql = '''INSERT INTO "User"
            (first_name, surname, email, password, location, family_id)
            VALUES (%(first_name)s, %(surname)s, %(email)s, %(password)s, %(location)s, %(family_id)s);'''
    with psycopg2.connect(current_app.config['db_URL']) as conn:
        cur = conn.cursor()
        cur.execute(sql, register._asdict())        


# ------ VIEW -----------

def view_artefacts(artefacts: List[Artefact]) -> str:
    with open('views/artefacts_template.html', encoding='utf8') as f:
        template = Template(f.read())
    return template.render(artefacts=artefacts)

if __name__ == '__main__':
    app.run()

