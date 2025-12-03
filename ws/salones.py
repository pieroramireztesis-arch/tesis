from flask import (
    Blueprint,
    render_template,
    session,
    redirect,
    url_for,
    request,
    flash,
)
from db import get_db

bp_salones = Blueprint("salones", __name__, url_prefix="/docente/salones")


# ---------------------------------------------
# UTILIDAD: obtener id_docente desde sesión
# ---------------------------------------------
def get_id_docente_from_session():
    if "user_id" not in session or session.get("user_rol") != "docente":
        return None

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT id_docente FROM docente WHERE id_usuario = %s",
        (session["user_id"],),
    )
    row = cur.fetchone()
    cur.close()

    return row[0] if row else None


# ---------------------------------------------
# LISTAR SALONES
# ---------------------------------------------
@bp_salones.route("/")
def gestion_salones():
    id_docente = get_id_docente_from_session()
    if not id_docente:
        return redirect(url_for("auth.login"))

    conn = get_db()
    cur = conn.cursor()

    # Salones del docente
    cur.execute(
        """
        SELECT 
            s.id_salon,
            s.nombre_salon,
            s.grado,
            (
                SELECT COUNT(*)
                FROM estudiante_salones es
                WHERE es.id_salon = s.id_salon
            ) AS num_estudiantes
        FROM salones s
        JOIN docente_salones ds ON ds.id_salon = s.id_salon
        WHERE ds.id_docente = %s
        ORDER BY s.nombre_salon ASC
        """,
        (id_docente,),
    )
    salones_rows = cur.fetchall()

    # Salones disponibles para unirse (todos los que NO tiene este docente)
    cur.execute(
        """
        SELECT s.id_salon, s.nombre_salon, s.grado
        FROM salones s
        WHERE s.id_salon NOT IN (
            SELECT id_salon
            FROM docente_salones
            WHERE id_docente = %s
        )
        ORDER BY s.nombre_salon ASC
        """,
        (id_docente,),
    )
    disponibles_rows = cur.fetchall()

    cur.close()

    salones = [
        {
            "id_salon": row[0],
            "nombre_salon": row[1],
            "grado": row[2],
            "num_estudiantes": row[3],
        }
        for row in salones_rows
    ]

    salones_disponibles = [
        {
            "id_salon": row[0],
            "nombre_salon": row[1],
            "grado": row[2],
        }
        for row in disponibles_rows
    ]

    return render_template(
        "docente_gestion_salones.html",
        titulo_pagina="Administración de Salones",
        active_page="salones",
        salones=salones,
        salones_disponibles=salones_disponibles,
    )


# ---------------------------------------------
# CREAR SALÓN
# ---------------------------------------------
@bp_salones.route("/crear", methods=["POST"])
def crear_salon():
    id_docente = get_id_docente_from_session()
    if not id_docente:
        return redirect(url_for("auth.login"))

    nombre_salon = request.form.get("nombre_salon", "").strip()
    grado = request.form.get("grado", "").strip()

    if not nombre_salon or not grado:
        flash("Todos los campos son obligatorios.", "danger")
        return redirect(url_for("salones.gestion_salones"))

    conn = get_db()
    cur = conn.cursor()

    # 1) Insertar salón
    cur.execute(
        """
        INSERT INTO salones (nombre_salon, grado)
        VALUES (%s, %s)
        RETURNING id_salon
        """,
        (nombre_salon, grado),
    )
    id_salon = cur.fetchone()[0]

    # 2) Asignar salón al docente
    cur.execute(
        """
        INSERT INTO docente_salones (id_docente, id_salon)
        VALUES (%s, %s)
        """,
        (id_docente, id_salon),
    )

    conn.commit()
    cur.close()

    flash("Salón creado correctamente.", "success")
    return redirect(url_for("salones.gestion_salones"))


