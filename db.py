import os
import psycopg
from flask import g
from config import Config


def get_db():
    """
    Devuelve una única conexión a la BD por request.

    - En LOCAL: se usa la cadena por defecto de Config.DATABASE_URL
      sin SSL.
    - En RENDER (o nube): si existe la variable de entorno DATABASE_URL,
      se conecta con sslmode='require'.
    """
    if "db_conn" not in g:
        # ¿Hay DATABASE_URL en variables de entorno? (Render / producción)
        db_url_env = os.environ.get("DATABASE_URL")

        if db_url_env:
            # Modo nube (Render): usa SSL
            g.db_conn = psycopg.connect(db_url_env, sslmode="require")
        else:
            # Modo local: usa la URL por defecto SIN SSL
            if not Config.DATABASE_URL:
                raise RuntimeError("DATABASE_URL no está configurada")
            g.db_conn = psycopg.connect(Config.DATABASE_URL)

    return g.db_conn


def close_db(e=None):
    db_conn = g.pop("db_conn", None)
    if db_conn is not None:
        db_conn.close()
