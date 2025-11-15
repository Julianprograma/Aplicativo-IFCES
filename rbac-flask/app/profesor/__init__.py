from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, jsonify
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from datetime import datetime
import json

from ..extensions import db
from ..models import User, Examen, Pregunta, Respuesta, ExamenResultado, Categoria
from ..decorators import role_required

profesor_bp = Blueprint("profesor", __name__, url_prefix="/profesor")


@profesor_bp.route("/estudiantes")
@login_required
@role_required("profesor")
def lista_estudiantes():
    estudiantes = User.query.filter_by(role="estudiante").all()
    return render_template("profesor/estudiantes.html", estudiantes=estudiantes)


@profesor_bp.route("/estudiante/<int:id>/toggle", methods=["POST"])
@login_required
@role_required("profesor")
def toggle_estudiante(id):
    estudiante = User.query.get_or_404(id)
    if estudiante.role != "estudiante":
        flash("Solo se pueden gestionar estudiantes", "danger")
        return redirect(url_for("profesor.lista_estudiantes"))
    
    estudiante.is_active = not estudiante.is_active
    db.session.commit()
    estado = "activado" if estudiante.is_active else "desactivado"
    flash(f"Estudiante {estudiante.username} {estado}", "success")
    return redirect(url_for("profesor.lista_estudiantes"))


@profesor_bp.route("/estudiante/<int:id>/eliminar", methods=["POST"])
@login_required
@role_required("profesor")
def eliminar_estudiante(id):
    estudiante = User.query.get_or_404(id)
    if estudiante.role != "estudiante":
        flash("Solo se pueden eliminar estudiantes", "danger")
        return redirect(url_for("profesor.lista_estudiantes"))
    
    username = estudiante.username
    db.session.delete(estudiante)
    db.session.commit()
    flash(f"Estudiante {username} eliminado", "success")
    return redirect(url_for("profesor.lista_estudiantes"))


@profesor_bp.route("/examenes")
@login_required
@role_required("profesor")
def lista_examenes():
    examenes = Examen.query.filter_by(profesor_id=current_user.id).all()
    return render_template("profesor/examenes.html", examenes=examenes)


@profesor_bp.route("/examen/crear", methods=["GET", "POST"])
@login_required
@role_required("profesor")
def crear_examen():
    if request.method == "POST":
        titulo = request.form.get("titulo", "").strip()
        descripcion = request.form.get("descripcion", "").strip()
        categoria_id = request.form.get("categoria_id", "").strip()
        duracion_minutos = request.form.get("duracion_minutos", "60").strip()
        fecha_limite = request.form.get("fecha_limite", "").strip()
        intentos_maximos = request.form.get("intentos_maximos", "1").strip()
        calificacion_minima = request.form.get("calificacion_minima", "60").strip()
        mostrar_respuestas = request.form.get("mostrar_respuestas") == "on"
        barajar_preguntas = request.form.get("barajar_preguntas") == "on"
        publicado = request.form.get("publicado") == "on"
        
        if not titulo:
            flash("El título es obligatorio", "warning")
            categorias = Categoria.query.filter_by(activo=True).all()
            return render_template("profesor/crear_examen.html", categorias=categorias)
        
        # Convertir fecha_limite de string a datetime
        fecha_limite_dt = None
        if fecha_limite:
            try:
                fecha_limite_dt = datetime.strptime(fecha_limite, '%Y-%m-%dT%H:%M')
            except ValueError:
                pass
        
        # Crear examen con todas las configuraciones
        examen = Examen(
            titulo=titulo,
            descripcion=descripcion,
            profesor_id=current_user.id,
            categoria_id=int(categoria_id) if categoria_id else None,
            duracion_minutos=int(duracion_minutos) if duracion_minutos else 60,
            fecha_limite=fecha_limite_dt,
            intentos_maximos=int(intentos_maximos) if intentos_maximos else 1,
            calificacion_minima=float(calificacion_minima) if calificacion_minima else 60.0,
            mostrar_respuestas=mostrar_respuestas,
            barajar_preguntas=barajar_preguntas,
            publicado=publicado
        )
        db.session.add(examen)
        db.session.commit()
        flash(f"Examen '{titulo}' creado exitosamente", "success")
        return redirect(url_for("profesor.gestionar_preguntas", id=examen.id))
    
    categorias = Categoria.query.filter_by(activo=True).all()
    return render_template("profesor/crear_examen.html", categorias=categorias)



