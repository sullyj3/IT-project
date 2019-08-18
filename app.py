from flask import Flask

import os

app = Flask(__name__)


@app.route('/')
def hello_world():
    return 'Hello World!'

def get_port() -> int:
    try:
        return os.environ['PORT']
    except KeyError as e:
        DEFAULT_PORT = 5000
        print(f'PORT environment variable not found, using fallback {DEFAULT_PORT}')
        return DEFAULT_PORT

if __name__ == '__main__':
    app.run(port=get_port())
