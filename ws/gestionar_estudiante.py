# ws/gestionar_estudiante.py

from flask import render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash

from db import get_db
from .docentes import bp_docentes  # usamos el mismo Blueprint


def _obtener_id_docente_desde_sesion():
    """
    Usa session['user_id'] para obtener id_docente.
    """
    if "user_id" not in session or session.get("user_rol") != "docente":
        return None

    id_usuario = session["user_id"]

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT id_docente FROM docente WHERE id_usuario = %s",
        (id_usuario,),
    )
    row = cur.fetchone()
    cur.close()

    if not row:
        return None

    return row[0]


@bp_docentes.route("/estudiantes")
def gestion_estudiantes():
    id_docente = _obtener_id_docente_desde_sesion()
    if id_docente is None:
        return redirect(url_for("auth.login"))

    conn = get_db()
    cur = conn.cursor()

    # ============================
    # Estudiantes de los salones
    # ============================
    cur.execute(
        """
        SELECT
            e.id_estudiante,
            u.id_usuario,
            u.nombre,
            u.apellidos,
            u.correo,
            e.grado,
            e.estado_estudiante,
            s.nombre_salon,
            COALESCE(e.operaciones_basicas, 0) AS comp_cantidad,
            COALESCE(e.ecuaciones, 0)          AS comp_regularidad,
            COALESCE(e.funciones, 0)           AS comp_forma,
            COALESCE(e.geometria, 0)           AS comp_datos,
            COALESCE(e.progreso_general, 0)    AS progreso_general
        FROM docente_salones ds
        JOIN salones s ON s.id_salon = ds.id_salon
        JOIN estudiante_salones es ON es.id_salon = s.id_salon
        JOIN estudiante e ON e.id_estudiante = es.id_estudiante
        JOIN usuarios u ON u.id_usuario = e.id_usuario
        WHERE ds.id_docente = %s
        ORDER BY u.apellidos, u.nombre
        """,
        (id_docente,),
    )
    rows = cur.fetchall()

    estudiantes = [
        {
            "id_estudiante": r[0],
            "id_usuario": r[1],
            "nombre": r[2],
            "apellidos": r[3],
            "correo": r[4],
            "grado": r[5],
            "estado_estudiante": r[6],
            "nombre_salon": r[7],
            "comp_cantidad": r[8],
            "comp_regularidad": r[9],
            "comp_forma": r[10],
            "comp_datos": r[11],
            "progreso_general": r[12],
            "nombre_completo": f"{r[2]} {r[3]}",
        }
        for r in rows
    ]

    # ============================
    # Usuarios que ya son alumnos
    # ============================
    cur.execute(
        """
        SELECT
            u.id_usuario,
            u.nombre,
            u.apellidos,
            u.correo,
            COALESCE(e.grado, '') AS grado
        FROM usuarios u
        LEFT JOIN estudiante e ON e.id_usuario = u.id_usuario
        WHERE u.rol = 'estudiante'
        ORDER BY u.apellidos, u.nombre
        """
    )
    usuarios_rows = cur.fetchall()
    usuarios_estudiantes = [
        {
            "id_usuario": r[0],
            "nombre": r[1],
            "apellidos": r[2],
            "correo": r[3],
            "grado": r[4],
            "nombre_completo": f"{r[1]} {r[2]}",
        }
        for r in usuarios_rows
    ]

    cur.close()

    return render_template(
        "docente_gestion_estudiantes.html",
        titulo_pagina="Gestión de Estudiantes",
        active_page="estudiantes",
        estudiantes=estudiantes,
        usuarios_estudiantes=usuarios_estudiantes,
    )


