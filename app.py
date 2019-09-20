import os
from typing import List, Tuple
from collections import namedtuple

from flask import Flask, current_app, request, abort
from jinja2 import Template
from werkzeug.datastructures import FileStorage

import psycopg2
import sys
from datetime import datetime

from images import upload_image

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

        artefact_id = add_artefact(new_artefact)

        # is there an image?
        if 'pic' in request.files:
            pic = request.files['pic']
            fname = generate_img_filename(request.form['owner'], pic)
            upload_image(pic, fname)

            artefact_image = ArtefactImage(None, artefact_id, fname, None)
            add_image(artefact_image)

        return "Success!"

def generate_img_filename(user_id: str, img: FileStorage):
    name, ext = img.filename.rsplit('.',1)
    timestamp = datetime.utcnow().isoformat().replace(":", "_")
    return f'{user_id}-{name}-{timestamp}.{ext}'

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
ArtefactImage = namedtuple("ArtefactImage", ("image_id",
                                             "artefact_id",
                                             "image_url",
                                             "image_description"))

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

def add_image(artefact_image: ArtefactImage):
    with psycopg2.connect(current_app.config['db_URL']) as conn:
        cur = conn.cursor()
        sql = '''INSERT INTO ArtefactImage
                 (artefact_id, image_url, image_description)
                 VALUES (%(artefact_id)s, %(image_url)s, %(image_description)s)'''

        cur.execute(sql, artefact_image._asdict())


# ------ VIEW -----------

def view_artefacts(artefacts: List[Artefact]) -> str:
    with open('views/artefacts_template.html') as f:
        template = Template(f.read())
    return template.render(artefacts=artefacts)

if __name__ == '__main__':
    app.run()

