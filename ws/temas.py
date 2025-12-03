# ws/temas.py
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

bp_temas = Blueprint("temas", __name__, url_prefix="/docente/temas")

# IDs de las 4 competencias base del MINEDU (ajusta si tus IDs son otros)
BASE_COMPETENCIAS_IDS = {1, 2, 3, 4}


# ================= LISTAR TEMAS Y MATERIALES =================
@bp_temas.route("/", methods=["GET"])
def gestion_temas():
    """
    Muestra la pantalla de Gestión de Temas.
    Opcionalmente puede filtrar por:
      - id_competencia -> tema seleccionado
      - nivel_filtro   -> nivel de materiales (1,2,3) o todos
    """

    if "user_id" not in session or session.get("user_rol") != "docente":
        return redirect(url_for("auth.login"))

    conn = get_db()
    cur = conn.cursor()

    # ---- filtro de tema ----
    id_comp_raw = request.args.get("id_competencia")
    filtro_comp = None
    if id_comp_raw:
        try:
            filtro_comp = int(id_comp_raw)
        except ValueError:
            filtro_comp = None

    # ---- filtro de nivel de materiales ----
    nivel_filtro_raw = request.args.get("nivel_filtro", "").strip()
    nivel_filtro = None
    if nivel_filtro_raw in ("1", "2", "3"):
        nivel_filtro = int(nivel_filtro_raw)

    # ---- lista de competencias ----
    cur.execute(
        """
        SELECT id_competencia, area, descripcion, nivel
        FROM competencias
        ORDER BY id_competencia
        """
    )
    rows = cur.fetchall()

    temas = [
        {
            "id_competencia": r[0],
            "area": r[1],
            "descripcion": r[2],
            "nivel": r[3],
        }
        for r in rows
    ]

    # ---- tema activo ----
    tema_activo = None
    if filtro_comp is not None:
        for t in temas:
            if t["id_competencia"] == filtro_comp:
                tema_activo = t
                break
    else:
        if temas:
            tema_activo = temas[0]

    # ---- materiales del tema activo ----
    materiales = []
    if tema_activo:
        sql = """
            SELECT id_material, titulo, tipo, url, tiempo_estimado, nivel
            FROM material_estudio
            WHERE id_competencia = %s
        """
        params = [tema_activo["id_competencia"]]

        # si hay nivel_filtro, filtramos por ese nivel
        if nivel_filtro in (1, 2, 3):
            sql += " AND nivel = %s"
            params.append(nivel_filtro)

        sql += " ORDER BY id_material"
        cur.execute(sql, params)

        mat_rows = cur.fetchall()
        materiales = [
            {
                "id_material": m[0],
                "titulo": m[1],
                "tipo": m[2],
                "url": m[3],
                "tiempo_estimado": m[4],
                "nivel": m[5],
            }
            for m in mat_rows
        ]

    cur.close()

    return render_template(
        "docente_gestion_temas.html",
        temas=temas,
        tema_activo=tema_activo,
        materiales=materiales,
        base_competencias_ids=BASE_COMPETENCIAS_IDS,
        nivel_filtro=nivel_filtro,
        titulo_pagina="Gestión de Temas de Álgebra",
        active_page="temas",
    )


# ================= CREAR NUEVO TEMA =================
@bp_temas.route("/nuevo", methods=["POST"])
def crear_tema():
    if "user_id" not in session or session.get("user_rol") != "docente":
        return redirect(url_for("auth.login"))

    titulo = (request.form.get("titulo_tema") or "").strip()
    descripcion = (request.form.get("descripcion_tema") or "").strip()
    nivel_str = request.form.get("nivel_tema", "1")

    try:
        nivel = int(nivel_str)
    except ValueError:
        nivel = 1

    if nivel not in (1, 2, 3):
        nivel = 1

    if not titulo:
        flash("El título del tema es obligatorio.", "error")
        return redirect(url_for("temas.gestion_temas"))

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO competencias (descripcion, area, nivel)
        VALUES (%s, %s, %s)
        RETURNING id_competencia
        """,
        (descripcion, titulo, nivel),
    )
    nuevo_id = cur.fetchone()[0]
    conn.commit()
    cur.close()

    flash("Tema creado correctamente.", "success")
    return redirect(url_for("temas.gestion_temas", id_competencia=nuevo_id))


# ================= ACTUALIZAR TEMA =================
@bp_temas.route("/<int:id_competencia>/actualizar", methods=["POST"])
def actualizar_tema(id_competencia):
    if "user_id" not in session or session.get("user_rol") != "docente":
        return redirect(url_for("auth.login"))

    titulo = (request.form.get("titulo_tema") or "").strip()
    descripcion = (request.form.get("descripcion_tema") or "").strip()
    nivel_str = request.form.get("nivel_tema", "1")

    try:
        nivel = int(nivel_str)
    except ValueError:
        nivel = 1

    if nivel not in (1, 2, 3):
        nivel = 1

    if not titulo:
        flash("El título del tema es obligatorio.", "error")
        return redirect(url_for("temas.gestion_temas", id_competencia=id_competencia))

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE competencias
        SET area = %s,
            descripcion = %s,
            nivel = %s
        WHERE id_competencia = %s
        """,
        (titulo, descripcion, nivel, id_competencia),
    )
    conn.commit()
    cur.close()

    flash("Tema actualizado correctamente.", "success")
    return redirect(url_for("temas.gestion_temas", id_competencia=id_competencia))


