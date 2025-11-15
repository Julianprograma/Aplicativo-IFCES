from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import func, desc, case
from datetime import datetime, timedelta
import json
import uuid

from ..extensions import db
from ..models import (User, Examen, Pregunta, ExamenResultado, Categoria, 
                      Respuesta, Notificacion, Certificado)
from ..decorators import role_required

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    return render_template("index.html")


@main_bp.route("/dashboard_estudiante")
@login_required
@role_required("estudiante")
def dashboard_estudiante():
    # Obtener estadísticas del estudiante
    total_asignados = len(current_user.examenes_asignados)
    
    # Contar exámenes completados
    completados = ExamenResultado.query.filter_by(estudiante_id=current_user.id).count()
    
    # Calcular promedio general
    resultados = ExamenResultado.query.filter_by(estudiante_id=current_user.id).all()
    promedio = sum(r.calificacion for r in resultados) / len(resultados) if resultados else 0
    
    # Exámenes próximos a vencer
    hoy = datetime.now()
    proximos = [e for e in current_user.examenes_asignados 
                if e.fecha_limite and e.fecha_limite > hoy 
                and not ExamenResultado.query.filter_by(estudiante_id=current_user.id, examen_id=e.id).first()]
    
    return render_template("dashboard_estudiante.html",
                         total_asignados=total_asignados,
                         completados=completados,
                         promedio=promedio,
                         examenes_proximos=proximos[:5])


@main_bp.route("/dashboard_profesor")
@login_required
@role_required("profesor")
def dashboard_profesor():
    # Estadísticas generales
    total_examenes = Examen.query.filter_by(profesor_id=current_user.id).count()
    total_preguntas = db.session.query(func.count(Pregunta.id)).join(
        Examen, Pregunta.examen_id == Examen.id
    ).filter(Examen.profesor_id == current_user.id).scalar()
    
    total_estudiantes = User.query.filter_by(role="estudiante", is_active=True).count()
    
    # Exámenes recientes (últimos 5)
    examenes_recientes = Examen.query.filter_by(
        profesor_id=current_user.id
    ).order_by(desc(Examen.fecha_creacion)).limit(5).all()
    
    # Exámenes próximos con fecha límite
    hoy = datetime.now()
    examenes_proximos = Examen.query.filter(
        Examen.profesor_id == current_user.id,
        Examen.fecha_limite.isnot(None),
        Examen.fecha_limite > hoy
    ).order_by(Examen.fecha_limite).limit(5).all()
    
    # Resultados recientes (últimas presentaciones)
    resultados_recientes = ExamenResultado.query.join(
        Examen, ExamenResultado.examen_id == Examen.id
    ).filter(
        Examen.profesor_id == current_user.id
    ).order_by(desc(ExamenResultado.fecha_presentacion)).limit(10).all()
    
    # Estadísticas de rendimiento
    stats_rendimiento = db.session.query(
        func.avg(ExamenResultado.calificacion).label('promedio'),
        func.max(ExamenResultado.calificacion).label('maxima'),
        func.min(ExamenResultado.calificacion).label('minima'),
        func.count(ExamenResultado.id).label('total')
    ).join(
        Examen, ExamenResultado.examen_id == Examen.id
    ).filter(
        Examen.profesor_id == current_user.id
    ).first()
    
    # Estudiantes con bajo rendimiento (promedio < 3.0 en escala 0-5)
    avg_calif_normalizada = func.avg(
        case(
            (ExamenResultado.calificacion > 5.0, ExamenResultado.calificacion / 20.0),
            else_=ExamenResultado.calificacion
        )
    ).label('promedio')

    estudiantes_bajo_rendimiento = db.session.query(
        User.id,
        User.username,
        avg_calif_normalizada
    ).join(
        ExamenResultado, User.id == ExamenResultado.estudiante_id
    ).join(
        Examen, ExamenResultado.examen_id == Examen.id
    ).filter(
        Examen.profesor_id == current_user.id
    ).group_by(User.id, User.username).having(
        avg_calif_normalizada < 3.0
    ).limit(5).all()
    
    return render_template(
        "dashboard_profesor.html",
        total_examenes=total_examenes,
        total_preguntas=total_preguntas,
        total_estudiantes=total_estudiantes,
        examenes_recientes=examenes_recientes,
        examenes_proximos=examenes_proximos,
        resultados_recientes=resultados_recientes,
        stats_rendimiento=stats_rendimiento,
        estudiantes_bajo_rendimiento=estudiantes_bajo_rendimiento,
        now=datetime.now()
    )


