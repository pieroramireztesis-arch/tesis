import os
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, session, flash
)
from db import get_db
from werkzeug.utils import secure_filename

bp_perfil = Blueprint("perfil", __name__, url_prefix="/docente/perfil")

UPLOAD_FOLDER = "static/fotos_perfil"
ALLOWED = {"jpg", "jpeg", "png"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED


@bp_perfil.route("/")
def ver_perfil():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT nombre, apellidos, correo, foto_perfil
        FROM usuarios WHERE id_usuario=%s
    """, (session["user_id"],))

    datos = cur.fetchone()
    cur.close()

    return render_template(
        "docente_perfil.html",
        datos=datos,
        titulo_pagina="Perfil del Profesor",
        active_page="perfil"
    )


@bp_perfil.route("/actualizar", methods=["POST"])
def actualizar_perfil():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    archivo = request.files.get("foto")

    conn = get_db()
    cur = conn.cursor()

    if archivo and allowed_file(archivo.filename):
        filename = f"user_{session['user_id']}.jpg"
        ruta = os.path.join(UPLOAD_FOLDER, filename)
        archivo.save(ruta)

        url_foto = f"/static/fotos_perfil/{filename}"
        cur.execute("""
            UPDATE usuarios SET foto_perfil=%s
            WHERE id_usuario=%s
        """, (url_foto, session["user_id"]))

    conn.commit()
    cur.close()

    flash("Foto de perfil actualizada", "success")
    return redirect(url_for("perfil.ver_perfil"))
