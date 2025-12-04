import os

class Config:
    # ============================
    #  🔐 Clave de sesión de Flask
    # ============================
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-key")

    # ===========================================
    #  🔗 Cadena de conexión a la base de datos
    #  En local usa el valor por defecto.
    #  En Render usa la variable DATABASE_URL
    # ===========================================
    DATABASE_URL = os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:hola1@localhost:5432/bd_ejemplo"
    )

    # ============================
    #  📧 Configuración de correo
    # ============================
    MAIL_SERVER = "smtp.gmail.com"
    MAIL_PORT = 465
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "ww.sco.lol@gmail.com")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "hgzm kujp blfu sczr")
    MAIL_DEFAULT_SENDER = MAIL_USERNAME
