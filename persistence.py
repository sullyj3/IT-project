from typing import List, Tuple
from datetime import datetime

from flask import current_app
from werkzeug.datastructures import FileStorage
import psycopg2

import boto3

from model import Artefact, Credentials, Register, ArtefactImage

############
# Database #
############

'''
    sql: A select statement
'''
def pg_select(sql: str, select_what=None) -> List[Tuple]:
    try:
        conn = psycopg2.connect(current_app.config['db_URL'])
    except e:
        print("couldn't connect to " + current_app.config['db_URL'])
        raise e

    with conn:
        cur = conn.cursor()
        if select_what is not None:
            cur.execute(sql, select_what)
        else:
            cur.execute(sql)

        return cur.fetchall()


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