@profesor_bp.route("/examen/<int:id>/editar", methods=["GET", "POST"])
@login_required
@role_required("profesor")
def editar_examen(id):
    examen = Examen.query.get_or_404(id)
    
    # Verificar que el profesor sea el creador
    if examen.profesor_id != current_user.id:
        flash("No tienes permiso para editar este examen", "danger")
        return redirect(url_for("profesor.lista_examenes"))
    
    if request.method == "POST":
        examen.titulo = request.form.get("titulo").strip()
        examen.descripcion = request.form.get("descripcion", "").strip()
        
        # Categoría
        categoria_id = request.form.get("categoria_id")
        examen.categoria_id = int(categoria_id) if categoria_id else None
        
        # Duración y fecha límite
        duracion = request.form.get("duracion_minutos")
        if duracion and duracion.isdigit():
            examen.duracion_minutos = int(duracion)
        
        fecha_limite_str = request.form.get("fecha_limite")
        if fecha_limite_str:
            from datetime import datetime
            try:
                examen.fecha_limite = datetime.fromisoformat(fecha_limite_str)
            except ValueError:
                flash("Formato de fecha inválido", "warning")
        
        # Configuraciones avanzadas
        intentos = request.form.get("intentos_maximos")
        if intentos and intentos.isdigit():
            examen.intentos_maximos = int(intentos)
        
        calificacion = request.form.get("calificacion_minima")
        if calificacion:
            try:
                examen.calificacion_minima = float(calificacion)
            except ValueError:
                pass
        
        examen.mostrar_respuestas = 'mostrar_respuestas' in request.form
        examen.barajar_preguntas = 'barajar_preguntas' in request.form
        
        db.session.commit()
        flash(f"Examen '{examen.titulo}' actualizado exitosamente", "success")
        return redirect(url_for("profesor.lista_examenes"))
    
    from app.models import Categoria
    categorias = Categoria.query.filter_by(activo=True).all()
    return render_template("profesor/editar_examen.html", 
                         examen=examen, categorias=categorias)


@profesor_bp.route("/examen/<int:id>/asignar", methods=["GET", "POST"])
@login_required
@role_required("profesor")
def asignar_examen(id):
    examen = Examen.query.get_or_404(id)
    
    if examen.profesor_id != current_user.id:
        flash("No tienes permiso para gestionar este examen", "danger")
        return redirect(url_for("profesor.lista_examenes"))
    
    if request.method == "POST":
        estudiante_ids = request.form.getlist("estudiantes")
        
        # Limpiar asignaciones previas
        examen.estudiantes = []
        
        # Agregar nuevas asignaciones
        for est_id in estudiante_ids:
            estudiante = User.query.get(int(est_id))
            if estudiante and estudiante.role == "estudiante":
                examen.estudiantes.append(estudiante)
        
        db.session.commit()
        flash(f"Estudiantes asignados al examen '{examen.titulo}'", "success")
        return redirect(url_for("profesor.lista_examenes"))
    
    estudiantes = User.query.filter_by(role="estudiante", is_active=True).all()
    asignados_ids = [e.id for e in examen.estudiantes.all()]
    
    return render_template("profesor/asignar_examen.html",
                         examen=examen,
                         estudiantes=estudiantes,
                         asignados_ids=asignados_ids)


@profesor_bp.route("/examen/<int:id>/duplicar", methods=["POST"])
@login_required
@role_required("profesor")
def duplicar_examen(id):
    examen_original = Examen.query.get_or_404(id)
    
    # Verificar permiso
    if examen_original.profesor_id != current_user.id:
        flash("No tienes permiso para duplicar este examen", "danger")
        return redirect(url_for("profesor.lista_examenes"))
    
    # Crear copia del examen
    nuevo_examen = Examen(
        titulo=f"{examen_original.titulo} (Copia)",
        descripcion=examen_original.descripcion,
        duracion_minutos=examen_original.duracion_minutos,
        fecha_limite=None,
        publicado=False,
        profesor_id=current_user.id,
        intentos_maximos=examen_original.intentos_maximos,
        mostrar_respuestas=examen_original.mostrar_respuestas,
        barajar_preguntas=examen_original.barajar_preguntas,
        calificacion_minima=examen_original.calificacion_minima
    )
    db.session.add(nuevo_examen)
    db.session.flush()  # Para obtener el ID del nuevo examen
    
    # Copiar preguntas
    for pregunta_original in examen_original.preguntas:
        nueva_pregunta = Pregunta(
            examen_id=nuevo_examen.id,
            texto=pregunta_original.texto,
            tipo=pregunta_original.tipo,
            opciones=pregunta_original.opciones,
            respuesta_correcta=pregunta_original.respuesta_correcta,
            puntos=pregunta_original.puntos,
            orden=pregunta_original.orden
        )
        db.session.add(nueva_pregunta)
    
    db.session.commit()
    flash(f"Examen duplicado exitosamente como '{nuevo_examen.titulo}'", "success")
    return redirect(url_for("profesor.gestionar_preguntas", id=nuevo_examen.id))


