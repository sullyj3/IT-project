from model import Credentials

from flask import current_app
from flask_bcrypt import check_password_hash, generate_password_hash


def authenticate_user(credentials: Credentials, pw_hash):

    print()
    print(pw_hash)
    print()

    if check_password_hash(pw_hash.tobytes(), credentials.password):
        return "password correct 😎"
    else:
        return "wrong password 😖"


def test_password(plaintext, pw_hash):
    
    return check_password_hash(pw_hash, plaintext)

def generate_pass(plaintext):

    return generate_password_hash(plaintext)