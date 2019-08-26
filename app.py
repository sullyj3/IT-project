from flask import Flask

import os

app = Flask(__name__)


@app.route('/')
def hello_world():
    return '🐢 Hello furious turtles! 🐢'

if __name__ == '__main__':
    db_URL = os.environ.get("DATABASE_URL")
    if db_URL is None:
        print("DATABASE_URL not found!")
    else:
        print(f"DATABASE_URL is '{db_URL}'")

    app.run()