@bp_docentes.route("/estudiantes/nuevo", methods=["POST"])
def crear_estudiante():
    id_docente = _obtener_id_docente_desde_sesion()
    if id_docente is None:
        return redirect(url_for("auth.login"))

    # Puede venir un usuario ya existente
    id_usuario_existente = request.form.get("id_usuario_existente", type=int)

    nombre = request.form.get("nombre", "").strip()
    apellidos = request.form.get("apellidos", "").strip()
    correo = request.form.get("correo", "").strip().lower()
    grado = request.form.get("grado", "").strip()  # 3ro A, 3ro B, 3ro C
    contrasena = request.form.get("contrasena", "")
    contrasena_confirm = request.form.get("contrasena_confirm", "")

    conn = get_db()
    cur = conn.cursor()

    # Obtener un salón del docente (el primero)
    cur.execute(
        """
        SELECT id_salon
        FROM docente_salones
        WHERE id_docente = %s
        LIMIT 1
        """,
        (id_docente,),
    )
    row_salon = cur.fetchone()
    if not row_salon:
        flash(
            "No tienes salones asignados. No se puede crear el estudiante.",
            "error",
        )
        cur.close()
        return redirect(url_for("docentes.gestion_estudiantes"))

    id_salon = row_salon[0]

    # =========================================
    # OPCIÓN 1: usar usuario existente
    # =========================================
    if id_usuario_existente:
        # Verificar que exista y sea rol estudiante
        cur.execute(
            """
            SELECT id_usuario, nombre, apellidos, correo
            FROM usuarios
            WHERE id_usuario = %s AND rol = 'estudiante'
            """,
            (id_usuario_existente,),
        )
        u = cur.fetchone()
        if not u:
            flash("El usuario seleccionado no es válido.", "error")
            cur.close()
            return redirect(url_for("docentes.gestion_estudiantes"))

        # Ver si ya tiene registro en estudiante
        cur.execute(
            "SELECT id_estudiante FROM estudiante WHERE id_usuario = %s",
            (id_usuario_existente,),
        )
        row_est = cur.fetchone()
        if row_est:
            id_estudiante = row_est[0]
            # Actualizar grado
            cur.execute(
                "UPDATE estudiante SET grado = %s WHERE id_estudiante = %s",
                (grado, id_estudiante),
            )
        else:
            # Crear registro de estudiante
            cur.execute(
                """
                INSERT INTO estudiante (grado, id_usuario)
                VALUES (%s, %s)
                RETURNING id_estudiante
                """,
                (grado, id_usuario_existente),
            )
            id_estudiante = cur.fetchone()[0]

        # Asociar al salón si no está ya
        cur.execute(
            """
            SELECT 1
            FROM estudiante_salones
            WHERE id_estudiante = %s AND id_salon = %s
            """,
            (id_estudiante, id_salon),
        )
        if not cur.fetchone():
            cur.execute(
                """
                INSERT INTO estudiante_salones (id_estudiante, id_salon)
                VALUES (%s, %s)
                """,
                (id_estudiante, id_salon),
            )

        conn.commit()
        cur.close()
        flash("Estudiante asociado correctamente a tu salón.", "success")
        return redirect(url_for("docentes.gestion_estudiantes"))

    # =========================================
    # OPCIÓN 2: crear usuario nuevo
    # =========================================
    if not nombre or not apellidos or not correo or not contrasena:
        flash("Todos los campos obligatorios deben estar completos.", "error")
        cur.close()
        return redirect(url_for("docentes.gestion_estudiantes"))

    if contrasena != contrasena_confirm:
        flash("Las contraseñas no coinciden.", "error")
        cur.close()
        return redirect(url_for("docentes.gestion_estudiantes"))

    # Validar que el correo no exista
    cur.execute("SELECT id_usuario FROM usuarios WHERE correo = %s", (correo,))
    if cur.fetchone():
        flash("El correo ya está registrado.", "error")
        cur.close()
        return redirect(url_for("docentes.gestion_estudiantes"))

    # Crear usuario
    hash_pwd = generate_password_hash(contrasena)
    cur.execute(
        """
        INSERT INTO usuarios (nombre, apellidos, correo, contrasena, rol)
        VALUES (%s, %s, %s, %s, 'estudiante')
        RETURNING id_usuario
        """,
        (nombre, apellidos, correo, hash_pwd),
    )
    id_usuario = cur.fetchone()[0]

    # Crear estudiante (sin niveles iniciales por ahora)
    cur.execute(
        """
        INSERT INTO estudiante (grado, id_usuario)
        VALUES (%s, %s)
        RETURNING id_estudiante
        """,
        (grado, id_usuario),
    )
    id_estudiante = cur.fetchone()[0]

    # Asociar a salón del docente
    cur.execute(
        """
        INSERT INTO estudiante_salones (id_estudiante, id_salon)
        VALUES (%s, %s)
        """,
        (id_estudiante, id_salon),
    )

    conn.commit()
    cur.close()

    flash("Estudiante creado correctamente.", "success")
    return redirect(url_for("docentes.gestion_estudiantes"))


