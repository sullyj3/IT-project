from typing import List, Tuple, Dict
from datetime import datetime

from flask import current_app
from flask_login import current_user
from werkzeug.datastructures import FileStorage
import psycopg2

import boto3

import string
import random

from model import Artefact, Credentials, Register, ArtefactImage, ArtefactUser, User

############
# Database #
############


def row_to_artefact_preview(row: Tuple) -> Dict:
    '''
    takes a row consisting of the artefact fields, user first and last names,
    and optionally the first ArtefactImage associated with that artefact
    and collates them into a dict like this:

    {
        'artefact': Artefact
        'first_name': str
        'last_name': str
        'image': ArtefactImage or None
    }
    '''

    d = dict()
    d['artefact'] = Artefact(*(row[0:8]))
    d['first_name'] = row[8]
    d['last_name'] = row[9]

    # artefact may not have any images associated with it
    d['image'] = (img_with_presigned_url(ArtefactImage(*(row[10:])))
                  if row[10] is not None
                  else None)

    return d


# Returns the artefacts that the user is able to view
def get_user_artefacts(user_id, family_id) -> List[ArtefactUser]:

    # Relevant inputs for where clauses
    inputs = {"user_id": user_id,
              "family_id": family_id}

    sql = '''
    SELECT DISTINCT ON (Artefact.artefact_id)
        Artefact.*, "user".first_name, "user".surname, ArtefactImage.*
    FROM "user"
    INNER JOIN Artefact
    ON Artefact.owner = "user".id
    LEFT JOIN ArtefactImage
    ON Artefact.artefact_id = ArtefactImage.artefact_id
    WHERE "user".family_id = %(family_id)s
    '''

    rows = pg_select(sql=sql, where=inputs)

    return [row_to_artefact_preview(row) for row in rows]


def pg_select(sql: str, where=None) -> List[Tuple]:
    '''
        sql: A select statement
        can now work with input dicts
    '''
    try:
        conn = psycopg2.connect(current_app.config['db_URL'])
    except e:
        print("couldn't connect to " + current_app.config['db_URL'])
        raise e

    with conn:
        cur = conn.cursor()
        if where is not None:
            cur.execute(sql, where)
        else:
            cur.execute(sql)

        return cur.fetchall()


''' Returns a family with the ids and users '''
def get_family(family_id) -> List[User]:
    inputs = {"family_id": family_id}

    sql = '''SELECT id, first_name, surname
             FROM "user"
             WHERE family_id = %(family_id)s'''

    rows = pg_select(sql=sql, where=inputs)

    return [User(*row) for row in rows]


def get_current_user_family() -> List[User]:
    return get_family(current_user.family_id)


# Returns the list of users ids for a given family
def family_user_ids(family_id) -> List[int]:

    inputs = {"family_id": family_id}

    sql = '''SELECT id
             FROM "user"
             WHERE family_id = %(family_id)s'''

    rows = pg_select(sql=sql, where=inputs)
    
    return [row[0] for row in rows]
    # return rows

    # return [row(0) for row in rows]


def get_artefacts(artefact_ids=None) -> [Artefact]:
    '''Can be passed a single id or a list of IDs. If a single id is passed, 
       the returned list will contain just one Artefact.
    '''

    if artefact_ids is None:
        rows = pg_select('SELECT * FROM Artefact;')

    elif type(artefact_ids) == int:
        rows = pg_select('SELECT * from Artefact WHERE artefact_id=%s',
                (artefact_ids,))

    elif type(artefact_ids) == list:
        rows = pg_select('SELECT * from Artefact WHERE artefact_id IN %s',
                (artefact_ids,))
    else:
        raise ValueError("artefact_ids must be an int or list of ints")

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


def edit_artefact_db(artefact: Artefact):
    ''' changes a new artefact '''

    with psycopg2.connect(current_app.config['db_URL']) as conn:
        cur = conn.cursor()
        sql = '''UPDATE Artefact
                 (name, owner, description, date_stored, stored_with, stored_with_user, stored_at_loc)
                 VALUES (%(name)s, %(owner)s, %(description)s, CURRENT_TIMESTAMP, %(stored_with)s, %(stored_with_user)s, %(stored_at_loc)s)
                 RETURNING artefact_id;'''

        sql = '''UPDATE Artefact
                 SET name = %(name)s, description = %(description)s, stored_with_user = %(stored_with_user)s, stored_at_loc = %(stored_at_loc)s, stored_with = %(stored_with)s
                 WHERE artefact_id = %(artefact_id)s;'''

        cur.execute(sql, artefact._asdict())


