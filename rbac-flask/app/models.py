from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

from .extensions import db, login_manager

ROLES = ("admin", "profesor", "estudiante")
NIVELES_DIFICULTAD = ("basico", "intermedio", "avanzado")

# Tabla de asociación para relación muchos a muchos
estudiante_examen = db.Table('estudiante_examen',
    db.Column('estudiante_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('examen_id', db.Integer, db.ForeignKey('examenes.id'), primary_key=True),
    db.Column('asignado_en', db.DateTime, default=datetime.utcnow)
)


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="estudiante")
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    examenes_creados = db.relationship('Examen', backref='profesor', lazy=True, foreign_keys='Examen.profesor_id')
    examenes_asignados = db.relationship('Examen', secondary=estudiante_examen, backref=db.backref('estudiantes', lazy='dynamic'))

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == "admin"

    @property
    def is_profesor(self):
        return self.role == "profesor"

    @property
    def is_estudiante(self):
        return self.role == "estudiante"


class Categoria(db.Model):
    __tablename__ = "categorias"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False, unique=True)
    descripcion = db.Column(db.Text)
    color = db.Column(db.String(7), default="#00695c")  # Color hex para UI
    icono = db.Column(db.String(50))  # Emoji o clase CSS
    activo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    examenes = db.relationship('Examen', backref='categoria', lazy=True)
    
    def __repr__(self):
        return f'<Categoria {self.nombre}>'


class Examen(db.Model):
    __tablename__ = "examenes"
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    duracion_minutos = db.Column(db.Integer, default=60)
    fecha_limite = db.Column(db.DateTime)
    publicado = db.Column(db.Boolean, default=False)
    profesor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categorias.id'))
    
    # Configuraciones avanzadas
    intentos_maximos = db.Column(db.Integer, default=1)  # número de intentos permitidos
    mostrar_respuestas = db.Column(db.Boolean, default=True)  # mostrar respuestas correctas después
    barajar_preguntas = db.Column(db.Boolean, default=False)  # randomizar orden preguntas
    calificacion_minima = db.Column(db.Float, default=60.0)  # porcentaje mínimo para aprobar
    
    # Relaciones
    preguntas = db.relationship('Pregunta', backref='examen', lazy=True, cascade='all, delete-orphan')
    resultados = db.relationship('ExamenResultado', backref='examen', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Examen {self.titulo}>'


class Pregunta(db.Model):
    __tablename__ = "preguntas"
    id = db.Column(db.Integer, primary_key=True)
    examen_id = db.Column(db.Integer, db.ForeignKey('examenes.id'), nullable=False)
    texto = db.Column(db.Text, nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # opcion_multiple, verdadero_falso, abierta
    opciones = db.Column(db.Text)  # JSON string para opciones múltiples
    respuesta_correcta = db.Column(db.Text)
    puntos = db.Column(db.Integer, default=1)
    orden = db.Column(db.Integer, default=0)
    
    # Características estilo ICFES
    nivel_dificultad = db.Column(db.String(20), default="basico")  # basico, intermedio, avanzado
    tiempo_estimado = db.Column(db.Integer, default=60)  # segundos
    explicacion = db.Column(db.Text)  # Explicación de la respuesta correcta
    imagen_url = db.Column(db.String(255))  # Ruta a imagen adjunta
    
    # Relaciones
    respuestas = db.relationship('Respuesta', backref='pregunta', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Pregunta {self.id}: {self.texto[:30]}>'


class Respuesta(db.Model):
    __tablename__ = "respuestas"
    id = db.Column(db.Integer, primary_key=True)
    examen_id = db.Column(db.Integer, db.ForeignKey('examenes.id'), nullable=False)
    estudiante_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    pregunta_id = db.Column(db.Integer, db.ForeignKey('preguntas.id'), nullable=False)
    respuesta_texto = db.Column(db.Text)
    es_correcta = db.Column(db.Boolean, default=False)
    puntos_obtenidos = db.Column(db.Float, default=0)
    fecha_respuesta = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Respuesta {self.id}>'


class ExamenResultado(db.Model):
    __tablename__ = "examenes_resultados"
    id = db.Column(db.Integer, primary_key=True)
    examen_id = db.Column(db.Integer, db.ForeignKey('examenes.id'), nullable=False)
    estudiante_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    calificacion = db.Column(db.Float, default=0)
    total_puntos = db.Column(db.Float, default=0)
    fecha_inicio = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_fin = db.Column(db.DateTime)
    completado = db.Column(db.Boolean, default=False)
    tiempo_utilizado = db.Column(db.Integer, default=0)  # en segundos
    
    # Campos FASE 1 - Comentarios del Profesor
    comentario_profesor = db.Column(db.Text)
    recomendaciones = db.Column(db.Text)
    fecha_presentacion = db.Column(db.DateTime)
    
    # FASE 3 - Modo Práctica y Revisión
    es_modo_practica = db.Column(db.Boolean, default=False)  # Sin calificación
    solicitud_revision = db.Column(db.Boolean, default=False)
    revision_completada = db.Column(db.Boolean, default=False)
    fecha_solicitud_revision = db.Column(db.DateTime)
    
    # Relación con estudiante y respuestas
    estudiante = db.relationship('User', foreign_keys=[estudiante_id], backref='mis_resultados')
    respuestas = db.relationship('Respuesta', 
                                 primaryjoin='and_(ExamenResultado.examen_id==Respuesta.examen_id, '
                                            'ExamenResultado.estudiante_id==Respuesta.estudiante_id)',
                                 foreign_keys='[Respuesta.examen_id, Respuesta.estudiante_id]',
                                 viewonly=True)
    
    def __repr__(self):
        return f'<ExamenResultado {self.id}>'


# FASE 2 - Modelo para Notificaciones
class Notificacion(db.Model):
    __tablename__ = "notificaciones"
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    titulo = db.Column(db.String(200), nullable=False)
    mensaje = db.Column(db.Text, nullable=False)
    tipo = db.Column(db.String(50), default="info")  # info, warning, success, danger
    leida = db.Column(db.Boolean, default=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    url_destino = db.Column(db.String(255))  # URL para redirigir al hacer clic
    
    # Relación
    usuario = db.relationship('User', backref='notificaciones')
    
    def __repr__(self):
        return f'<Notificacion {self.id}: {self.titulo}>'


# FASE 3 - Modelo para Certificados
class Certificado(db.Model):
    __tablename__ = "certificados"
    id = db.Column(db.Integer, primary_key=True)
    estudiante_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    examen_id = db.Column(db.Integer, db.ForeignKey('examenes.id'), nullable=False)
    resultado_id = db.Column(db.Integer, db.ForeignKey('examenes_resultados.id'), nullable=False)
    codigo_verificacion = db.Column(db.String(100), unique=True, nullable=False)
    fecha_emision = db.Column(db.DateTime, default=datetime.utcnow)
    calificacion = db.Column(db.Float, nullable=False)
    archivo_pdf = db.Column(db.String(255))  # Ruta al PDF generado
    
    # Relaciones
    estudiante = db.relationship('User', backref='certificados')
    examen = db.relationship('Examen', backref='certificados')
    resultado = db.relationship('ExamenResultado', backref='certificado', uselist=False)
    
    def __repr__(self):
        return f'<Certificado {self.codigo_verificacion}>'


@login_manager.user_loader
def load_user(user_id):  # pragma: no cover
    return User.query.get(int(user_id))
