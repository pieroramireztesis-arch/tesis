import psycopg
from flask import g
from config import Config

def get_db():
    """
    Devuelve una única conexión a la BD por request.
    Usamos DATABASE_URL para que funcione tanto en local como en Render.
    """
    if "db_conn" not in g:
        if not Config.DATABASE_URL:
            raise RuntimeError("DATABASE_URL no está configurada")

        # En Render se requiere sslmode="require"
        g.db_conn = psycopg.connect(
            Config.DATABASE_URL,
            sslmode="require"
        )

    return g.db_conn


def close_db(e=None):
    db_conn = g.pop("db_conn", None)
    if db_conn is not None:
        db_conn.close()
