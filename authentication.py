from model import Credentials

from flask import current_app
from flask_bcrypt import check_password_hash, generate_password_hash



def authenticate_user(credentials: Credentials, pw_hash):

    
    return check_password_hash(pw_hash.tobytes(), credentials.password)


def test_password(plaintext, pw_hash):
    
    return check_password_hash(pw_hash, plaintext)

def generate_pass(plaintext):

    return generate_password_hash(plaintext)