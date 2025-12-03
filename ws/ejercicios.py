import os
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    session,
)
from werkzeug.utils import secure_filename
from db import get_db

bp_ejercicios = Blueprint("ejercicios", __name__, url_prefix="/docente/ejercicios")

UPLOAD_FOLDER = "static/ejercicios_ayuda"
ALLOWED = {"png", "jpg", "jpeg"}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED


# ===================== LISTADO =====================
@bp_ejercicios.route("/")
def gestion_ejercicios():
    # 🔒 Solo docentes
    if "user_id" not in session or session.get("user_rol") != "docente":
        return redirect(url_for("auth.login"))

    conn = get_db()
    cur = conn.cursor()

    # Ejercicios con su competencia
    cur.execute(
        """
        SELECT 
            e.id_ejercicio,       -- 0
            e.descripcion,        -- 1
            e.id_competencia,     -- 2
            c.descripcion AS nombre_competencia  -- 3
        FROM ejercicios e
        JOIN competencias c ON c.id_competencia = e.id_competencia
        ORDER BY e.id_ejercicio DESC
        """
    )
    filas_ej = cur.fetchall()

    ejercicios = [
        {
            "id_ejercicio": f[0],
            "descripcion": f[1],
            "id_competencia": f[2],
            "nombre_competencia": f[3],
        }
        for f in filas_ej
    ]

    # Lista de competencias para los combos
    cur.execute(
        """
        SELECT id_competencia, area
        FROM competencias
        ORDER BY area
        """
    )
    filas_comp = cur.fetchall()
    competencias = [
        {"id_competencia": f[0], "area": f[1]}
        for f in filas_comp
    ]

    cur.close()

    return render_template(
        "docente_gestion_ejercicios.html",
        ejercicios=ejercicios,
        competencias=competencias,
        titulo_pagina="Gestión de Ejercicios",
        active_page="ejercicios",
    )