@main_bp.route("/reporte_examenes")
@login_required
@role_required("profesor")
def reporte_examenes():
    """FASE 2: Reporte detallado de exámenes calificados y progreso de estudiantes"""
    
    # Estadísticas generales
    total_examenes = Examen.query.filter_by(profesor_id=current_user.id).count()
    total_presentaciones = db.session.query(ExamenResultado).join(
        Examen
    ).filter(
        Examen.profesor_id == current_user.id,
        ExamenResultado.completado == True
    ).count()
    
    # Análisis por categoría
    stats_por_categoria = db.session.query(
        Categoria.nombre,
        Categoria.icono,
        func.count(Examen.id).label('total_examenes'),
        func.count(ExamenResultado.id).label('total_presentaciones'),
        func.avg(ExamenResultado.calificacion).label('promedio_calificacion')
    ).select_from(Categoria).outerjoin(
        Examen, Categoria.id == Examen.categoria_id
    ).outerjoin(
        ExamenResultado, Examen.id == ExamenResultado.examen_id
    ).filter(
        Examen.profesor_id == current_user.id
    ).group_by(Categoria.id, Categoria.nombre, Categoria.icono).all()
    
    # Progreso de estudiantes (Top 10)
    progreso_estudiantes = db.session.query(
        User.id,
        User.username,
        User.email,
        func.count(ExamenResultado.id).label('examenes_presentados'),
        func.avg(ExamenResultado.calificacion).label('promedio'),
        func.max(ExamenResultado.calificacion).label('mejor_nota'),
        func.min(ExamenResultado.calificacion).label('peor_nota'),
        func.sum(ExamenResultado.total_puntos).label('total_puntos_posibles'),
        func.sum(ExamenResultado.calificacion).label('total_puntos_obtenidos')
    ).join(
        ExamenResultado, User.id == ExamenResultado.estudiante_id
    ).join(
        Examen, ExamenResultado.examen_id == Examen.id
    ).filter(
        Examen.profesor_id == current_user.id,
        ExamenResultado.completado == True
    ).group_by(User.id, User.username, User.email).order_by(
        desc(func.avg(ExamenResultado.calificacion))
    ).limit(20).all()
    
    # Exámenes con más presentaciones
    examenes_populares = db.session.query(
        Examen.id,
        Examen.titulo,
        Categoria.nombre.label('categoria_nombre'),
        Categoria.icono.label('categoria_icono'),
        func.count(ExamenResultado.id).label('num_presentaciones'),
        func.avg(ExamenResultado.calificacion).label('promedio')
    ).outerjoin(
        ExamenResultado, Examen.id == ExamenResultado.examen_id
    ).outerjoin(
        Categoria, Examen.categoria_id == Categoria.id
    ).filter(
        Examen.profesor_id == current_user.id
    ).group_by(
        Examen.id, Examen.titulo, Categoria.nombre, Categoria.icono
    ).order_by(
        desc(func.count(ExamenResultado.id))
    ).limit(10).all()
    
    # Distribución de calificaciones (rangos)
    rango_calificaciones = db.session.query(
        func.count(ExamenResultado.id).label('count'),
        ExamenResultado.calificacion
    ).join(
        Examen, ExamenResultado.examen_id == Examen.id
    ).filter(
        Examen.profesor_id == current_user.id,
        ExamenResultado.completado == True
    ).all()
    
    # Calcular distribución por rangos
    rangos = {
        'excelente': 0,  # 4.5-5.0
        'bueno': 0,      # 3.5-4.49
        'aceptable': 0,  # 3.0-3.49
        'insuficiente': 0 # 0-2.99
    }
    
    for _, calificacion in rango_calificaciones:
        if calificacion is not None:
            if calificacion > 5.0: # Escala antigua 0-100
                if calificacion >= 90:
                    rangos['excelente'] += 1
                elif calificacion >= 70:
                    rangos['bueno'] += 1
                elif calificacion >= 60:
                    rangos['aceptable'] += 1
                else:
                    rangos['insuficiente'] += 1
            else: # Nueva escala 0-5
                if calificacion >= 4.5:
                    rangos['excelente'] += 1
                elif calificacion >= 3.5:
                    rangos['bueno'] += 1
                elif calificacion >= 3.0:
                    rangos['aceptable'] += 1
                else:
                    rangos['insuficiente'] += 1
    
    # Tendencia temporal (últimos 6 meses)
    hace_6_meses = datetime.now() - timedelta(days=180)
    tendencia_mensual = db.session.query(
        func.date_format(ExamenResultado.fecha_presentacion, '%Y-%m').label('mes'),
        func.count(ExamenResultado.id).label('total'),
        func.avg(ExamenResultado.calificacion).label('promedio')
    ).join(
        Examen, ExamenResultado.examen_id == Examen.id
    ).filter(
        Examen.profesor_id == current_user.id,
        ExamenResultado.completado == True,
        ExamenResultado.fecha_presentacion >= hace_6_meses
    ).group_by(
        func.date_format(ExamenResultado.fecha_presentacion, '%Y-%m')
    ).order_by('mes').all()
    
    return render_template(
        "profesor/reporte_examenes.html",
        total_examenes=total_examenes,
        total_presentaciones=total_presentaciones,
        stats_por_categoria=stats_por_categoria,
        progreso_estudiantes=progreso_estudiantes,
        examenes_populares=examenes_populares,
        rangos=rangos,
        tendencia_mensual=tendencia_mensual
    )