''' Determines if an email is taken in the database, if not returns the  '''
def email_taken(credentials: Credentials):

    sql = '''SELECT *
        FROM "user"
        WHERE email=%(email)s
        LIMIT 1'''

    # Returns user, if none with email returns None
    with psycopg2.connect(current_app.config['db_URL']) as conn:
        cur = conn.cursor()
        cur.execute(sql, credentials._asdict())
        return cur.fetchone()



''' Adds new user to the Database '''
def register_user(register: Register):

    sql = '''INSERT INTO "user"
            (first_name, surname, email, password, location, family_id)
            VALUES (%(first_name)s, %(surname)s, %(email)s, %(password)s, %(location)s, %(family_id)s);'''
    with psycopg2.connect(current_app.config['db_URL']) as conn:
        cur = conn.cursor()
        cur.execute(sql, register._asdict())

#############
# Amazon S3 #
#############
s3 = boto3.resource('s3')

def print_buckets():
    for bucket in s3.buckets.all():
        print(bucket.name)

def upload_image(img, s3key):
    bucket = s3.Bucket('shell-safe')
    bucket.put_object(Key=s3key, Body=img)

def add_image(artefact_image: ArtefactImage):
    with psycopg2.connect(current_app.config['db_URL']) as conn:
        cur = conn.cursor()
        sql = '''INSERT INTO ArtefactImage
                 (artefact_id, image_url, image_description)
                 VALUES (%(artefact_id)s, %(image_url)s, %(image_description)s)'''

        cur.execute(sql, artefact_image._asdict())

def get_artefact_images_metadata(artefact_id: int) -> [ArtefactImage]:
    rows = pg_select('SELECT * FROM ArtefactImage WHERE artefact_id = %s;',
            (artefact_id, ))
    return [img_with_presigned_url(ArtefactImage(*row)) for row in rows]


def generate_img_filename(user_id: str, img: FileStorage):
    name, ext = img.filename.rsplit('.',1)
    timestamp = datetime.utcnow().isoformat().replace(":", "_")
    return f'{user_id}-{name}-{timestamp}.{ext}'

# from https://boto3.amazonaws.com/v1/documentation/api/latest/guide/s3-presigned-urls.html
def create_presigned_url(object_name, expiration=3600):
    """Generate a presigned URL to share an S3 object

    :param object_name: string
    :param expiration: Time in seconds for the presigned URL to remain valid
    :return: Presigned URL as string. If error, returns None.
    """

    # Generate a presigned URL for the S3 object
    s3_client = boto3.client('s3')
    try:
        response = s3_client.generate_presigned_url('get_object',
                                                    Params={'Bucket': "shell-safe",
                                                            'Key': object_name},
                                                    ExpiresIn=expiration)
    except ClientError as e:
        logging.error(e)
        return None

    # The response contains the presigned URL
    return response

def img_with_presigned_url(artefact_image: ArtefactImage) -> ArtefactImage:
    '''Convert the "image_url" in the ArtefactImage from an S3 Object key (how
       it is stored in the DB) to a presigned URL suitable for the frontend to
       GET.
    '''
    return ArtefactImage(artefact_image.image_id,
                         artefact_image.image_id,
                         create_presigned_url(artefact_image.image_url),
                         artefact_image.image_description)

def create_family(family_name):


    # Generates random referral code
    

    salt = ''.join(random.choice(string.ascii_uppercase) for x in range(20))

    print(family_name)
    print(salt)

    referral_code = family_name + salt

    inputs = {"family_name": family_name,
              "referral_code": referral_code}

    
    ''' Creates a new family with the ''' 

        
    sql = '''INSERT INTO Family
             (name, referral_code)
             VALUES (%(family_name)s, %(referral_code)s)'''

    with psycopg2.connect(current_app.config['db_URL']) as conn:
        cur = conn.cursor()

        cur.execute(sql, inputs)

    return get_family_id(referral_code)

def get_family_id(referral_code):

    inputs = {"referral_code": referral_code}

    sql = '''SELECT family_id FROM family
             WHERE referral_code = %(referral_code)s
             LIMIT 1'''

    family_id = pg_select(sql, inputs)[0][0]

    print(family_id)

    return family_id