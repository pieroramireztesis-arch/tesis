import os

class Config:
    # Clave secreta para Flask (úsala desde variables de entorno en Render)
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-key")

    # URL completa de la base de datos (Render: DATABASE_URL)
    DATABASE_URL = os.environ.get("DATABASE_URL")

    # Configuración de correo (idealmente también en variables de entorno)
    MAIL_SERVER = "smtp.gmail.com"
    MAIL_PORT = 465
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "ww.sco.lol@gmail.com")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "hgzm kujp blfu sczr")
    MAIL_DEFAULT_SENDER = MAIL_USERNAME