# ============= RUTAS PARA ESTUDIANTES =============

@main_bp.route("/estudiante/examenes")
@login_required
@role_required("estudiante")
def estudiante_examenes():
    """Lista de exámenes asignados al estudiante"""
    hoy = datetime.now()
    
    examenes_info = []
    for examen in current_user.examenes_asignados:
        # Verificar si ya completó el examen
        resultado = ExamenResultado.query.filter_by(
            estudiante_id=current_user.id,
            examen_id=examen.id
        ).first()
        
        # Determinar estado
        if resultado:
            estado = "completado"
            fecha_completado = resultado.fecha_presentacion
        elif examen.fecha_limite and examen.fecha_limite < hoy:
            estado = "vencido"
            fecha_completado = None
        elif examen.fecha_limite and (
            examen.fecha_limite - hoy).days <= 3:
            estado = "por_vencer"
            fecha_completado = None
        else:
            estado = "disponible"
            fecha_completado = None
        
        examenes_info.append({
            'examen': examen,
            'estado': estado,
            'resultado': resultado,
            'fecha_completado': fecha_completado,
            'dias_restantes': (examen.fecha_limite - hoy).days if (
                examen.fecha_limite and examen.fecha_limite > hoy) else None
        })
    
    return render_template(
        "estudiante/examenes.html",
        examenes_info=examenes_info
    )


