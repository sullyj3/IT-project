import sys
import os

from typing import Dict

from flask import Flask, current_app, request, abort, redirect, render_template, flash, url_for

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
from jinja2 import Template

import psycopg2

from persistence import (
        add_artefact,
        add_image,
        create_family,
        edit_artefact_db,
        email_taken,
        family_user_ids,
        generate_img_filename,
        get_artefact_images_metadata,
        get_artefacts,
        get_current_user_family,
        get_family,
        get_family_id,
        get_referral_code,
        remove_artefact,
        get_user,
        get_tags_by_ids,
        get_tags_of_artefacts,
        get_tags_of_each_artefact,
        get_user_artefacts,
        register_user,
        remove_artefact,
        upload_image,
        get_user_loc,
        get_tags_by_names,
        insert_tag,
        pair_tag_to_artefact,
        edit_user_details
)
from views import view_artefacts, view_artefact
from model import Artefact, Credentials, Register, ArtefactImage, Tag

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
    surname = db.Column(db.String(100))
    family_id = db.Column(db.Integer)
    location = db.Column(db.String(200))

    def __init__(self, db_user, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.id = db_user[0]
        self.first_name = db_user[1]
        self.email = db_user[2]
        self.family_id = db_user[5]
        self.surname = db_user[6]
        self.location = db_user[4]


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --------------------- #
# ------ ROUTES ------- #
# --------------------- #
@app.route('/')
def hello_world(msg = None):
    if msg != None:
        flash(msg) 
    if (current_user.is_authenticated):
        return artefacts()        
    return render_template('helloturtles.html')


@app.route('/editartefact/<int:artefact_id>', methods=['GET','POST'])
@login_required
def edit_artefact(artefact_id):
    if (not current_user.is_authenticated):
        flash("Need to be logged in to edit artefacts")
        return redirect('/artefacts')

    try:
        [artefact] = get_artefacts(artefact_id)
    except ValueError as e:
        flash("Couldn't find that artefact")
        return redirect(url_for('artefacts'))


    if request.method == "GET":
        if artefact.owner == current_user.id:

            family = get_current_user_family()
            return render_template('edit_artefact.html', artefact=artefact, family=family)
        else:
            flash("You are not authorised to edit that artefact")
            return redirect('/artefacts')

    elif request.method == "POST":

        if artefact.owner == current_user.id:
            try:
                changed_artefact = create_artefact(artefact_id)
            except KeyError as e:
                print(str(e))
                return unauthorized()
            except ValueError as e:
                print(str(e))
                return unauthorized()

            edit_artefact_db(changed_artefact)

            maybe_add_pics(artefact_id)
            maybe_add_tags(artefact_id)

            flash("Successfully edited artefact")
            return redirect('/artefact/'+str(artefact_id))

        else:
            flash("You are not authorised to edit that artefact")
            return redirect('/  artefacts')

def maybe_add_tags(artefact_id):
    # Puts tags into formatted list
    tags = [tag.strip() for tag in request.form["tags"].split(',')]

    if not tags:
        return

    existing_tags = get_tags_by_names(tags)

    existing_tag_names = [t.name for t in existing_tags]
    tag_ids = [t.tag_id for t in existing_tags]

    for tag in tags:
        if tag not in existing_tag_names:
            tag_ids.append(insert_tag(tag))

    for tag_id in tag_ids:
        pair_tag_to_artefact(artefact_id, tag_id)


@app.route('/profile')
@login_required
def settings():
    return render_template('profile.html')

@app.route('/editprofile', methods=['GET', 'POST'])
@login_required
def editsettings():

    if request.method == 'GET':
        return render_template('edit_account_settings.html')
    elif request.method == 'POST':

        changed_details = Register(first_name = request.form["first_name"],
                                   surname = request.form["surname"],
                                   location = request.form["location"],
                                   family_id = None,
                                   email = None,
                                   password = None
        )


        edit_user_details(current_user.id, changed_details)
        flash("Details changed")
        return redirect('/profile')

@app.route('/family')
@login_required
def familysettings():
    
    referral_code = get_referral_code(current_user.family_id)
    family = get_family(current_user.family_id)
    return render_template('family_settings.html', family=family, referral_code=referral_code)


@app.route('/artefacts')
@login_required
def artefacts():
    family_artefacts = get_user_artefacts(current_user.id, current_user.family_id)
    family_artefact_ids = [p['artefact'].artefact_id for p in family_artefacts]
    family_tags = get_tags_of_artefacts(family_artefact_ids)

    if 'filtertags' in request.args:
        filtertag_ids = [int(tag_id) for tag_id in request.args.getlist('filtertags')]
        filtered_tags = get_tags_by_ids(filtertag_ids)

        artefacts = filter_artefact_previews_by_tags(family_artefacts, filtered_tags)
        return view_artefacts(artefacts, current_user.id, family_tags, filtered_tags)
    else:
        artefacts = family_artefacts
        return view_artefacts(artefacts, current_user.id, family_tags)


def filter_artefact_previews_by_tags(previews: [Dict], tags: [Tag]) -> [Dict]:
    artefact_ids = [preview['artefact'].artefact_id for preview in previews]
    artefact_tags = get_tags_of_each_artefact(artefact_ids)

    print('artefact_tags:')
    print(artefact_tags)

    has_all_tags = []
    for p in previews:
        artefact_id = p['artefact'].artefact_id
        if artefact_id not in artefact_tags:
            continue

        print(f'artefact_id type: {type(artefact_id)}')
        print(f'artefact_id: {artefact_id}')
        print(f'artefact_tags[artefact_id]: {artefact_tags[artefact_id]}')
        if all(tag in artefact_tags[artefact_id] for tag in tags):
            has_all_tags.append(p)

    return has_all_tags

@app.route('/artefact/<int:artefact_id>')
@login_required
def artefact(artefact_id):
    try:
        [artefact] = get_artefacts(artefact_id)
    except ValueError as e:
        flash("Couldn't find that Artefact!")
        return redirect(url_for('artefacts'))

    if artefact.owner in family_user_ids(current_user.family_id):

        artefact_images = get_artefact_images_metadata(artefact_id)

        owner = get_user(artefact.owner)

        if artefact.stored_with == "user":
            location = get_user_loc(artefact.stored_with_user)

        else:
            location = artefact.stored_at_loc

        tags = get_tags_of_artefacts([artefact.artefact_id])

        return view_artefact(artefact, artefact_images, current_user.id, location, owner, tags)

    else:
        flash("You don't have access to this item")
        return unauthorized()

@app.route('/deleteartefact/<int:artefact_id>', methods=['POST'])
@login_required
def delete_artefact(artefact_id):


    try:
        [artefact] = get_artefacts(artefact_id)
    except ValueError as e:
        return "Couldn't find that Artefact!", 400

    if artefact.owner == current_user.id:
        remove_artefact(artefact_id)
        flash("Artefact successfully deleted")
        return redirect('/artefacts')

    else:
        return unauthorized()

    return unauthorized()



@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'GET':

        if current_user.is_authenticated:
            flash("Already logged in!")
            return redirect(url_for('artefacts'))
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
                flash("Successfully logged in")
                return redirect('/')

            else:
                flash("Incorrect details, try again") 
                return redirect('/login')

        else:
            flash("That user doesn't exist!")
            return redirect('/login')


@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'GET':

        if current_user.is_authenticated:
            flash("You are already registered")
            return redirect(url_for('/'))
        else:
            return render_template('register.html')

    elif request.method == 'POST':  

        if request.form['pass'] == request.form['confirm_pass'] and len(request.form['pass']) > 0:

            new_user = Credentials(request.form['email'], request.form['pass'])
            user_details = email_taken(new_user)

            if not user_details:
                # Creates famly if no referral_code

                if "new_family" in request.form:
                    family_id = create_family(request.form['surname'])
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

                flash('Successfully registered')
                return redirect('/')
            else:
                flash("User already exists")
        else:
            flash("Passwords are not the same, or you have missing fields")
        return redirect(url_for('register'))


# Dummy route to logout
@app.route('/logout', methods=['POST'])
@login_required
def logout_page():
    logout_user()
    flash("You have been logged out")
    return redirect('/')


@app.route('/uploadartefact', methods=['GET','POST'])
@login_required
def upload_artefact():
    if request.method == 'GET':
        family = get_current_user_family()

        return render_template('upload_artefact.html', family=family)

    elif request.method == 'POST':
        try:
            new_artefact = create_artefact()
        except KeyError as e:
            return str(e), 400
        except ValueError as e:
            return str(e), 400

        artefact_id = add_artefact(new_artefact)

        maybe_add_tags(artefact_id)
        maybe_add_pics(artefact_id)

        flash("Successfully uploaded artefact")
        return redirect('/artefact/'+str(artefact_id))


def maybe_add_pics(artefact_id: int):
    if 'pic' in request.files:

        pics = request.files.getlist('pic')

        for pic in pics:
            if pic.filename != '':

                fname = generate_img_filename(current_user.id, pic)
                upload_image(pic, fname)
                artefact_image = ArtefactImage(None, artefact_id, fname, None)  
                add_image(artefact_image)
            else:
                print("A file was given, but it was empty")


@login_manager.unauthorized_handler
def unauthorized():

    if current_user.is_authenticated:
        return hello_world(msg = "You don't have access to that page")
    else:
        return hello_world(msg = "You must be logged in as a user authorised for that content in order to access it")

@app.errorhandler(404)
def page_not_found(e):

    return render_template('error_404.html'), 404


@app.errorhandler(400)
def bad_request(e):

    return render_template('error_400.html'), 400

@app.errorhandler(405)
def method_not_allowed(e):
    return redirect('/')

def create_artefact(artefact_id=None) -> Artefact:

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
            raise  KeyError("missing stored_with_user field")
        except ValueError:
            raise ValueError("stored with user wasn't an integer!")

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