@profesor_bp.route("/examen/<int:id>/vista_previa")
@login_required
@role_required("profesor")
def vista_previa_examen(id):
    examen = Examen.query.get_or_404(id)
    
    if examen.profesor_id != current_user.id:
        flash("No tienes permiso para ver este examen", "danger")
        return redirect(url_for("profesor.lista_examenes"))
    
    preguntas = Pregunta.query.filter_by(examen_id=id).order_by(Pregunta.orden).all()
    
    # Si barajar_preguntas está activo, mostramos un mensaje
    # (no barajamos realmente en vista previa para que el profesor vea el orden original)
    
    return render_template("profesor/vista_previa_examen.html",
                         examen=examen,
                         preguntas=preguntas)



@profesor_bp.route("/examen/<int:id>/eliminar", methods=["POST"])
@login_required
@role_required("profesor")
def eliminar_examen(id):
    examen = Examen.query.get_or_404(id)
    
    if examen.profesor_id != current_user.id:
        flash("No tienes permiso para eliminar este examen", "danger")
        return redirect(url_for("profesor.lista_examenes"))
    
    titulo = examen.titulo
    db.session.delete(examen)
    db.session.commit()
    flash(f"Examen '{titulo}' eliminado", "success")
    return redirect(url_for("profesor.lista_examenes"))


# ============= GESTIÓN DE PREGUNTAS =============

@profesor_bp.route("/examen/<int:id>/preguntas")
@login_required
@role_required("profesor")
def gestionar_preguntas(id):
    examen = Examen.query.get_or_404(id)
    
    if examen.profesor_id != current_user.id:
        flash("No tienes permiso para gestionar este examen", "danger")
        return redirect(url_for("profesor.lista_examenes"))
    
    preguntas = Pregunta.query.filter_by(examen_id=id).order_by(Pregunta.orden).all()
    total_puntos = sum([p.puntos for p in preguntas])
    
    return render_template("profesor/gestionar_preguntas.html", 
                         examen=examen, 
                         preguntas=preguntas,
                         total_puntos=total_puntos)