# ---------------------------------------------
# EDITAR SALÓN
# ---------------------------------------------
@bp_salones.route("/editar/<int:id_salon>", methods=["POST"])
def editar_salon(id_salon):
    id_docente = get_id_docente_from_session()
    if not id_docente:
        return redirect(url_for("auth.login"))

    nombre_salon = request.form.get("nombre_salon", "").strip()
    grado = request.form.get("grado", "").strip()

    if not nombre_salon or not grado:
        flash("Todos los campos son obligatorios.", "danger")
        return redirect(url_for("salones.gestion_salones"))

    conn = get_db()
    cur = conn.cursor()

    # Verificar que este salón pertenece al docente
    cur.execute(
        """
        SELECT 1 FROM docente_salones
        WHERE id_docente = %s AND id_salon = %s
        """,
        (id_docente, id_salon),
    )
    if not cur.fetchone():
        flash("No tienes permiso para editar este salón.", "danger")
        return redirect(url_for("salones.gestion_salones"))

    # Actualizar datos
    cur.execute(
        """
        UPDATE salones
        SET nombre_salon = %s,
            grado = %s
        WHERE id_salon = %s
        """,
        (nombre_salon, grado, id_salon),
    )

    conn.commit()
    cur.close()

    flash("Salón actualizado.", "success")
    return redirect(url_for("salones.gestion_salones"))


# ---------------------------------------------
# ELIMINAR SALÓN
# ---------------------------------------------
@bp_salones.route("/eliminar/<int:id_salon>", methods=["POST"])
def eliminar_salon(id_salon):
    id_docente = get_id_docente_from_session()
    if not id_docente:
        return redirect(url_for("auth.login"))

    conn = get_db()
    cur = conn.cursor()

    # Verificar que el salón le pertenece
    cur.execute(
        """
        SELECT 1 FROM docente_salones
        WHERE id_docente = %s AND id_salon = %s
        """,
        (id_docente, id_salon),
    )
    if not cur.fetchone():
        flash("No puedes eliminar este salón.", "danger")
        return redirect(url_for("salones.gestion_salones"))

    # Eliminar relaciones estudiante-salon
    cur.execute(
        """
        DELETE FROM estudiante_salones
        WHERE id_salon = %s
        """,
        (id_salon,),
    )

    # Eliminar relación docente-salon
    cur.execute(
        """
        DELETE FROM docente_salones
        WHERE id_salon = %s
        """,
        (id_salon,),
    )

    # Finalmente eliminar el salón
    cur.execute(
        """
        DELETE FROM salones
        WHERE id_salon = %s
        """,
        (id_salon,),
    )

    conn.commit()
    cur.close()

    flash("Salón eliminado correctamente.", "success")
    return redirect(url_for("salones.gestion_salones"))


# ---------------------------------------------
# UNIRSE A UN SALÓN EXISTENTE
# ---------------------------------------------
@bp_salones.route("/unirse", methods=["POST"])
def unirse_salon():
    id_docente = get_id_docente_from_session()
    if not id_docente:
        return redirect(url_for("auth.login"))

    id_salon = request.form.get("id_salon", "").strip()

    if not id_salon:
        flash("Debes seleccionar un salón.", "danger")
        return redirect(url_for("salones.gestion_salones"))

    conn = get_db()
    cur = conn.cursor()

    try:
        # 1. Verificar que el salón exista
        cur.execute("SELECT 1 FROM salones WHERE id_salon = %s", (id_salon,))
        if not cur.fetchone():
            flash("No existe un salón con ese código.", "danger")
            return redirect(url_for("salones.gestion_salones"))

        # 2. Verificar que el docente no esté ya asignado
        cur.execute(
            """
            SELECT 1
            FROM docente_salones
            WHERE id_docente = %s AND id_salon = %s
            """,
            (id_docente, id_salon),
        )
        if cur.fetchone():
            flash("Ya estás asignado a este salón.", "info")
            return redirect(url_for("salones.gestion_salones"))

        # 3. Insertar relación
        cur.execute(
            """
            INSERT INTO docente_salones (id_docente, id_salon)
            VALUES (%s, %s)
            """,
            (id_docente, id_salon),
        )
        conn.commit()
        flash("Te uniste al salón correctamente.", "success")

    except Exception as e:
        conn.rollback()
        print("ERROR UNIRSE SALON:", e)
        flash("Ocurrió un error al unirte al salón.", "danger")
    finally:
        cur.close()

    return redirect(url_for("salones.gestion_salones"))