# ===================== CREAR / ACTUALIZAR =====================
@bp_ejercicios.route("/crear", methods=["POST"])
def crear_ejercicio():
    """
    Si viene id_ejercicio vacío -> INSERT (nuevo ejercicio)
    Si viene id_ejercicio con valor -> UPDATE (editar ejercicio)
    """
    if "user_id" not in session or session.get("user_rol") != "docente":
        return redirect(url_for("auth.login"))

    id_ejercicio_raw = request.form.get("id_ejercicio", "").strip()
    descripcion = request.form.get("descripcion", "").strip()
    respuesta = request.form.get("opcion_correcta")  # letra A/B/C/D
    id_competencia = request.form.get("id_competencia")
    pista = request.form.get("pista", "").strip()
    archivo = request.files.get("imagen_ejercicio")  # nombre del input del HTML

    if not descripcion or not id_competencia:
        flash("Ingresa al menos la descripción y la competencia.", "danger")
        return redirect(url_for("ejercicios.gestion_ejercicios"))

    conn = get_db()
    cur = conn.cursor()

    # ¿INSERT o UPDATE?
    es_update = bool(id_ejercicio_raw)
    id_ej = None

    try:
        if es_update:
            id_ej = int(id_ejercicio_raw)
            cur.execute(
                """
                UPDATE ejercicios
                SET descripcion = %s,
                    respuesta_correcta = %s,
                    id_competencia = %s,
                    pista = %s
                WHERE id_ejercicio = %s
                """,
                (descripcion, respuesta, id_competencia, pista, id_ej),
            )
        else:
            cur.execute(
                """
                INSERT INTO ejercicios (descripcion, respuesta_correcta, id_competencia, pista)
                VALUES (%s, %s, %s, %s)
                RETURNING id_ejercicio
                """,
                (descripcion, respuesta, id_competencia, pista),
            )
            fila = cur.fetchone()
            id_ej = fila[0]

        # ---------- Guardar imagen si viene (para nuevo o editado) ----------
        if archivo and allowed_file(archivo.filename):
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)

            filename = secure_filename(f"ej_{id_ej}.jpg")
            ruta = os.path.join(UPLOAD_FOLDER, filename)
            archivo.save(ruta)

            img_url = f"/static/ejercicios_ayuda/{filename}"
            cur.execute(
                "UPDATE ejercicios SET imagen_url = %s WHERE id_ejercicio = %s",
                (img_url, id_ej),
            )

        # ---------- GUARDAR OPCIONES A–D EN LA TABLA opciones_ejercicio ----------
        # Borrar opciones anteriores si es UPDATE (o por seguridad en nuevo)
        cur.execute(
            "DELETE FROM opciones_ejercicio WHERE id_ejercicio = %s",
            (id_ej,),
        )

        opciones = {
            "A": request.form.get("opcion_A", "").strip(),
            "B": request.form.get("opcion_B", "").strip(),
            "C": request.form.get("opcion_C", "").strip(),
            "D": request.form.get("opcion_D", "").strip(),
        }

        respuesta_correcta = respuesta  # letra A/B/C/D

        for letra, texto in opciones.items():
            if texto != "":
                cur.execute(
                    """
                    INSERT INTO opciones_ejercicio (letra, descripcion, es_correcta, id_ejercicio)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        letra,
                        texto,
                        letra == respuesta_correcta,
                        id_ej,
                    ),
                )

        # ---------- COMMIT ----------
        conn.commit()

        if es_update:
            flash("Ejercicio actualizado correctamente.", "success")
        else:
            flash("Ejercicio creado correctamente.", "success")

    except Exception as e:
        conn.rollback()
        print("ERROR crear/actualizar ejercicio:", e)
        flash("Ocurrió un error al guardar el ejercicio.", "danger")
    finally:
        cur.close()

    return redirect(url_for("ejercicios.gestion_ejercicios"))


# ===================== ELIMINAR =====================
@bp_ejercicios.route("/eliminar/<int:id_ejercicio>", methods=["POST"])
def eliminar_ejercicio(id_ejercicio):
    if "user_id" not in session or session.get("user_rol") != "docente":
        return redirect(url_for("auth.login"))

    conn = get_db()
    cur = conn.cursor()

    try:
        # Borrar opciones asociadas
        cur.execute(
            "DELETE FROM opciones_ejercicio WHERE id_ejercicio = %s",
            (id_ejercicio,),
        )

        # Borrar imagen si existe
        ruta = os.path.join(UPLOAD_FOLDER, f"ej_{id_ejercicio}.jpg")
        if os.path.exists(ruta):
            os.remove(ruta)

        # Borrar ejercicio
        cur.execute("DELETE FROM ejercicios WHERE id_ejercicio = %s", (id_ejercicio,))
        conn.commit()
        flash("Ejercicio eliminado.", "success")
    except Exception as e:
        conn.rollback()
        print("ERROR eliminar ejercicio:", e)
        flash("No se pudo eliminar el ejercicio.", "danger")
    finally:
        cur.close()

    return redirect(url_for("ejercicios.gestion_ejercicios"))


# ===================== DETALLE JSON (para EDITAR) =====================
@bp_ejercicios.route("/detalle/<int:id_ejercicio>")
def detalle_ejercicio_json(id_ejercicio):
    """
    Devuelve un JSON con los datos del ejercicio para rellenar el formulario
    de edición rápida mediante fetch().
    """
    if "user_id" not in session or session.get("user_rol") != "docente":
        return jsonify({"error": "No autorizado"}), 401

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT 
            id_ejercicio,       -- 0
            descripcion,        -- 1
            id_competencia,     -- 2
            respuesta_correcta, -- 3
            pista               -- 4
        FROM ejercicios
        WHERE id_ejercicio = %s
        """,
        (id_ejercicio,),
    )
    ej = cur.fetchone()
    cur.close()

    if not ej:
        return jsonify({"error": "Ejercicio no encontrado"}), 404

    data = {
        "id_ejercicio": ej[0],
        "descripcion": ej[1],
        "id_competencia": ej[2],
        "respuesta_correcta": ej[3],
        "pista": ej[4],
        "opciones": {},  # si luego quieres, aquí se puede devolver también las opciones
    }

    return jsonify(data)
