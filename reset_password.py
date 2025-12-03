# reset_passwords.py
# Script para poner una nueva contraseña ENCRIPTADA
# a todos los usuarios existentes en la tabla "usuarios".

from config import Config
import psycopg
from werkzeug.security import generate_password_hash


def main():
    # 1. Define aquí la nueva contraseña temporal que tendrán todos
    NUEVA_PASSWORD_PLANA = "hola1"   # ← puedes cambiarla si quieres

    # 2. Crear el hash con werkzeug (mismo método que usa auth.py)
    hash_contra = generate_password_hash(NUEVA_PASSWORD_PLANA)
    print("Hash generado:", hash_contra)

    # 3. Conexión a la BD usando tu Config
    conn = psycopg.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        dbname=Config.DB_NAME,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
    )

    cur = conn.cursor()

    # 4. Actualizar TODAS las contraseñas
    cur.execute(
        """
        UPDATE usuarios
        SET contrasena = %s
        """,
        (hash_contra,),
    )

    conn.commit()
    cur.close()
    conn.close()

    print("Todas las contraseñas fueron actualizadas correctamente.")
    print(f"Ahora TODOS los usuarios pueden entrar con: {NUEVA_PASSWORD_PLANA}")


if __name__ == "__main__":
    main()
