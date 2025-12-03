# ws/reportes.py
from flask import (
    Blueprint, render_template, session, redirect,
    url_for, request, flash
)
from db import get_db

bp_reportes = Blueprint(
    "reportes",
    __name__,
    url_prefix="/docente/reportes"
)


@bp_reportes.route("/progreso", methods=["GET"])
def reporte_progreso():
    """
    Reporte de progreso del estudiante.
    - Filtros de salón y estudiante
    - Progreso general
    - Progreso por competencia (porcentaje de aciertos)
    - Historial de actividades
    - Datos para gráfico histórico tipo heatmap
    """
    # Solo docentes
    if "user_id" not in session or session.get("user_rol") != "docente":
        return redirect(url_for("auth.login"))

    conn = get_db()
    cur = conn.cursor()

    # 1) Salones asignados al docente
    cur.execute(
        """
        SELECT s.id_salon, s.nombre_salon
        FROM salones s
        JOIN docente_salones ds ON ds.id_salon = s.id_salon
        JOIN docente d         ON d.id_docente = ds.id_docente
        WHERE d.id_usuario = %s
        ORDER BY s.nombre_salon
        """,
        (session["user_id"],),
    )
    salones_rows = cur.fetchall()
    salones = [
        {"id_salon": r[0], "nombre": r[1]}
        for r in salones_rows
    ]

    if not salones:
        cur.close()
        return render_template(
            "docente_reporte_progreso.html",
            titulo_pagina="Reportes Detallados",
            active_page="reportes",
            salones=[],
            estudiantes=[],
            salon_seleccionado=None,
            estudiante_seleccionado=None,
            salon_actual=None,
            estudiante_actual=None,
            progreso_general=0,
            progreso_competencias={},
            historial=[],
            valores_heatmap=[0] * 28,
        )

    # 2) Salón seleccionado
    id_salon_sel = request.args.get("id_salon", type=int)
    if not id_salon_sel:
        id_salon_sel = salones[0]["id_salon"]

    # 3) Estudiantes del salón
    cur.execute(
        """
        SELECT e.id_estudiante,
               u.nombre || ' ' || u.apellidos AS nombre_completo
        FROM estudiante e
        JOIN usuarios u             ON u.id_usuario = e.id_usuario
        JOIN estudiante_salones es  ON es.id_estudiante = e.id_estudiante
        WHERE es.id_salon = %s
        ORDER BY nombre_completo
        """,
        (id_salon_sel,),
    )
    est_rows = cur.fetchall()
    estudiantes = [
        {"id_estudiante": r[0], "nombre": r[1]}
        for r in est_rows
    ]

    if not estudiantes:
        cur.close()
        return render_template(
            "docente_reporte_progreso.html",
            titulo_pagina="Reportes Detallados",
            active_page="reportes",
            salones=salones,
            estudiantes=[],
            salon_seleccionado=id_salon_sel,
            estudiante_seleccionado=None,
            salon_actual=None,
            estudiante_actual=None,
            progreso_general=0,
            progreso_competencias={},
            historial=[],
            valores_heatmap=[0] * 28,
        )

    # 4) Estudiante seleccionado
    id_est_sel = request.args.get("id_estudiante", type=int)
    if not id_est_sel:
        id_est_sel = estudiantes[0]["id_estudiante"]

    # Objetos "actuales" para la tarjeta de arriba
    salon_actual = next(
        (s for s in salones if s["id_salon"] == id_salon_sel),
        None
    )
    estudiante_actual = next(
        (e for e in estudiantes if e["id_estudiante"] == id_est_sel),
        None
    )

        # 5) Progreso general (promedio de PUNTAJES 0..100, igual que la API)
    cur.execute(
        """
        SELECT COALESCE(AVG(p.puntaje), 0) AS promedio
        FROM puntajes p
        WHERE p.id_estudiante = %s
        """,
        (id_est_sel,),
    )
    row_pg = cur.fetchone()
    promedio = row_pg[0] if row_pg and row_pg[0] is not None else 0
    progreso_general = int(round(float(promedio)))
    if progreso_general < 0:
        progreso_general = 0
    if progreso_general > 100:
        progreso_general = 100

    # 6) Progreso por competencia (mismo criterio que /progreso/por_competencia de la API)
    cur.execute(
        """
        SELECT
            c.area,
            COALESCE(AVG(p.puntaje), 0) AS promedio
        FROM competencias c
        LEFT JOIN puntajes p
               ON p.id_competencia = c.id_competencia
              AND p.id_estudiante = %s
        GROUP BY c.id_competencia, c.area
        ORDER BY c.id_competencia
        """,
        (id_est_sel,),
    )

    progreso_competencias = {}
    for area, promedio in cur.fetchall():
        if promedio is None:
            porcentaje_int = 0
        else:
            porcentaje_int = int(round(float(promedio)))
        porcentaje_int = max(0, min(100, porcentaje_int))
        progreso_competencias[area] = porcentaje_int
        
    # 7) Historial de actividades
    #    a) Respuestas a ejercicios
    cur.execute(
        """
        SELECT r.id_respuesta,
               r.fecha,
               e.descripcion AS actividad,
               'Ejercicio'   AS tipo,
               COALESCE(NULLIF(r.respuesta_texto, ''), opt.descripcion, '-') AS respuesta_estudiante,
               COALESCE(opt.descripcion, '-') AS respuesta_correcta,
               CASE
                   WHEN opt.es_correcta THEN 100
                   ELSE 0
               END AS puntaje,
               (r.desarrollo_url IS NOT NULL) AS tiene_imagen,
               r.desarrollo_url
        FROM respuestas_estudiantes r
        JOIN ejercicios e       ON e.id_ejercicio = r.id_ejercicio
        LEFT JOIN opciones_ejercicio opt ON opt.id_opcion = r.id_opcion
        WHERE r.id_estudiante = %s
        """,
        (id_est_sel,),
    )
    hist_ej = cur.fetchall()

    #    b) Historial de materiales (videos, PDFs, etc.)
    cur.execute(
        """
        SELECT h.id_historial,
               h.fecha_revision,
               m.titulo         AS actividad,
               m.tipo           AS tipo,
               NULL             AS respuesta_estudiante,
               NULL             AS respuesta_correcta,
               CASE
                    WHEN h.estado = 'completado' THEN 100
                    ELSE NULL
               END              AS puntaje,
               FALSE            AS tiene_imagen,
               NULL             AS desarrollo_url
        FROM historial_material_estudio h
        JOIN material_estudio m ON m.id_material = h.id_material
        WHERE h.id_estudiante = %s
        """,
        (id_est_sel,),
    )
    hist_mat = cur.fetchall()

    cur.close()

    # Unificamos en una sola lista y ordenamos por fecha DESC
    historial = []
    for r in hist_ej:
        historial.append({
            "id_respuesta": r[0],
            "fecha": r[1],
            "actividad": r[2],
            "tipo": r[3],
            "respuesta_estudiante": r[4],
            "respuesta_correcta": r[5],
            "puntaje": r[6],
            "tiene_imagen": bool(r[7]),
            "desarrollo_url": r[8],
        })
    for r in hist_mat:
        historial.append({
            "id_respuesta": None,
            "fecha": r[1],
            "actividad": r[2],
            "tipo": r[3],
            "respuesta_estudiante": r[4],
            "respuesta_correcta": r[5],
            "puntaje": r[6],
            "tiene_imagen": False,
            "desarrollo_url": None,
        })

    historial.sort(key=lambda x: x["fecha"], reverse=True)
    historial = historial[:50]  # un poco más largo para el gráfico


    # 8) Valores para el gráfico histórico tipo heatmap
    valores_heatmap = [
        (h["puntaje"] or 0)
        for h in historial
        if h["tipo"] == "Ejercicio"
    ][:28]  # máximo 28 celdas (7x4)

    # Rellenamos hasta 28 con ceros
    while len(valores_heatmap) < 28:
        valores_heatmap.append(0)

    return render_template(
        "docente_reporte_progreso.html",
        titulo_pagina="Reportes Detallados",
        active_page="reportes",
        salones=salones,
        estudiantes=estudiantes,
        salon_seleccionado=id_salon_sel,
        estudiante_seleccionado=id_est_sel,
        salon_actual=salon_actual,
        estudiante_actual=estudiante_actual,
        progreso_general=progreso_general,
        progreso_competencias=progreso_competencias,
        historial=historial[:15],   # en la tabla solo mostramos 15
        valores_heatmap=valores_heatmap,
    )