# ================= ELIMINAR TEMA =================
@bp_temas.route("/<int:id_competencia>/eliminar", methods=["POST"])
def eliminar_tema(id_competencia):
    if "user_id" not in session or session.get("user_rol") != "docente":
        return redirect(url_for("auth.login"))

    if id_competencia in BASE_COMPETENCIAS_IDS:
        flash(
            "Este tema forma parte de las competencias base del MINEDU y no puede eliminarse.",
            "error",
        )
        return redirect(url_for("temas.gestion_temas", id_competencia=id_competencia))

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT COUNT(*) FROM material_estudio WHERE id_competencia = %s",
        (id_competencia,),
    )
    tiene_materiales = cur.fetchone()[0] > 0

    if tiene_materiales:
        cur.close()
        flash(
            "No se puede eliminar un tema que tiene materiales asociados. "
            "Elimina los materiales primero.",
            "error",
        )
        return redirect(url_for("temas.gestion_temas", id_competencia=id_competencia))

    cur.execute(
        "DELETE FROM competencias WHERE id_competencia = %s",
        (id_competencia,),
    )
    conn.commit()
    cur.close()

    flash("Tema eliminado correctamente.", "success")
    return redirect(url_for("temas.gestion_temas"))


# ================= CREAR MATERIAL =================
@bp_temas.route("/<int:id_competencia>/material/nuevo", methods=["POST"])
def crear_material(id_competencia):
    if "user_id" not in session or session.get("user_rol") != "docente":
        return redirect(url_for("auth.login"))

    titulo = (request.form.get("titulo_material") or "").strip()
    tipo = (request.form.get("tipo") or "").strip().lower()
    url_mat = (request.form.get("url") or "").strip()
    tiempo_str = request.form.get("tiempo_estimado", "").strip()
    nivel_str = request.form.get("nivel_material", "").strip()

    try:
        tiempo = int(tiempo_str) if tiempo_str else 0
    except ValueError:
        tiempo = 0

    try:
        nivel_material = int(nivel_str) if nivel_str else None
    except ValueError:
        nivel_material = None

    if nivel_material not in (1, 2, 3, None):
        nivel_material = None

    if not titulo or not tipo or not url_mat:
        flash("Título, tipo y URL del material son obligatorios.", "error")
        return redirect(url_for("temas.gestion_temas", id_competencia=id_competencia))

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO material_estudio (titulo, tipo, url, tiempo_estimado, nivel, id_competencia)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (titulo, tipo, url_mat, tiempo, nivel_material, id_competencia),
    )
    conn.commit()
    cur.close()

    flash("Material añadido correctamente.", "success")
    return redirect(url_for("temas.gestion_temas", id_competencia=id_competencia))


# ================= EDITAR MATERIAL =================
@bp_temas.route("/material/<int:id_material>/editar", methods=["POST"])
def editar_material(id_material):
    if "user_id" not in session or session.get("user_rol") != "docente":
        return redirect(url_for("auth.login"))

    titulo = (request.form.get("titulo_material") or "").strip()
    tipo = (request.form.get("tipo") or "").strip().lower()
    url_mat = (request.form.get("url") or "").strip()
    tiempo_str = request.form.get("tiempo_estimado", "").strip()
    nivel_str = request.form.get("nivel_material", "").strip()

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT id_competencia FROM material_estudio WHERE id_material = %s",
        (id_material,),
    )
    row = cur.fetchone()
    if not row:
        cur.close()
        flash("El material no existe.", "error")
        return redirect(url_for("temas.gestion_temas"))

    id_competencia = row[0]

    try:
        tiempo = int(tiempo_str) if tiempo_str else 0
    except ValueError:
        tiempo = 0

    try:
        nivel_material = int(nivel_str) if nivel_str else None
    except ValueError:
        nivel_material = None

    if nivel_material not in (1, 2, 3, None):
        nivel_material = None

    if not titulo or not tipo or not url_mat:
        cur.close()
        flash("Título, tipo y URL del material son obligatorios.", "error")
        return redirect(url_for("temas.gestion_temas", id_competencia=id_competencia))

    cur.execute(
        """
        UPDATE material_estudio
        SET titulo = %s,
            tipo = %s,
            url = %s,
            tiempo_estimado = %s,
            nivel = %s
        WHERE id_material = %s
        """,
        (titulo, tipo, url_mat, tiempo, nivel_material, id_material),
    )
    conn.commit()
    cur.close()

    flash("Material actualizado correctamente.", "success")
    return redirect(url_for("temas.gestion_temas", id_competencia=id_competencia))


# ================= ELIMINAR MATERIAL =================
@bp_temas.route("/material/<int:id_material>/eliminar", methods=["POST"])
def eliminar_material(id_material):
    if "user_id" not in session or session.get("user_rol") != "docente":
        return redirect(url_for("auth.login"))

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT id_competencia FROM material_estudio WHERE id_material = %s",
        (id_material,),
    )
    row = cur.fetchone()
    if not row:
        cur.close()
        flash("El material ya no existe.", "error")
        return redirect(url_for("temas.gestion_temas"))

    id_competencia = row[0]

    cur.execute(
        "DELETE FROM material_estudio WHERE id_material = %s",
        (id_material,),
    )
    conn.commit()
    cur.close()

    flash("Material eliminado correctamente.", "success")
    return redirect(url_for("temas.gestion_temas", id_competencia=id_competencia))