@main_bp.route("/estudiante/examen/<int:examen_id>/presentar")
@login_required
@role_required("estudiante")
def estudiante_presentar_examen(examen_id):
    """Vista para presentar un examen"""
    examen = Examen.query.get_or_404(examen_id)
    
    # Verificar que el examen esté asignado
    if examen not in current_user.examenes_asignados:
        return "No tienes acceso a este examen", 403
    
    # Verificar si ya lo completó
    resultado_existente = ExamenResultado.query.filter_by(
        estudiante_id=current_user.id,
        examen_id=examen.id
    ).first()
    
    if resultado_existente:
        return "Ya has completado este examen", 400
    
    # Verificar fecha límite
    if examen.fecha_limite and examen.fecha_limite < datetime.now():
        return "Este examen ha vencido", 400
    
    return render_template(
        "estudiante/presentar_examen.html",
        examen=examen
    )


@main_bp.route("/estudiante/mis-resultados")
@login_required
@role_required("estudiante")
def estudiante_resultados():
    """Historial de resultados del estudiante"""
    resultados = ExamenResultado.query.filter_by(
        estudiante_id=current_user.id
    ).order_by(desc(ExamenResultado.fecha_presentacion)).all()
    
    # Calcular estadísticas
    if resultados:
        promedio = sum(r.calificacion for r in resultados) / len(resultados)
        
        aprobados = 0
        for r in resultados:
            calificacion_actual = r.calificacion
            calif_minima = r.examen.calificacion_minima or 60

            # Normalizar calificacion_actual a escala 0-5 si es necesario
            if calificacion_actual > 5.0:
                calificacion_actual = (calificacion_actual / 100) * 5.0

            # Normalizar calif_minima a escala 0-5 si es necesario
            if calif_minima > 5.0:
                calif_minima = (calif_minima / 100) * 5.0
            
            if calificacion_actual >= calif_minima:
                aprobados += 1
        
        mejor_nota = max(r.calificacion for r in resultados)
    else:
        promedio = 0
        aprobados = 0
        mejor_nota = 0
    
    return render_template(
        "estudiante/resultados.html",
        resultados=resultados,
        total=len(resultados),
        promedio=promedio,
        aprobados=aprobados,
        mejor_nota=mejor_nota
    )


@main_bp.route("/estudiante/resultado/<int:resultado_id>")
@login_required
@role_required("estudiante")
def estudiante_detalle_resultado(resultado_id):
    """Detalle de un resultado específico"""
    resultado = ExamenResultado.query.get_or_404(resultado_id)
    
    # Verificar que sea del estudiante actual
    if resultado.estudiante_id != current_user.id:
        return "No tienes acceso a este resultado", 403
    
    return render_template(
        "estudiante/detalle_resultado.html",
        resultado=resultado
    )


@main_bp.route("/estudiante/examen/<int:examen_id>/enviar", methods=["POST"])
@login_required
@role_required("estudiante")
def estudiante_enviar_examen(examen_id):
    """Procesar respuestas del examen"""
    examen = Examen.query.get_or_404(examen_id)
    
    # Verificar acceso
    if examen not in current_user.examenes_asignados:
        return jsonify({"error": "No autorizado"}), 403
    
    # Verificar si ya completó
    resultado_existente = ExamenResultado.query.filter_by(
        estudiante_id=current_user.id,
        examen_id=examen.id
    ).first()
    
    if resultado_existente:
        return jsonify({"error": "Ya completaste este examen"}), 400
    
    # Obtener respuestas del formulario
    respuestas_data = request.get_json()
    
    # Calcular calificación
    total_preguntas = len(examen.preguntas)
    correctas = 0
    
    respuestas_guardadas = []
    
    for pregunta in examen.preguntas:
        respuesta_estudiante = respuestas_data.get(
            f'pregunta_{pregunta.id}', '')
        
        # Verificar si es correcta
        es_correcta = False
        if pregunta.tipo == 'opcion_multiple':
            opciones = json.loads(pregunta.opciones)
            respuesta_correcta = next(
                (opt['texto'] for opt in opciones if opt['correcta']), None)
            es_correcta = respuesta_estudiante == respuesta_correcta
        elif pregunta.tipo == 'verdadero_falso':
            es_correcta = respuesta_estudiante == pregunta.respuesta_correcta
        
        if es_correcta:
            correctas += 1
        
        # Guardar respuesta
        respuesta = Respuesta(
            examen_id=examen.id,
            pregunta_id=pregunta.id,
            estudiante_id=current_user.id,
            respuesta_texto=respuesta_estudiante,
            es_correcta=es_correcta
        )
        respuestas_guardadas.append(respuesta)
    
    # Calcular calificación de 0.0 a 5.0
    calificacion = round((correctas / total_preguntas) * 5.0, 2) if (
        total_preguntas > 0) else 0.0
    
    # Crear resultado
    resultado = ExamenResultado(
        examen_id=examen.id,
        estudiante_id=current_user.id,
        calificacion=calificacion,
        completado=True,
        fecha_presentacion=datetime.now(),
        tiempo_utilizado=respuestas_data.get('tiempo_utilizado', 0)
    )
    
    db.session.add(resultado)
    for resp in respuestas_guardadas:
        db.session.add(resp)
    
    db.session.commit()
    
    return jsonify({
        "success": True,
        "calificacion": calificacion,
        "correctas": correctas,
        "total": total_preguntas,
        "resultado_id": resultado.id
    })




