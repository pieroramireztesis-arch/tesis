from flask import Flask, jsonify, redirect, url_for
from config import Config
from db import get_db, close_db
from ws import register_blueprints

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    app.teardown_appcontext(close_db)
    register_blueprints(app)

    @app.route("/ping-db")
    def ping_db():
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()[0]
        cur.close()
        return jsonify({"db_version": version})

    @app.route("/")
    def index():
        return redirect(url_for("auth.login"))

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
