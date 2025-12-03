# db.py
import psycopg
from flask import current_app, g

def get_db():
    """
    Devuelve una única conexión a la BD por request.
    Las filas se devuelven como TUPLAS (comportamiento clásico),
    para que funcione todo el código que usa row[0], row[1], etc.
    """
    if "db_conn" not in g:
        g.db_conn = psycopg.connect(
            host=current_app.config["DB_HOST"],
            port=current_app.config["DB_PORT"],
            dbname=current_app.config["DB_NAME"],
            user=current_app.config["DB_USER"],
            password=current_app.config["DB_PASSWORD"],
        )
    return g.db_conn


def close_db(e=None):
    db_conn = g.pop("db_conn", None)
    if db_conn is not None:
        db_conn.close()