@main_bp.route("/dashboard_admin")
@login_required
@role_required("admin")
def dashboard_admin():
    usuarios = User.query.all()
    return render_template("dashboard_admin.html", usuarios=usuarios)


@main_bp.route("/usuarios")
@login_required
@role_required("admin", "profesor")
def usuarios():
    if current_user.role == "profesor":
        data = User.query.filter_by(role="estudiante").all()
    else:
        data = User.query.all()
    return render_template("usuarios.html", usuarios=data)


# ============================================================================
# FASE 2: FUNCIONALIDADES AVANZADAS
# ============================================================================

@main_bp.route("/estudiante/progreso-detallado")
@login_required
@role_required("estudiante")
def estudiante_progreso_detallado():
    """Dashboard de progreso personal más detallado con análisis por categoría"""
    resultados = ExamenResultado.query.filter_by(
        estudiante_id=current_user.id,
        completado=True
    ).all()
    
    # Análisis por categoría
    categorias_stats = {}
    for resultado in resultados:
        if resultado.examen.categoria:
            cat_nombre = resultado.examen.categoria.nombre
            if cat_nombre not in categorias_stats:
                categorias_stats[cat_nombre] = {
                    'total': 0,
                    'suma_calificaciones': 0,
                    'color': resultado.examen.categoria.color,
                    'icono': resultado.examen.categoria.icono
                }
            categorias_stats[cat_nombre]['total'] += 1
            categorias_stats[cat_nombre]['suma_calificaciones'] += resultado.calificacion
    
    # Calcular promedios por categoría
    for cat in categorias_stats:
        categorias_stats[cat]['promedio'] = (
            categorias_stats[cat]['suma_calificaciones'] / 
            categorias_stats[cat]['total']
        )
    
    # Análisis de fortalezas y debilidades
    fortalezas = []
    debilidades = []
    
    for cat, stats in categorias_stats.items():
        if stats['promedio'] >= 80:
            fortalezas.append({'nombre': cat, 'promedio': stats['promedio'], 
                             'color': stats['color'], 'icono': stats['icono']})
        elif stats['promedio'] < 60:
            debilidades.append({'nombre': cat, 'promedio': stats['promedio'],
                              'color': stats['color'], 'icono': stats['icono']})
    
    # Progreso en el tiempo
    progreso_tiempo = []
    for resultado in sorted(resultados, key=lambda x: x.fecha_presentacion):
        progreso_tiempo.append({
            'fecha': resultado.fecha_presentacion.strftime('%d/%m/%Y'),
            'calificacion': resultado.calificacion,
            'examen': resultado.examen.titulo
        })
    
    # Estadísticas generales
    total_examenes = len(resultados)
    promedio_general = (sum(r.calificacion for r in resultados) / 
                       total_examenes) if total_examenes > 0 else 0
    mejor_calificacion = max((r.calificacion for r in resultados), default=0)
    
    examenes_aprobados = 0
    for r in resultados:
        calificacion_actual = r.calificacion
        calif_minima = r.examen.calificacion_minima or 60

        # Normalizar calificacion_actual a escala 0-5 si es necesario
        if calificacion_actual > 5.0:
            calificacion_actual = (calificacion_actual / 100) * 5.0

        # Normalizar calif_minima a escala 0-5 si es necesario
        if calif_minima > 5.0:
            calif_minima = (calif_minima / 100) * 5.0
        
        if calificacion_actual >= calif_minima:
            examenes_aprobados += 1
    
    return render_template(
        "estudiante/progreso_detallado.html",
        categorias_stats=categorias_stats,
        fortalezas=fortalezas,
        debilidades=debilidades,
        progreso_tiempo=progreso_tiempo,
        total_examenes=total_examenes,
        promedio_general=promedio_general,
        mejor_calificacion=mejor_calificacion,
        examenes_aprobados=examenes_aprobados
    )


