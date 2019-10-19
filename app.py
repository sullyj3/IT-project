import sys
import os

from flask import Flask, current_app, request, abort, redirect, render_template, flash

from flask_sqlalchemy import SQLAlchemy
from flask_login import (
        LoginManager,
        UserMixin,
        login_user,
        login_required,
        logout_user,
        current_user
)

from flask_bcrypt import check_password_hash, generate_password_hash

import psycopg2

from persistence import (
        get_artefacts,
        add_artefact,
        email_taken,
        register_user,
        upload_image,
        add_image,
        generate_img_filename,
        get_artefact_images_metadata,
        get_user_artefacts,
        family_user_ids,
        edit_artefact_db,
        create_family,
        get_family_id
)
from views import view_artefacts, view_artefact
from model import Artefact, Credentials, Register, ArtefactImage, example_artefact

app = Flask(__name__, template_folder='views')

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


app.config['SQLALCHEMY_DATABASE_URI'] = db_URL
app.config['SECRET_KEY'] = 'hidden'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy()
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)

print()
print("Shell-safe is running!")
print()


# User class to track logging
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(50), unique=True)
    first_name = db.Column(db.String(100))
    surname = db.Column(db.String(100), unique=True)
    family_id = db.Column(db.Integer)

    def __init__(self, db_user, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.id = db_user[0]
        self.first_name = db_user[1]
        self.email = db_user[2]
        self.family_id = db_user[5]
        self.surname = db_user[6]


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --------------------- #
# ------ ROUTES ------- #
# --------------------- #
@app.route('/')
def hello_world():
    if (current_user.is_authenticated):
        return artefacts()        
    return render_template('helloturtles.html')

@app.route('/editartefact/<int:artefact_id>', methods=['GET','POST'])
@login_required
def edit_artefact(artefact_id):
    print(f"got request, method = {request.method}, artefact_id = {artefact_id}")
    if request.method == "GET":

        try:
            [artefact] = get_artefacts(artefact_id)
        except ValueError as e:
            return "Couldn't find that Artefact!", 400

        if artefact.owner == current_user.id:
            return render_template('edit_artefact.html', artefact=artefact)

        else:
            return "not your artefact"

    elif request.method == "POST":
        
        try:
            [artefact] = get_artefacts(artefact_id)
        except ValueError as e:
            return "Couldn't find that Artefact!", 400


        if artefact.owner == current_user.id:
            changed_artefact = create_artefact(artefact_id)

            edit_artefact_db(changed_artefact)
            
            return redirect('/artefact/'+str(artefact_id))

        else:
            return "not your artefact to edit"

@app.route('/settings')
def settings():
    return render_template('account_settings.html')

@app.route('/family')
def familysettings():
    return render_template('family_settings.html')

@app.route('/artefacts')
@login_required
def artefacts():

    return view_artefacts(get_user_artefacts(current_user.id, current_user.family_id))

@app.route('/artefact/<int:artefact_id>')
@login_required
def artefact(artefact_id):
    try:
        [artefact] = get_artefacts(artefact_id)
    except ValueError as e:
        return "Couldn't find that Artefact!", 400

    if artefact.owner in  family_user_ids(current_user.family_id):

        artefact_images = get_artefact_images_metadata(artefact_id)
        return view_artefact(artefact, artefact_images)

    else:
        return unauthorized()

@app.route('/insertexample')
def insert_example():
    add_artefact(example_artefact)
    return('inserting...')


@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'GET':
        
        if current_user.is_authenticated:
            return redirect(hello_world())
        else:
            return render_template('login.html')
    elif request.method == 'POST':
        
        new_user = Credentials(request.form['email'],
                           request.form['password'])

        # Determines if a user with that email exists in the database   
        db_user = email_taken(new_user)
        if db_user:

            hash_pw = db_user[3]

            # Determines if the password has is correct
            if check_password_hash(hash_pw.tobytes(), new_user.password):

                new_user = User(db_user)

                login_user(new_user)

                return redirect('/')
            
            else:

                # TODO Popup message showing incorrect details 
                
                return redirect('/login')


        else:
            return "no user exists 😳"


@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'GET':

        if current_user.is_authenticated:
            return "already logged in 🙄"
        else:
            return render_template('register.html')

    elif request.method == 'POST':
        
        
        if request.form['pass'] == request.form['confirm_pass'] and len(request.form['pass']) > 0:

            new_user = Credentials(request.form['email'], request.form['pass'])
            user_details = email_taken(new_user)

            if (not user_details):         

                # Creates famly if no referral_code

                if request.form["new_family"] ==  "on":
                    family_id =  create_family(request.form['surname'])                
                else:
                    family_id = get_family_id(request.form['referral_code'])
                
                # Creates new register with hashed password
                new_register = Register(request.form['first_name'],
                                        request.form['surname'],
                                        family_id,
                                        request.form['email'],
                                        request.form['location'],
                                        generate_password_hash(request.form['pass']))

                register_user(new_register)


                # Logs in user after adding to database
                db_user = email_taken(new_user)

                login_user(User(db_user))

                return redirect('/')
            else:   
                return "User Exists 😳"
        else:
            return "Different Passwords 😳"


# Dummy route to logout
@app.route('/logout')
@login_required
def logout_page():
    if request.method == 'GET':
        logout_user()
        return redirect('/')


# Dummy route to check if logged in
@app.route('/islogged')
def is_logged_in():
    if request.method == 'GET':
        if current_user.is_authenticated:

            user_info = "Logged in<br>User_id: {}<br>User_email: {}"
            return user_info.format(current_user.id, current_user.email)
        else:
            return "not logged in"

        

@app.route('/uploadartefact', methods=['GET','POST'])
@login_required
def upload_artefact():
    if request.method == 'GET':
        return render_template('upload_artefact.html')

    elif request.method == 'POST':
        
        new_artefact = create_artefact()

        artefact_id = add_artefact(new_artefact)

        if 'pic' in request.files:
   
            pic = request.files['pic']
            fname = generate_img_filename(current_user.id, pic)
            upload_image(pic, fname)
            artefact_image = ArtefactImage(None, artefact_id, fname, None)  
            add_image(artefact_image)
        

        return "Success!"

@login_manager.unauthorized_handler
def unauthorized():
    
    # TODO Make unauthorized html page, redirect to login page

    ''' Must either redirect to a login page if you aren't logged in or say you can't access the page'''

    if current_user.is_authenticated:
        return '''you don't have access to this page<br>
        <img src=https://media1.giphy.com/media/enj50kao8gMfu/source.gif>'''
    else:
        return '''you must be logged in to access this page<br>
        <img src=https://media1.giphy.com/media/enj50kao8gMfu/source.gif>'''

@app.errorhandler(404)
def page_not_found(e):

    return render_template('error_404.html'), 404


@app.errorhandler(400)
def bad_request(e):

    # TODO make bad request page

    return ''' bad request<br>
    <img src=https://media1.giphy.com/media/enj50kao8gMfu/source.gif> ''', 400

def create_artefact(artefact_id=None):

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
        except KeyError:
            return "missing stored_with_user field", 400
        except ValueError:
            return "stored with user wasn't an integer!", 400

    elif request.form['stored_with'] == 'location':
        stored_at_loc = request.form['stored_at_loc']
        stored_with_user = None
    else:
        # any other value for the stored_with enum is invalid
        abort(400)

    new_artefact = Artefact(
            # DB will decide the id, doesn't make sense to add it here.
            # This is really a data modelling issue, need to think about this more.
            artefact_id = artefact_id,
            name        = request.form['name'],
            owner       = current_user.id,
            description = request.form['description'],

            # same for date_stored, database will call CURRENT_TIMESTAMP
            date_stored = None,
            stored_with = request.form['stored_with'],
            stored_with_user = stored_with_user,
            stored_at_loc = stored_at_loc)

    return new_artefact


if __name__ == '__main__':
    app.run()