@profesor_bp.route("/examen/<int:id>/pregunta/crear", methods=["GET", "POST"])
@login_required
@role_required("profesor")
def crear_pregunta(id):
    examen = Examen.query.get_or_404(id)
    
    if examen.profesor_id != current_user.id:
        flash("No tienes permiso", "danger")
        return redirect(url_for("profesor.lista_examenes"))
    
    if request.method == "POST":
        texto = request.form.get("texto").strip()
        tipo = request.form.get("tipo")
        puntos = int(request.form.get("puntos", 1))
        
        if not texto or not tipo:
            flash("Texto y tipo son obligatorios", "warning")
            return render_template("profesor/crear_pregunta.html", examen=examen)
        
        # Procesar según tipo
        opciones_json = None
        respuesta_correcta = None
        
        if tipo == "opcion_multiple":
            opciones_texto = []
            i = 1
            while f"opcion_{i}" in request.form:
                opcion = request.form.get(f"opcion_{i}").strip()
                if opcion:
                    opciones_texto.append(opcion)
                i += 1
            
            if len(opciones_texto) < 2:
                flash("Debes agregar al menos 2 opciones", "warning")
                return render_template("profesor/crear_pregunta.html", examen=examen)
            
            respuesta_correcta_texto = request.form.get("respuesta_correcta")
            if not respuesta_correcta_texto:
                flash("Debes seleccionar una respuesta correcta", "warning")
                return render_template("profesor/crear_pregunta.html", examen=examen)

            opciones = []
            for opt in opciones_texto:
                opciones.append({
                    "texto": opt,
                    "correcta": opt == respuesta_correcta_texto
                })

            opciones_json = json.dumps(opciones)
            respuesta_correcta = None  # La respuesta correcta ahora está en el JSON de opciones
            
        elif tipo == "verdadero_falso":
            opciones_json = json.dumps([
                {"texto": "Verdadero", "correcta": request.form.get("respuesta_correcta") == "Verdadero"},
                {"texto": "Falso", "correcta": request.form.get("respuesta_correcta") == "Falso"}
            ])
            respuesta_correcta = request.form.get("respuesta_correcta")
        
        elif tipo == "abierta":
            respuesta_correcta = request.form.get("respuesta_correcta", "")
        
        # Obtener campos ICFES
        nivel_dificultad = request.form.get("nivel_dificultad", "basico")
        tiempo_estimado = int(request.form.get("tiempo_estimado", 60))
        explicacion = request.form.get("explicacion", "").strip()
        
        # Obtener el siguiente orden
        max_orden = db.session.query(db.func.max(Pregunta.orden)).filter_by(examen_id=id).scalar() or 0
        
        pregunta = Pregunta(
            examen_id=id,
            texto=texto,
            tipo=tipo,
            opciones=opciones_json,
            respuesta_correcta=respuesta_correcta,
            puntos=puntos,
            orden=max_orden + 1,
            nivel_dificultad=nivel_dificultad,
            tiempo_estimado=tiempo_estimado,
            explicacion=explicacion
        )
        
        db.session.add(pregunta)
        db.session.commit()
        flash("Pregunta agregada exitosamente", "success")
        return redirect(url_for("profesor.gestionar_preguntas", id=id))
    
    return render_template("profesor/crear_pregunta.html", examen=examen)


@profesor_bp.route("/pregunta/<int:id>/editar", methods=["GET", "POST"])
@login_required
@role_required("profesor")
def editar_pregunta(id):
    pregunta = Pregunta.query.get_or_404(id)
    examen = pregunta.examen
    
    if examen.profesor_id != current_user.id:
        flash("No tienes permiso para editar esta pregunta", "danger")
        return redirect(url_for("profesor.lista_examenes"))
    
    if request.method == "POST":
        pregunta.texto = request.form.get("texto").strip()
        tipo = request.form.get("tipo")
        pregunta.tipo = tipo
        pregunta.puntos = int(request.form.get("puntos", 5))
        
        if tipo == "opcion_multiple":
            opciones_texto = []
            i = 1
            while f"opcion_{i}" in request.form:
                opcion = request.form.get(f"opcion_{i}").strip()
                if opcion:
                    opciones_texto.append(opcion)
                i += 1
            
            if len(opciones_texto) < 2:
                flash("Debes agregar al menos 2 opciones", "warning")
                return render_template("profesor/editar_pregunta.html", 
                                     pregunta=pregunta, examen=examen)
            
            respuesta_correcta_texto = request.form.get("respuesta_correcta")
            if not respuesta_correcta_texto:
                flash("Debes seleccionar una respuesta correcta", "warning")
                return render_template("profesor/editar_pregunta.html", 
                                     pregunta=pregunta, examen=examen)

            opciones = []
            for opt in opciones_texto:
                opciones.append({
                    "texto": opt,
                    "correcta": opt == respuesta_correcta_texto
                })

            pregunta.opciones = json.dumps(opciones)
            pregunta.respuesta_correcta = None  # La respuesta correcta ahora está en el JSON de opciones
            
        elif tipo == "verdadero_falso":
            respuesta_correcta_vf = request.form.get("respuesta_correcta")
            pregunta.opciones = json.dumps([
                {"texto": "Verdadero", "correcta": respuesta_correcta_vf == "Verdadero"},
                {"texto": "Falso", "correcta": respuesta_correcta_vf == "Falso"}
            ])
            pregunta.respuesta_correcta = respuesta_correcta_vf
        
        else:  # abierta
            pregunta.opciones = None
            pregunta.respuesta_correcta = request.form.get("respuesta_correcta", "")
        
        db.session.commit()
        flash("Pregunta actualizada exitosamente", "success")
        return redirect(url_for("profesor.gestionar_preguntas", id=examen.id))
    
    return render_template("profesor/editar_pregunta.html", 
                         pregunta=pregunta, examen=examen)


