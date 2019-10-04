import sys
import os

from flask import Flask, current_app, request, abort
from jinja2 import Template #TODO move all rendering code to views.py
import psycopg2

from persistence import get_artefacts, add_artefact, email_taken, register_user, upload_image, add_image, generate_img_filename
from authentication import authenticate_user
from views import view_artefacts 
from model import Artefact, Credentials, Register, ArtefactImage, example_artefact
from authentication import generate_pass

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

# --------------------- #
# ------ ROUTES ------- #
# --------------------- #
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
        
        new_user = Credentials(request.form['email'],
                           request.form['password'])
        
        db_user = email_taken(new_user)

        if db_user:
            return authenticate_user(new_user, db_user[3])

        else:
            return "no user exists 😳"
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

            user_details = email_taken(new_user)

            if (not user_details):
                # TODO: change hashing from plaintext to encrypted

                hashed_pword = ""

                # Creates new register with hashed password
                new_register = Register(request.form['first_name'],
                                        request.form['surname'],
                                        request.form['family_id'],
                                        request.form['email'],
                                        request.form['location'],
                                        generate_pass(request.form['pass']))

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

        artefact_id = add_artefact(new_artefact)

        # is there an image?
        if 'pic' in request.files:
            pic = request.files['pic']
            fname = generate_img_filename(request.form['owner'], pic)
            upload_image(pic, fname)

            artefact_image = ArtefactImage(None, artefact_id, fname, None)
            add_image(artefact_image)

        return "Success!"

if __name__ == '__main__':
    app.run()
