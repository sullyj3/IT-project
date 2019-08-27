import os
from typing import List, Tuple
from collections import namedtuple

from flask import Flask, current_app
from jinja2 import Template
import psycopg2

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


@app.route('/')
def hello_world():
    with open("helloturtles.html") as f:
        template = Template(f.read())
    return template.render()


@app.route('/dummydata')
def dummy_data():
    return view_dummy_data(get_dummy_data())

# doing it this way allows us to do "item.text" instead of "item[1]" which 
# would mean nothing. We use this in the for loop in dummy_data_template.html


Dummy = namedtuple("Dummy", ("id", "text"))


def get_dummy_data() -> List[Dummy]:

    with psycopg2.connect(current_app.config['db_URL']) as conn:
        cur = conn.cursor()
        cur.execute('SELECT * FROM ITProjectTestTable;')
        data = [Dummy(id, text) for id, text in cur.fetchall()]

    return data


def view_dummy_data(data: List[Dummy]) -> str:
    with open('dummy_data_template.html') as f:
        template = Template(f.read())
    return template.render(data=data)


if __name__ == '__main__':
    app.run()