@main_bp.route("/estudiante/notificaciones")
@login_required
@role_required("estudiante")
def estudiante_notificaciones():
    """Ver todas las notificaciones del estudiante"""
    notificaciones = Notificacion.query.filter_by(
        usuario_id=current_user.id
    ).order_by(desc(Notificacion.fecha_creacion)).all()
    
    # Contar no leídas
    no_leidas = sum(1 for n in notificaciones if not n.leida)
    
    return render_template(
        "estudiante/notificaciones.html",
        notificaciones=notificaciones,
        no_leidas=no_leidas
    )


@main_bp.route("/estudiante/notificacion/<int:notif_id>/marcar-leida", 
               methods=["POST"])
@login_required
@role_required("estudiante")
def marcar_notificacion_leida(notif_id):
    """Marcar una notificación como leída"""
    notificacion = Notificacion.query.get_or_404(notif_id)
    
    if notificacion.usuario_id != current_user.id:
        return jsonify({"error": "No autorizado"}), 403
    
    notificacion.leida = True
    db.session.commit()
    
    return jsonify({"success": True})


@main_bp.route("/api/notificaciones/no-leidas")
@login_required
def obtener_notificaciones_no_leidas():
    """API para obtener notificaciones no leídas (para actualización en tiempo real)"""
    notificaciones = Notificacion.query.filter_by(
        usuario_id=current_user.id,
        leida=False
    ).order_by(desc(Notificacion.fecha_creacion)).limit(5).all()
    
    return jsonify({
        "count": len(notificaciones),
        "notificaciones": [{
            "id": n.id,
            "titulo": n.titulo,
            "mensaje": n.mensaje,
            "tipo": n.tipo,
            "fecha": n.fecha_creacion.strftime('%d/%m/%Y %H:%M'),
            "url": n.url_destino
        } for n in notificaciones]
    })


# ============================================================================
# FASE 3: FUNCIONALIDADES EXTRA
# ============================================================================

@main_bp.route("/estudiante/examen/<int:examen_id>/modo-practica")
@login_required
@role_required("estudiante")
def estudiante_modo_practica(examen_id):
    """Presentar examen en modo práctica (sin calificación)"""
    examen = Examen.query.get_or_404(examen_id)
    
    # Verificar que el examen esté asignado
    if examen not in current_user.examenes_asignados:
        flash("No tienes acceso a este examen", "danger")
        return redirect(url_for('main.estudiante_examenes'))
    
    return render_template(
        "estudiante/presentar_examen.html",
        examen=examen,
        modo_practica=True
    )


@main_bp.route("/estudiante/examen/<int:examen_id>/enviar-practica", 
               methods=["POST"])