@profesor_bp.route("/pregunta/<int:id>/eliminar", methods=["POST"])
@login_required
@role_required("profesor")
def eliminar_pregunta(id):
    pregunta = Pregunta.query.get_or_404(id)
    examen = pregunta.examen
    
    if examen.profesor_id != current_user.id:
        flash("No tienes permiso", "danger")
        return redirect(url_for("profesor.lista_examenes"))
    
    examen_id = pregunta.examen_id
    db.session.delete(pregunta)
    db.session.commit()
    flash("Pregunta eliminada", "success")
    return redirect(url_for("profesor.gestionar_preguntas", id=examen_id))


@profesor_bp.route("/examen/<int:id>/publicar", methods=["POST"])
@login_required
@role_required("profesor")
def publicar_examen(id):
    examen = Examen.query.get_or_404(id)
    
    if examen.profesor_id != current_user.id:
        flash("No tienes permiso", "danger")
        return redirect(url_for("profesor.lista_examenes"))
    
    # Verificar que tenga preguntas
    if not examen.preguntas:
        flash("No puedes publicar un examen sin preguntas", "warning")
        return redirect(url_for("profesor.gestionar_preguntas", id=id))
    
    examen.publicado = True
    db.session.commit()
    flash(f"Examen '{examen.titulo}' publicado correctamente", "success")
    return redirect(url_for("profesor.lista_examenes"))


@profesor_bp.route("/examen/<int:id>/resultados")
@login_required
@role_required("profesor")
def ver_resultados(id):
    examen = Examen.query.get_or_404(id)
    
    if examen.profesor_id != current_user.id:
        flash("No tienes permiso", "danger")
        return redirect(url_for("profesor.lista_examenes"))
    
    resultados = ExamenResultado.query.filter_by(examen_id=id, completado=True).all()
    
    # Estadísticas
    if resultados:
        promedio = sum([r.calificacion for r in resultados]) / len(resultados)
        aprobados = len([r for r in resultados if r.calificacion >= 60])
    else:
        promedio = 0
        aprobados = 0
    
    return render_template("profesor/resultados_examen.html",
                         examen=examen,
                         resultados=resultados,
                         promedio=promedio,
                         aprobados=aprobados)


# FASE 1 - Comentarios del Profesor: Ver detalle de resultado
@profesor_bp.route("/examen/resultado/<int:id>")
@login_required
@role_required("Profesor")
def detalle_resultado(id):
    resultado = ExamenResultado.query.get_or_404(id)
    examen = Examen.query.get_or_404(resultado.examen_id)
    
    # Verificar que el profesor sea el propietario del examen
    if examen.profesor_id != current_user.id:
        flash("No tienes permiso para ver este resultado", "danger")
        return redirect(url_for("profesor.lista_examenes"))
    
    # Obtener preguntas del examen con respuestas del estudiante
    preguntas = Pregunta.query.filter_by(examen_id=examen.id).order_by(Pregunta.orden).all()
    
    return render_template("profesor/detalle_resultado.html",
                         resultado=resultado,
                         examen=examen,
                         preguntas=preguntas)


# FASE 1 - Comentarios del Profesor: Agregar/Editar comentario
@profesor_bp.route("/examen/resultado/<int:id>/comentar", methods=["POST"])
@login_required
@role_required("Profesor")
def agregar_comentario(id):
    resultado = ExamenResultado.query.get_or_404(id)
    examen = Examen.query.get_or_404(resultado.examen_id)
    
    # Verificar que el profesor sea el propietario del examen
    if examen.profesor_id != current_user.id:
        flash("No tienes permiso para comentar este resultado", "danger")
        return redirect(url_for("profesor.lista_examenes"))
    
    # Obtener datos del formulario
    comentario = request.form.get("comentario_profesor", "").strip()
    recomendaciones = request.form.get("recomendaciones", "").strip()
    
    # Actualizar resultado
    resultado.comentario_profesor = comentario if comentario else None
    resultado.recomendaciones = recomendaciones if recomendaciones else None
    
    db.session.commit()
    
    flash("Comentarios guardados exitosamente", "success")
    return redirect(url_for("profesor.detalle_resultado", id=id))

