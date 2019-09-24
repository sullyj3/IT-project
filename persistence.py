import psycopg2
from typing import List, Tuple

from model import Artefact, Credentials, Register

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

''' Determines if an email is taken in the database '''
def email_available(credentials: Credentials):
    
    sql = "SELECT *\
        FROM 'User'\
        WHERE email=%s\
        LIMIT 1"

    # Returns user, if none with email returns None
    with psycopg2.connect(current_app.cofig['db_URL']) as conn:
        cur = conn.cursor()
        cur.execute(sql, (credentials.email))
        return cur.fetchone()
    # test email: hello@hello.com


''' Adds new user to the Database '''
def register_user(register: Register):

    with psycopg2.connect(current_app.config['db_URL']) as conn:
        cur = conn.cursor()
        sql = '''INSERT INTO "Users"
                 (first_name, surname, email, password, location, family_id)
                 VALUES (%(first_name)s, %(surname)s, %(email)s, %(password)s, %(location)s, %(family_id)s)'''