@login_required
@role_required("estudiante")
def estudiante_enviar_practica(examen_id):
    """Procesar respuestas del modo práctica"""
    examen = Examen.query.get_or_404(examen_id)
    
    # Verificar acceso
    if examen not in current_user.examenes_asignados:
        return jsonify({"error": "No autorizado"}), 403
    
    # Obtener respuestas del formulario
    respuestas_data = request.get_json()
    
    # Calcular calificación (sin guardar)
    total_preguntas = len(examen.preguntas)
    correctas = 0
    resultados_preguntas = []
    
    for pregunta in examen.preguntas:
        respuesta_estudiante = respuestas_data.get(
            f'pregunta_{pregunta.id}', '')
        
        # Verificar si es correcta
        es_correcta = False
        respuesta_correcta = ""
        
        if pregunta.tipo == 'opcion_multiple':
            opciones = json.loads(pregunta.opciones)
            respuesta_correcta = next(
                (opt['texto'] for opt in opciones if opt['correcta']), None)
            es_correcta = respuesta_estudiante == respuesta_correcta
        elif pregunta.tipo == 'verdadero_falso':
            respuesta_correcta = pregunta.respuesta_correcta
            es_correcta = respuesta_estudiante == respuesta_correcta
        
        if es_correcta:
            correctas += 1
        
        resultados_preguntas.append({
            'pregunta_id': pregunta.id,
            'pregunta_texto': pregunta.texto,
            'respuesta_estudiante': respuesta_estudiante,
            'respuesta_correcta': respuesta_correcta,
            'es_correcta': es_correcta,
            'explicacion': pregunta.explicacion
        })
    
    # Calcular calificación de 0.0 a 5.0
    calificacion = round((correctas / total_preguntas) * 5.0, 2) if (
        total_preguntas > 0) else 0.0
    
    return jsonify({
        "success": True,
        "modo_practica": True,
        "calificacion": calificacion,
        "correctas": correctas,
        "total": total_preguntas,
        "resultados": resultados_preguntas
    })


@main_bp.route("/estudiante/resultado/<int:resultado_id>/solicitar-revision",
               methods=["POST"])
@login_required
@role_required("estudiante")
def solicitar_revision_resultado(resultado_id):
    """Solicitar revisión de respuestas al profesor"""
    resultado = ExamenResultado.query.get_or_404(resultado_id)
    
    # Verificar que sea del estudiante actual
    if resultado.estudiante_id != current_user.id:
        return jsonify({"error": "No autorizado"}), 403
    
    # Verificar que no haya sido solicitada antes
    if resultado.solicitud_revision:
        return jsonify({"error": "Ya solicitaste revisión para este examen"}), 400
    
    # Marcar como solicitada
    resultado.solicitud_revision = True
    resultado.fecha_solicitud_revision = datetime.now()
    
    # Crear notificación para el profesor
    notificacion = Notificacion(
        usuario_id=resultado.examen.profesor_id,
        titulo=f"Solicitud de revisión: {resultado.examen.titulo}",
        mensaje=f"El estudiante {current_user.username} ha solicitado revisión de su examen",
        tipo="info",
        url_destino=url_for('main.profesor_revisar_resultado', 
                           resultado_id=resultado.id)
    )
    
    db.session.add(notificacion)
    db.session.commit()
    
    flash("Solicitud de revisión enviada al profesor", "success")
    return jsonify({"success": True})


@main_bp.route("/profesor/resultado/<int:resultado_id>/revisar")
@login_required
@role_required("profesor")
def profesor_revisar_resultado(resultado_id):
    """Vista para que el profesor revise un resultado con solicitud"""
    resultado = ExamenResultado.query.get_or_404(resultado_id)
    
    # Verificar que sea del profesor actual
    if resultado.examen.profesor_id != current_user.id:
        flash("No tienes acceso a este resultado", "danger")
        return redirect(url_for('main.dashboard_profesor'))
    
    return render_template(
        "profesor/revisar_resultado.html",
        resultado=resultado
    )