@bp_reportes.route("/respuesta/<int:id_respuesta>/imagen")
def ver_imagen_respuesta(id_respuesta):
    """
    Abre el desarrollo del estudiante.
    Si la respuesta tiene 'desarrollo_url', redirigimos allí (archivo en /static).
    Si no, probamos con respuesta_imagen (legacy). Si nada, mensaje de error.
    """
    from flask import send_file, redirect
    import io

    if "user_id" not in session or session.get("user_rol") != "docente":
        return redirect(url_for("auth.login"))

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT desarrollo_url, respuesta_imagen
        FROM respuestas_estudiantes
        WHERE id_respuesta = %s
        """,
        (id_respuesta,),
    )
    row = cur.fetchone()
    cur.close()

    if not row:
        flash("No se encontró la respuesta.", "error")
        return redirect(url_for("reportes.reporte_progreso"))

    desarrollo_url, respuesta_imagen = row

    # 1) Nuevo flujo: archivo en /static (ruta tipo "/static/desarrollos_alumno/resp_10.jpg")
    if desarrollo_url:
        return redirect(desarrollo_url)

    # 2) Flujo viejo: imagen en bytea
    if respuesta_imagen:
        img_bytes = respuesta_imagen
        return send_file(io.BytesIO(img_bytes), mimetype="image/png")

    flash("Esta respuesta no tiene desarrollo asociado.", "error")
    return redirect(url_for("reportes.reporte_progreso"))

# Puedes dejar este stub o eliminarlo; ahora el botón usa window.print()
@bp_reportes.route("/progreso/pdf")
def reporte_progreso_pdf():
    flash("Para exportar, usa el botón 'Exportar PDF' que abre la vista de impresión del navegador.", "info")
    return redirect(url_for("reportes.reporte_progreso"))
