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

def generate_img_filename(user_id: str, img: FileStorage):
    name, ext = img.filename.rsplit('.',1)
    timestamp = datetime.utcnow().isoformat().replace(":", "_")
    return f'{user_id}-{name}-{timestamp}.{ext}'