@main_bp.route("/estudiante/certificado/<int:resultado_id>/generar",
               methods=["POST"])
@login_required
@role_required("estudiante")
def generar_certificado(resultado_id):
    """Generar certificado para un examen aprobado"""
    resultado = ExamenResultado.query.get_or_404(resultado_id)
    
    # Verificar que sea del estudiante actual
    if resultado.estudiante_id != current_user.id:
        return jsonify({"error": "No autorizado"}), 403
    
    # Verificar que haya aprobado
    calificacion_actual = resultado.calificacion
    calif_minima = resultado.examen.calificacion_minima or 60

    # Normalizar calificacion_actual a escala 0-5 si es necesario
    if calificacion_actual > 5.0:
        calificacion_actual = (calificacion_actual / 100) * 5.0

    # Normalizar calif_minima a escala 0-5 si es necesario
    if calif_minima > 5.0:
        calif_minima = (calif_minima / 100) * 5.0
    
    if calificacion_actual < calif_minima:
        return jsonify({"error": "Debes aprobar el examen para obtener el certificado"}), 400
    
    # Verificar si ya tiene certificado
    certificado_existente = Certificado.query.filter_by(
        resultado_id=resultado.id
    ).first()
    
    if certificado_existente:
        return jsonify({
            "success": True,
            "mensaje": "Certificado ya generado",
            "codigo": certificado_existente.codigo_verificacion
        })
    
    # Generar código único
    codigo = f"IFCES-{uuid.uuid4().hex[:8].upper()}"
    
    # Crear certificado
    certificado = Certificado(
        estudiante_id=current_user.id,
        examen_id=resultado.examen.id,
        resultado_id=resultado.id,
        codigo_verificacion=codigo,
        calificacion=resultado.calificacion
    )
    
    db.session.add(certificado)
    db.session.commit()
    
    # Crear notificación
    notificacion = Notificacion(
        usuario_id=current_user.id,
        titulo="¡Certificado generado!",
        mensaje=f"Tu certificado para {resultado.examen.titulo} ha sido generado exitosamente",
        tipo="success",
        url_destino=url_for('main.ver_certificado', codigo=codigo)
    )
    
    db.session.add(notificacion)
    db.session.commit()
    
    return jsonify({
        "success": True,
        "mensaje": "Certificado generado exitosamente",
        "codigo": codigo
    })


@main_bp.route("/certificado/<codigo>")
def ver_certificado(codigo):
    """Ver certificado público por código de verificación"""
    certificado = Certificado.query.filter_by(
        codigo_verificacion=codigo
    ).first_or_404()
    
    return render_template(
        "certificado.html",
        certificado=certificado
    )

@main_bp.route('/profesor/examen/<int:examen_id>/resultados', methods=['GET', 'POST'])
@login_required
@role_required('profesor')
def profesor_resultados_examen(examen_id):
    examen = Examen.query.get_or_404(examen_id)
    if examen.profesor_id != current_user.id:
        flash('No tienes permiso para ver los resultados de este examen.', 'danger')
        return redirect(url_for('main.dashboard_profesor'))

    if request.method == 'POST':
        for resultado in examen.resultados:
            comentario = request.form.get(f'comentario-{resultado.id}')
            recomendaciones = request.form.get(f'recomendaciones-{resultado.id}')
            resultado.comentario_profesor = comentario
            resultado.recomendaciones = recomendaciones
        db.session.commit()
        flash('Comentarios guardados exitosamente.', 'success')
        return redirect(url_for('main.profesor_resultados_examen', examen_id=examen.id))

    resultados = ExamenResultado.query.filter_by(examen_id=examen.id).all()
    return render_template('profesor/resultados_examen.html', examen=examen, resultados=resultados)