@bp_docentes.route("/estudiantes/<int:id_estudiante>/editar", methods=["POST"])
def editar_estudiante(id_estudiante):
    if "user_id" not in session or session.get("user_rol") != "docente":
        return redirect(url_for("auth.login"))

    id_usuario = request.form.get("id_usuario", type=int)
    nombre = request.form.get("nombre", "").strip()
    apellidos = request.form.get("apellidos", "").strip()
    correo = request.form.get("correo", "").strip().lower()
    grado = request.form.get("grado", "").strip()
    estado_estudiante = request.form.get("estado_estudiante", "activo").strip().lower()
    contrasena = request.form.get("contrasena", "")
    contrasena_confirm = request.form.get("contrasena_confirm", "")

    # Niveles diagnósticos por competencia (0..100)
    def _parse_int(name):
        val = request.form.get(name, "").strip()
        if not val:
            return None
        try:
            n = int(val)
            return max(0, min(100, n))
        except ValueError:
            return None

    comp_cantidad = _parse_int("comp_cantidad")
    comp_regularidad = _parse_int("comp_regularidad")
    comp_forma = _parse_int("comp_forma")
    comp_datos = _parse_int("comp_datos")

    if not nombre or not apellidos or not correo:
        flash("Nombre, apellidos y correo son obligatorios.", "error")
        return redirect(url_for("docentes.gestion_estudiantes"))

    if contrasena or contrasena_confirm:
        if contrasena != contrasena_confirm:
            flash("Las contraseñas no coinciden.", "error")
            return redirect(url_for("docentes.gestion_estudiantes"))

    # Progreso general manual (promedio de las competencias ingresadas)
    valores = [
        v for v in [comp_cantidad, comp_regularidad, comp_forma, comp_datos]
        if v is not None
    ]
    progreso_general = int(round(sum(valores) / len(valores))) if valores else None

    conn = get_db()
    cur = conn.cursor()

    # Validar correo único
    cur.execute(
        "SELECT id_usuario FROM usuarios WHERE correo = %s AND id_usuario <> %s",
        (correo, id_usuario),
    )
    if cur.fetchone():
        flash("El correo ya está registrado por otro usuario.", "error")
        cur.close()
        return redirect(url_for("docentes.gestion_estudiantes"))

    # Actualizar usuario
    cur.execute(
        """
        UPDATE usuarios
        SET nombre = %s, apellidos = %s, correo = %s
        WHERE id_usuario = %s
        """,
        (nombre, apellidos, correo, id_usuario),
    )

    # Actualizar estudiante + niveles iniciales
    cur.execute(
        """
        UPDATE estudiante
        SET grado = %s,
            estado_estudiante = %s,
            operaciones_basicas = COALESCE(%s, operaciones_basicas),
            ecuaciones          = COALESCE(%s, ecuaciones),
            funciones           = COALESCE(%s, funciones),
            geometria           = COALESCE(%s, geometria),
            progreso_general    = COALESCE(%s, progreso_general)
        WHERE id_estudiante = %s
        """,
        (
            grado,
            estado_estudiante,
            comp_cantidad,
            comp_regularidad,
            comp_forma,
            comp_datos,
            progreso_general,
            id_estudiante,
        ),
    )

    # Actualizar contraseña si corresponde
    if contrasena:
        hash_pwd = generate_password_hash(contrasena)
        cur.execute(
            "UPDATE usuarios SET contrasena = %s WHERE id_usuario = %s",
            (hash_pwd, id_usuario),
        )

    conn.commit()
    cur.close()

    flash("Estudiante actualizado correctamente.", "success")
    return redirect(url_for("docentes.gestion_estudiantes"))


@bp_docentes.route("/estudiantes/<int:id_estudiante>/baja", methods=["POST"])
def baja_estudiante(id_estudiante):
    if "user_id" not in session or session.get("user_rol") != "docente":
        return redirect(url_for("auth.login"))

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "UPDATE estudiante SET estado_estudiante = 'inactivo' WHERE id_estudiante = %s",
        (id_estudiante,),
    )
    conn.commit()
    cur.close()

    flash("Estudiante dado de baja.", "success")
    return redirect(url_for("docentes.gestion_estudiantes"))
