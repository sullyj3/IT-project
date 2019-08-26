import os

from flask import Flask
import psycopg2

app = Flask(__name__)


@app.route('/')
def hello_world():
    return '🐢 Hello furious turtles! 🐢'

def print_dummy_data(conn) -> None:
    cur = conn.cursor()
    cur.execute('SELECT * FROM ITProjectTestTable;')
    data = cur.fetchall()

    print("\ndummy data:")
    for id, text in data:
        print(id, text)
    print()

if __name__ == '__main__':
    db_URL = os.environ.get("DATABASE_URL")
    if db_URL is None:
        print("DATABASE_URL not found!")
    else:
        print(f"DATABASE_URL is '{db_URL}'")

    conn = psycopg2.connect(db_URL)
    print(f"Successfully connected to the database!")
    print_dummy_data(conn)

    app.run()
