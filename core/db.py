"""Capa de datos de The Reset.

Funciona con SQLite (desarrollo local) o PostgreSQL (producción, vía DATABASE_URL); ver core/conexion.py.
Todas las funciones validan sus entradas y lanzan ValidationError con un mensaje en español si algo no es válido.
"""
from __future__ import annotations

import json
import os
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path

from .conexion import IntegrityError, abrir, config

DEFAULT_DB = Path(os.environ.get("THE_RESET_DB", Path(__file__).resolve().parent.parent / "data" / "the_reset.db"))
ESTADOS_PROF = ["pendiente", "aprobado", "rechazado", "suspendido"]

ESPECIALIDADES = ["Endocrinología", "Nutrición", "Medicina deportiva", "Medicina general"]
SEXOS = ["Femenino", "Masculino", "Otro", "Prefiero no decir"]
MODALIDADES = ["Virtual", "Presencial"]
ESTADOS_CITA = ["programada", "cancelada", "completada"]
DESENLACES = ["Desconocido", "En recuperación", "Recuperado", "Recuperado con secuelas", "No recuperado"]
GRAVEDAD = ["No", "Sí", "No sé"]
SINTOMAS = ["Náuseas", "Vómito", "Diarrea", "Estreñimiento", "Dolor abdominal", "Reacción en el sitio de inyección",
            "Mareo", "Fatiga", "Disminución del apetito", "Dolor de cabeza", "Otro"]
CATEGORIAS_PLAN = ["Nutrición", "Actividad física", "Seguimiento clínico"]
HORARIOS = ["08:00", "09:00", "10:00", "11:00", "14:00", "15:00", "16:00", "17:00"]
DIAS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]

# Campos de un reporte de evento adverso. Los 4 primeros son los 4 datos mínimos del problema central
# (edad, sexo, peso y desenlace conocido); los demás completan la descripción del evento.
CAMPOS_REPORTE = {
    "edad": "Edad", "sexo": "Sexo", "peso_kg": "Peso", "desenlace": "Desenlace conocido",
    "fecha_evento": "Fecha del evento", "medicamento": "Medicamento declarado", "descripcion": "Descripción del evento",
}
CAMPOS_MINIMOS = ["edad", "sexo", "peso_kg", "desenlace"]


class ValidationError(ValueError):
    """Error de validación con mensaje legible para la interfaz."""


# ------------------------------------------------------------------ conexión y esquema
def connect(path: str | Path | None = None, init: bool = True):
    """Abre la base (PostgreSQL si hay DATABASE_URL; si no, SQLite) y, por defecto, crea o migra el esquema."""
    con = abrir(path or (None if config("DATABASE_URL") else os.environ.get("THE_RESET_DB", DEFAULT_DB)))
    if init:
        init_schema(con)
    return con


@contextmanager
def tx(con):
    with con.transaccion():
        yield con


SCHEMA = """
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    edad INTEGER NOT NULL CHECK (edad BETWEEN 18 AND 100),
    sexo TEXT NOT NULL,
    ciudad TEXT,
    correo_demo TEXT,
    peso_kg REAL CHECK (peso_kg IS NULL OR peso_kg BETWEEN 30 AND 300),
    medicamento_declarado TEXT,
    fecha_registro TEXT NOT NULL,
    es_demo INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS profesionales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    especialidad TEXT NOT NULL,
    experiencia_anios INTEGER NOT NULL,
    perfil TEXT NOT NULL,
    ciudad TEXT NOT NULL,
    modalidades TEXT NOT NULL,
    dias TEXT NOT NULL,
    verificado INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS citas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    profesional_id INTEGER NOT NULL REFERENCES profesionales(id),
    fecha TEXT NOT NULL,
    hora TEXT NOT NULL,
    modalidad TEXT NOT NULL,
    motivo TEXT,
    estado TEXT NOT NULL DEFAULT 'programada',
    veces_reprogramada INTEGER NOT NULL DEFAULT 0,
    creado TEXT NOT NULL,
    actualizado TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_cita_prof ON citas(profesional_id, fecha, hora) WHERE estado = 'programada';
CREATE UNIQUE INDEX IF NOT EXISTS ux_cita_usuario ON citas(usuario_id, fecha, hora) WHERE estado = 'programada';
CREATE TABLE IF NOT EXISTS plan_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    categoria TEXT NOT NULL,
    titulo TEXT NOT NULL,
    descripcion TEXT,
    semana INTEGER NOT NULL,
    completado INTEGER NOT NULL DEFAULT 0,
    fecha_completado TEXT
);
CREATE TABLE IF NOT EXISTS seguimientos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    fecha TEXT NOT NULL,
    peso_kg REAL CHECK (peso_kg IS NULL OR peso_kg BETWEEN 30 AND 300),
    sintomas TEXT,
    energia INTEGER CHECK (energia IS NULL OR energia BETWEEN 1 AND 5),
    observaciones TEXT,
    creado TEXT NOT NULL,
    actualizado TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS reportes_eventos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    fecha_evento TEXT,
    medicamento TEXT,
    edad INTEGER,
    sexo TEXT,
    peso_kg REAL,
    descripcion TEXT,
    sintomas TEXT,
    grave TEXT,
    desenlace TEXT,
    estado TEXT NOT NULL,
    creado TEXT NOT NULL,
    actualizado TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS reportes_historial (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reporte_id INTEGER NOT NULL REFERENCES reportes_eventos(id) ON DELETE CASCADE,
    fecha TEXT NOT NULL,
    cambio TEXT NOT NULL
);
-- Versión 2: programas y rutas de acompañamiento (se crean sin tocar las tablas anteriores)
CREATE TABLE IF NOT EXISTS inscripciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    programa_id TEXT NOT NULL,
    estado TEXT NOT NULL CHECK (estado IN ('activo','pausado','finalizado')),
    fecha_inicio TEXT NOT NULL,
    objetivos TEXT,
    preferencias TEXT,
    medicamento_declarado TEXT,
    fecha_pausa TEXT,
    dias_pausa INTEGER NOT NULL DEFAULT 0,
    creado TEXT NOT NULL,
    actualizado TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_inscripcion_vigente ON inscripciones(usuario_id, programa_id) WHERE estado IN ('activo','pausado');
CREATE TABLE IF NOT EXISTS plan_actividades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    inscripcion_id INTEGER NOT NULL REFERENCES inscripciones(id) ON DELETE CASCADE,
    orden INTEGER NOT NULL,
    semana INTEGER NOT NULL,
    dia INTEGER NOT NULL,
    fecha TEXT NOT NULL,
    categoria TEXT NOT NULL,
    titulo TEXT NOT NULL,
    descripcion TEXT,
    accion TEXT,
    completada INTEGER NOT NULL DEFAULT 0,
    fecha_completada TEXT,
    observacion TEXT
);
CREATE TABLE IF NOT EXISTS plan_notas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    inscripcion_id INTEGER NOT NULL REFERENCES inscripciones(id) ON DELETE CASCADE,
    semana INTEGER NOT NULL,
    fecha TEXT NOT NULL,
    texto TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS cuentas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    correo TEXT NOT NULL UNIQUE,
    clave_hash TEXT NOT NULL,
    rol TEXT NOT NULL CHECK (rol IN ('paciente','profesional','admin')),
    usuario_id INTEGER REFERENCES usuarios(id) ON DELETE CASCADE,
    profesional_id INTEGER REFERENCES profesionales(id) ON DELETE CASCADE,
    activa INTEGER NOT NULL DEFAULT 1,
    debe_cambiar_clave INTEGER NOT NULL DEFAULT 0,
    intentos_fallidos INTEGER NOT NULL DEFAULT 0,
    bloqueada_hasta TEXT,
    consentimiento_fecha TEXT,
    politica_version TEXT,
    creado TEXT NOT NULL,
    ultimo_acceso TEXT
);
CREATE TABLE IF NOT EXISTS auditoria (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cuenta_id INTEGER,
    accion TEXT NOT NULL,
    detalle TEXT,
    fecha TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS plan_registros (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    inscripcion_id INTEGER NOT NULL REFERENCES inscripciones(id) ON DELETE CASCADE,
    tipo TEXT NOT NULL CHECK (tipo IN ('comida','habito','actividad')),
    fecha TEXT NOT NULL,
    detalle TEXT NOT NULL,
    minutos INTEGER,
    nota TEXT,
    creado TEXT NOT NULL
);
"""
SCHEMA_VERSION = 3
# Columnas añadidas en la versión 3 (operación real con cuentas). Se agregan sin borrar datos existentes.
COLUMNAS_V3 = {
    "profesionales": [("registro_profesional", "TEXT"), ("estado", "TEXT NOT NULL DEFAULT 'aprobado'"), ("correo", "TEXT"), ("creado", "TEXT")],
    "usuarios": [("compartir_registros", "INTEGER NOT NULL DEFAULT 1")],
    "citas": [("enlace", "TEXT")],
}


def init_schema(con) -> None:
    """Crea o migra el esquema. Todas las sentencias usan IF NOT EXISTS: una base de una versión anterior
    conserva sus datos y solo recibe las tablas y columnas nuevas."""
    script = SCHEMA if con.motor == "sqlite" else SCHEMA.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
    con.executescript(script)
    for tabla, cols in COLUMNAS_V3.items():
        existentes = con.columnas(tabla)
        for nombre, tipo in cols:
            if nombre not in existentes:
                con.execute(f"ALTER TABLE {tabla} ADD COLUMN {nombre} {tipo}")
    if con.motor == "postgres":
        # Seguridad en Supabase: con RLS activo y sin políticas, la API pública (PostgREST) no puede leer estas tablas.
        # La app se conecta como propietaria de las tablas, así que su acceso directo no cambia.
        for (tabla,) in [tuple(r.values()) for r in con.execute("SELECT tablename FROM pg_tables WHERE schemaname = current_schema()")]:
            con.execute(f'ALTER TABLE "{tabla}" ENABLE ROW LEVEL SECURITY')
    if con.motor == "sqlite":
        if con.execute("PRAGMA user_version").fetchone()[0] < SCHEMA_VERSION:
            con.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    con.commit()


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def rows(cur) -> list[dict]:
    return [dict(r) for r in cur.fetchall()]


# ------------------------------------------------------------------ validaciones comunes
def _txt(v, campo, obligatorio=True, maxlen=500):
    v = (v or "").strip() if isinstance(v, str) or v is None else str(v).strip()
    if obligatorio and not v:
        raise ValidationError(f"El campo «{campo}» es obligatorio.")
    if len(v) > maxlen:
        raise ValidationError(f"El campo «{campo}» admite máximo {maxlen} caracteres.")
    return v or None


def _peso(v, campo="Peso"):
    if v in (None, "", 0, 0.0):
        return None
    try:
        v = float(v)
    except (TypeError, ValueError):
        raise ValidationError(f"«{campo}» debe ser un número.")
    if not 30 <= v <= 300:
        raise ValidationError(f"«{campo}» debe estar entre 30 y 300 kg.")
    return round(v, 1)


def _fecha(v, campo, permitir_futuro=True):
    if v in (None, ""):
        return None
    if isinstance(v, str):
        try:
            v = date.fromisoformat(v)
        except ValueError:
            raise ValidationError(f"«{campo}» no es una fecha válida (AAAA-MM-DD).")
    if isinstance(v, datetime):
        v = v.date()
    if not permitir_futuro and v > date.today():
        raise ValidationError(f"«{campo}» no puede ser una fecha futura.")
    return v.isoformat()


# ------------------------------------------------------------------ usuarios
def crear_usuario(con, nombre, edad, sexo, ciudad=None, correo_demo=None, peso_kg=None, medicamento_declarado=None, es_demo=False, fecha_registro=None,
                  commit=True):
    nombre = _txt(nombre, "Nombre", maxlen=80)
    if len(nombre) < 2:
        raise ValidationError("El nombre debe tener al menos 2 caracteres.")
    try:
        edad = int(edad)
    except (TypeError, ValueError):
        raise ValidationError("La edad debe ser un número entero.")
    if not 18 <= edad <= 100:
        raise ValidationError("The Reset está dirigido a personas adultas: la edad debe estar entre 18 y 100 años.")
    if sexo not in SEXOS:
        raise ValidationError("Seleccione una opción válida de sexo.")
    correo_demo = _txt(correo_demo, "Correo", obligatorio=False, maxlen=120)
    if correo_demo and ("@" not in correo_demo or "." not in correo_demo.split("@")[-1]):
        raise ValidationError("El correo no tiene un formato válido.")
    def insertar():
        cur = con.execute(
            "INSERT INTO usuarios (nombre, edad, sexo, ciudad, correo_demo, peso_kg, medicamento_declarado, fecha_registro, es_demo) VALUES (?,?,?,?,?,?,?,?,?)",
            (nombre, edad, sexo, _txt(ciudad, "Ciudad", False, 60), correo_demo, _peso(peso_kg), _txt(medicamento_declarado, "Medicamento", False, 80),
             fecha_registro or date.today().isoformat(), int(es_demo)))
        crear_plan_base(con, cur.lastrowid)
        return cur.lastrowid
    if not commit:
        return insertar()
    with tx(con):
        uid = insertar()
    return uid


def actualizar_usuario(con, uid, **campos):
    u = obtener_usuario(con, uid)
    if not u:
        raise ValidationError("Usuario no encontrado.")
    nuevo = {**u, **campos}
    if not 18 <= int(nuevo["edad"]) <= 100:
        raise ValidationError("La edad debe estar entre 18 y 100 años.")
    if nuevo["sexo"] not in SEXOS:
        raise ValidationError("Seleccione una opción válida de sexo.")
    with tx(con):
        con.execute("UPDATE usuarios SET nombre=?, edad=?, sexo=?, ciudad=?, correo_demo=?, peso_kg=?, medicamento_declarado=? WHERE id=?",
                    (_txt(nuevo["nombre"], "Nombre", maxlen=80), int(nuevo["edad"]), nuevo["sexo"], _txt(nuevo.get("ciudad"), "Ciudad", False, 60),
                     _txt(nuevo.get("correo_demo"), "Correo", False, 120), _peso(nuevo.get("peso_kg")),
                     _txt(nuevo.get("medicamento_declarado"), "Medicamento", False, 80), uid))


def obtener_usuario(con, uid):
    r = con.execute("SELECT * FROM usuarios WHERE id=?", (uid,)).fetchone()
    return dict(r) if r else None


def listar_usuarios(con):
    return rows(con.execute("SELECT * FROM usuarios ORDER BY es_demo DESC, id"))


# ------------------------------------------------------------------ profesionales
def _validar_prof(nombre, especialidad, experiencia_anios, perfil, ciudad, modalidades, dias):
    nombre = _txt(nombre, "Nombre", maxlen=80)
    if especialidad not in ESPECIALIDADES:
        raise ValidationError("Especialidad no válida.")
    try:
        exp = int(experiencia_anios)
    except (TypeError, ValueError):
        raise ValidationError("Los años de experiencia deben ser un número.")
    if not 0 <= exp <= 60:
        raise ValidationError("Los años de experiencia deben estar entre 0 y 60.")
    if not modalidades or any(m not in MODALIDADES for m in modalidades):
        raise ValidationError("Elija al menos una modalidad de atención.")
    if not dias or any(d not in DIAS for d in dias):
        raise ValidationError("Elija al menos un día de atención.")
    return (nombre, especialidad, exp, _txt(perfil, "Perfil profesional", True, 400), _txt(ciudad, "Ciudad", True, 60),
            ",".join(modalidades), ",".join(d for d in DIAS if d in dias))


def crear_profesional(con, nombre, especialidad, experiencia_anios, perfil, ciudad, modalidades, dias, registro_profesional=None,
                      correo=None, estado="aprobado", commit=True):
    vals = _validar_prof(nombre, especialidad, experiencia_anios, perfil, ciudad, modalidades, dias)
    if estado not in ESTADOS_PROF:
        raise ValidationError("Estado no válido.")
    sql = ("INSERT INTO profesionales (nombre, especialidad, experiencia_anios, perfil, ciudad, modalidades, dias, registro_profesional, correo, estado, creado) "
           "VALUES (?,?,?,?,?,?,?,?,?,?,?)")
    args = (*vals, _txt(registro_profesional, "Registro profesional", False, 40), correo, estado, now())
    if not commit:
        return con.execute(sql, args).lastrowid
    with tx(con):
        cur = con.execute(sql, args)
    return cur.lastrowid


def actualizar_profesional(con, pid, nombre, especialidad, experiencia_anios, perfil, ciudad, modalidades, dias):
    vals = _validar_prof(nombre, especialidad, experiencia_anios, perfil, ciudad, modalidades, dias)
    with tx(con):
        con.execute("UPDATE profesionales SET nombre=?, especialidad=?, experiencia_anios=?, perfil=?, ciudad=?, modalidades=?, dias=? WHERE id=?", (*vals, pid))


def cambiar_estado_profesional(con, pid, estado):
    if estado not in ESTADOS_PROF:
        raise ValidationError("Estado no válido.")
    with tx(con):
        con.execute("UPDATE profesionales SET estado=?, verificado=? WHERE id=?", (estado, int(estado == "aprobado"), pid))


def listar_profesionales(con, especialidad=None, estado="aprobado"):
    """Por defecto solo devuelve profesionales aprobados por el administrador (los que aparecen en el directorio)."""
    q, args = "SELECT * FROM profesionales WHERE 1=1", []
    if estado:
        q += " AND estado=?"; args.append(estado)
    if especialidad and especialidad != "Todas":
        q += " AND especialidad=?"; args.append(especialidad)
    return rows(con.execute(q + " ORDER BY especialidad, nombre", args))


def obtener_profesional(con, pid):
    r = con.execute("SELECT * FROM profesionales WHERE id=?", (pid,)).fetchone()
    return dict(r) if r else None


def atiende_ese_dia(prof, fecha: date) -> bool:
    return DIAS[fecha.weekday()] in prof["dias"].split(",")


def horarios_disponibles(con, pid, fecha, usuario_id=None, excluir_cita=None):
    """Horarios libres del profesional en la fecha (y sin choque con otras citas del usuario)."""
    prof = obtener_profesional(con, pid)
    f = date.fromisoformat(_fecha(fecha, "Fecha"))
    if not prof or not atiende_ese_dia(prof, f) or f < date.today():
        return []
    excl = excluir_cita or -1
    ocupados = {r["hora"] for r in con.execute("SELECT hora FROM citas WHERE profesional_id=? AND fecha=? AND estado='programada' AND id<>?",
                                                (pid, f.isoformat(), excl))}
    if usuario_id:
        ocupados |= {r["hora"] for r in con.execute("SELECT hora FROM citas WHERE usuario_id=? AND fecha=? AND estado='programada' AND id<>?",
                                                     (usuario_id, f.isoformat(), excl))}
    libres = [h for h in HORARIOS if h not in ocupados]
    if f == date.today():
        libres = [h for h in libres if h > datetime.now().strftime("%H:%M")]
    return libres


# ------------------------------------------------------------------ citas
def _validar_cita(con, usuario_id, pid, fecha, hora, modalidad, excluir=None):
    prof = obtener_profesional(con, pid)
    if not prof or prof.get("estado", "aprobado") != "aprobado":
        raise ValidationError("Seleccione un profesional válido.")
    if not obtener_usuario(con, usuario_id):
        raise ValidationError("Usuario no encontrado.")
    f = _fecha(fecha, "Fecha")
    if date.fromisoformat(f) < date.today():
        raise ValidationError("No se pueden agendar citas en fechas pasadas.")
    if not atiende_ese_dia(prof, date.fromisoformat(f)):
        raise ValidationError(f"{prof['nombre']} no atiende ese día (atiende: {prof['dias'].replace(',', ', ')}).")
    if modalidad not in prof["modalidades"].split(","):
        raise ValidationError(f"Modalidad no disponible con este profesional ({prof['modalidades'].replace(',', ', ')}).")
    if hora not in horarios_disponibles(con, pid, f, usuario_id, excluir):
        raise ValidationError("Ese horario ya no está disponible o choca con otra cita suya. Elija otro horario.")
    return f


def crear_cita(con, usuario_id, pid, fecha, hora, modalidad, motivo=None):
    f = _validar_cita(con, usuario_id, pid, fecha, hora, modalidad)
    try:
        with tx(con):
            cur = con.execute("INSERT INTO citas (usuario_id, profesional_id, fecha, hora, modalidad, motivo, estado, creado, actualizado) VALUES (?,?,?,?,?,?,'programada',?,?)",
                              (usuario_id, pid, f, hora, modalidad, _txt(motivo, "Motivo", False, 300), now(), now()))
    except IntegrityError:
        raise ValidationError("Ya existe una cita en ese horario (reserva duplicada).")
    return cur.lastrowid


def obtener_cita(con, cid):
    r = con.execute("SELECT * FROM citas WHERE id=?", (cid,)).fetchone()
    return dict(r) if r else None


def reprogramar_cita(con, cid, nueva_fecha, nueva_hora, modalidad=None):
    c = obtener_cita(con, cid)
    if not c or c["estado"] != "programada":
        raise ValidationError("Solo se pueden reprogramar citas programadas.")
    modalidad = modalidad or c["modalidad"]
    f = _validar_cita(con, c["usuario_id"], c["profesional_id"], nueva_fecha, nueva_hora, modalidad, excluir=cid)
    try:
        with tx(con):
            con.execute("UPDATE citas SET fecha=?, hora=?, modalidad=?, veces_reprogramada=veces_reprogramada+1, actualizado=? WHERE id=?",
                        (f, nueva_hora, modalidad, now(), cid))
    except IntegrityError:
        raise ValidationError("Ese horario ya fue reservado.")


def cancelar_cita(con, cid):
    c = obtener_cita(con, cid)
    if not c or c["estado"] != "programada":
        raise ValidationError("Solo se pueden cancelar citas programadas.")
    with tx(con):
        con.execute("UPDATE citas SET estado='cancelada', actualizado=? WHERE id=?", (now(), cid))


def listar_citas(con, usuario_id=None, solo_futuras=False, estado=None, profesional_id=None):
    q = ("SELECT c.*, p.nombre AS profesional, p.especialidad, u.nombre AS paciente FROM citas c JOIN profesionales p ON p.id=c.profesional_id "
         "JOIN usuarios u ON u.id=c.usuario_id WHERE 1=1")
    args = []
    if usuario_id:
        q += " AND c.usuario_id=?"; args.append(usuario_id)
    if profesional_id:
        q += " AND c.profesional_id=?"; args.append(profesional_id)
    if estado:
        q += " AND c.estado=?"; args.append(estado)
    if solo_futuras:
        q += " AND c.fecha>=?"; args.append(date.today().isoformat())
    q += " ORDER BY c.fecha, c.hora"
    return rows(con.execute(q, args))


def completar_cita(con, cid, profesional_id):
    c = obtener_cita(con, cid)
    if not c or c["profesional_id"] != profesional_id:
        raise ValidationError("Cita no encontrada.")
    if c["estado"] != "programada":
        raise ValidationError("Solo se pueden marcar como atendidas las citas programadas.")
    with tx(con):
        con.execute("UPDATE citas SET estado='completada', actualizado=? WHERE id=?", (now(), cid))


def guardar_enlace(con, cid, profesional_id, enlace):
    c = obtener_cita(con, cid)
    if not c or c["profesional_id"] != profesional_id:
        raise ValidationError("Cita no encontrada.")
    enlace = _txt(enlace, "Enlace", False, 300)
    if enlace and not enlace.startswith("https://"):
        raise ValidationError("El enlace de la consulta virtual debe empezar por https://")
    with tx(con):
        con.execute("UPDATE citas SET enlace=?, actualizado=? WHERE id=?", (enlace, now(), cid))


def pacientes_de_profesional(con, pid):
    """Pacientes que tienen o tuvieron al menos una cita con el profesional."""
    return rows(con.execute(
        "SELECT u.id, u.nombre, u.edad, u.sexo, u.ciudad, u.medicamento_declarado, u.compartir_registros, "
        "COUNT(c.id) AS citas, MAX(c.fecha) AS ultima_cita FROM citas c JOIN usuarios u ON u.id=c.usuario_id "
        "WHERE c.profesional_id=? GROUP BY u.id, u.nombre, u.edad, u.sexo, u.ciudad, u.medicamento_declarado, u.compartir_registros ORDER BY u.nombre", (pid,)))


def profesional_atiende_a(con, pid, uid) -> bool:
    return con.execute("SELECT 1 FROM citas WHERE profesional_id=? AND usuario_id=?", (pid, uid)).fetchone() is not None


def eliminar_usuario(con, uid):
    """Derecho de supresión: borra al usuario y, en cascada, sus citas, planes, seguimientos y reportes."""
    with tx(con):
        con.execute("DELETE FROM usuarios WHERE id=?", (uid,))


def exportar_datos(con, uid) -> str:
    """Todos los datos del usuario en JSON (derecho de acceso, Ley 1581 de 2012)."""
    datos = {
        "perfil": obtener_usuario(con, uid),
        "citas": listar_citas(con, uid),
        "seguimientos": listar_seguimientos(con, uid),
        "reportes_eventos": listar_reportes(con, uid),
        "programas": rows(con.execute("SELECT * FROM inscripciones WHERE usuario_id=?", (uid,))),
        "actividades": rows(con.execute("SELECT a.* FROM plan_actividades a JOIN inscripciones i ON i.id=a.inscripcion_id WHERE i.usuario_id=?", (uid,))),
        "registros": rows(con.execute("SELECT r.* FROM plan_registros r JOIN inscripciones i ON i.id=r.inscripcion_id WHERE i.usuario_id=?", (uid,))),
        "exportado": now(),
    }
    return json.dumps(datos, ensure_ascii=False, indent=2, default=str)


def actualizar_compartir(con, uid, compartir: bool):
    with tx(con):
        con.execute("UPDATE usuarios SET compartir_registros=? WHERE id=?", (int(bool(compartir)), uid))


# ------------------------------------------------------------------ plan de acompañamiento (ejemplos educativos)
PLAN_BASE = [
    ("Nutrición", "Registrar comidas durante 3 días", "Anotar qué come y a qué hora para conversarlo con su nutricionista.", 1),
    ("Nutrición", "Hidratación diaria", "Llevar registro de los vasos de agua del día.", 1),
    ("Nutrición", "Revisar el plan con el nutricionista", "Llevar sus registros a la cita para ajustar el plan.", 2),
    ("Actividad física", "Caminar 3 veces esta semana", "Actividad ligera, según lo que su profesional considere adecuado.", 1),
    ("Actividad física", "Registrar minutos de actividad", "Anotar duración y tipo de actividad.", 2),
    ("Actividad física", "Valoración con medicina deportiva", "Definir con el profesional un plan de ejercicio seguro.", 3),
    ("Seguimiento clínico", "Registrar peso semanal", "Un registro por semana en la sección Seguimiento de salud.", 1),
    ("Seguimiento clínico", "Anotar síntomas y cómo evolucionan", "Si aparece un síntoma, registrar también cómo termina (desenlace).", 2),
    ("Seguimiento clínico", "Asistir a control médico", "Cita de seguimiento con su médico tratante.", 4),
]


def crear_plan_base(con, uid, commit=True):
    con.executemany("INSERT INTO plan_items (usuario_id, categoria, titulo, descripcion, semana) VALUES (?,?,?,?,?)",
                    [(uid, c, t, d, s) for c, t, d, s in PLAN_BASE])


def listar_plan(con, uid):
    return rows(con.execute("SELECT * FROM plan_items WHERE usuario_id=? ORDER BY semana, categoria, id", (uid,)))


def marcar_item(con, item_id, completado: bool):
    with tx(con):
        con.execute("UPDATE plan_items SET completado=?, fecha_completado=? WHERE id=?",
                    (int(completado), date.today().isoformat() if completado else None, item_id))


def progreso_plan(con, uid):
    items = listar_plan(con, uid)
    out = {"total": len(items), "completados": sum(i["completado"] for i in items)}
    out["pct"] = round(100 * out["completados"] / out["total"], 1) if out["total"] else 0.0
    out["por_categoria"] = {c: {"total": sum(1 for i in items if i["categoria"] == c), "completados": sum(i["completado"] for i in items if i["categoria"] == c)}
                            for c in CATEGORIAS_PLAN}
    return out


# ------------------------------------------------------------------ seguimiento de salud
def _sint(v):
    if not v:
        return None
    lst = v if isinstance(v, (list, tuple)) else [s.strip() for s in str(v).split(",")]
    malos = [s for s in lst if s not in SINTOMAS]
    if malos:
        raise ValidationError(f"Síntomas no válidos: {', '.join(malos)}")
    return ",".join(lst)


def crear_seguimiento(con, uid, fecha, peso_kg=None, sintomas=None, energia=None, observaciones=None):
    f = _fecha(fecha, "Fecha", permitir_futuro=False)
    if not f:
        raise ValidationError("La fecha es obligatoria.")
    peso, s = _peso(peso_kg), _sint(sintomas)
    obs = _txt(observaciones, "Observaciones", False, 500)
    if peso is None and not s and not obs and energia is None:
        raise ValidationError("Registre al menos un dato: peso, síntomas, energía u observaciones.")
    if energia is not None and not 1 <= int(energia) <= 5:
        raise ValidationError("La energía debe estar entre 1 y 5.")
    with tx(con):
        cur = con.execute("INSERT INTO seguimientos (usuario_id, fecha, peso_kg, sintomas, energia, observaciones, creado, actualizado) VALUES (?,?,?,?,?,?,?,?)",
                          (uid, f, peso, s, energia, obs, now(), now()))
    return cur.lastrowid


def actualizar_seguimiento(con, sid, fecha, peso_kg=None, sintomas=None, energia=None, observaciones=None):
    if not con.execute("SELECT 1 FROM seguimientos WHERE id=?", (sid,)).fetchone():
        raise ValidationError("Registro no encontrado.")
    f = _fecha(fecha, "Fecha", permitir_futuro=False)
    with tx(con):
        con.execute("UPDATE seguimientos SET fecha=?, peso_kg=?, sintomas=?, energia=?, observaciones=?, actualizado=? WHERE id=?",
                    (f, _peso(peso_kg), _sint(sintomas), energia, _txt(observaciones, "Observaciones", False, 500), now(), sid))


def eliminar_seguimiento(con, sid):
    with tx(con):
        con.execute("DELETE FROM seguimientos WHERE id=?", (sid,))


def listar_seguimientos(con, uid):
    return rows(con.execute("SELECT * FROM seguimientos WHERE usuario_id=? ORDER BY fecha, id", (uid,)))


# ------------------------------------------------------------------ reportes de eventos adversos
def completitud(reporte: dict) -> dict:
    """Qué campos están completos. 'Desenlace' cuenta solo si es distinto de 'Desconocido'."""
    def ok(k):
        v = reporte.get(k)
        if k == "desenlace":
            return bool(v) and v != "Desconocido"
        return v not in (None, "", 0)
    estado = {k: ok(k) for k in CAMPOS_REPORTE}
    n = sum(estado.values())
    return {"campos": estado, "completos": n, "total": len(CAMPOS_REPORTE), "pct": round(100 * n / len(CAMPOS_REPORTE), 1),
            "minimos_ok": all(estado[k] for k in CAMPOS_MINIMOS), "faltantes": [CAMPOS_REPORTE[k] for k, v in estado.items() if not v]}


def _limpiar_reporte(d):
    out = {
        "fecha_evento": _fecha(d.get("fecha_evento"), "Fecha del evento", permitir_futuro=False),
        "medicamento": _txt(d.get("medicamento"), "Medicamento", False, 80),
        "edad": None, "sexo": d.get("sexo") or None, "peso_kg": _peso(d.get("peso_kg")),
        "descripcion": _txt(d.get("descripcion"), "Descripción", False, 1000), "sintomas": _sint(d.get("sintomas")),
        "grave": d.get("grave") or None, "desenlace": d.get("desenlace") or None,
    }
    if d.get("edad") not in (None, "", 0):
        try:
            out["edad"] = int(d["edad"])
        except (TypeError, ValueError):
            raise ValidationError("La edad debe ser un número entero.")
        if not 18 <= out["edad"] <= 100:
            raise ValidationError("La edad debe estar entre 18 y 100 años.")
    if out["sexo"] and out["sexo"] not in SEXOS:
        raise ValidationError("Sexo no válido.")
    if out["grave"] and out["grave"] not in GRAVEDAD:
        raise ValidationError("Valor de gravedad no válido.")
    if out["desenlace"] and out["desenlace"] not in DESENLACES:
        raise ValidationError("Desenlace no válido.")
    return out


def guardar_reporte(con, uid, datos: dict, como_borrador: bool):
    """Crea un reporte. Si no es borrador, exige los 7 campos completos (incluido un desenlace conocido)."""
    d = _limpiar_reporte(datos)
    comp = completitud(d)
    if not como_borrador and comp["completos"] < comp["total"]:
        raise ValidationError("Para guardarlo como reporte completo faltan: " + ", ".join(comp["faltantes"]) + ". Puede guardarlo como borrador.")
    if not any(v for k, v in d.items() if k in ("descripcion", "sintomas", "medicamento")):
        raise ValidationError("Describa al menos el evento, un síntoma o el medicamento para crear el registro.")
    estado = "completo" if comp["completos"] == comp["total"] else "borrador"
    with tx(con):
        cur = con.execute("""INSERT INTO reportes_eventos (usuario_id, fecha_evento, medicamento, edad, sexo, peso_kg, descripcion, sintomas, grave, desenlace, estado, creado, actualizado)
                             VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                          (uid, d["fecha_evento"], d["medicamento"], d["edad"], d["sexo"], d["peso_kg"], d["descripcion"], d["sintomas"], d["grave"], d["desenlace"], estado, now(), now()))
        rid = cur.lastrowid
        con.execute("INSERT INTO reportes_historial (reporte_id, fecha, cambio) VALUES (?,?,?)",
                    (rid, now(), f"Creado como {estado} ({comp['completos']}/{comp['total']} campos)"))
    return rid


def actualizar_reporte(con, rid, cambios: dict):
    """Actualiza campos (por ejemplo el desenlace). El estado se recalcula: pasa a 'completo' cuando están los 7 campos."""
    r = obtener_reporte(con, rid)
    if not r:
        raise ValidationError("Reporte no encontrado.")
    d = _limpiar_reporte({**r, **cambios})
    comp = completitud(d)
    estado = "completo" if comp["completos"] == comp["total"] else "borrador"
    difs = [f"{CAMPOS_REPORTE.get(k, k)}: {r.get(k) or '—'} → {d[k] or '—'}" for k in d if (r.get(k) or None) != (d[k] or None)]
    if not difs:
        raise ValidationError("No hay cambios para guardar.")
    with tx(con):
        con.execute("""UPDATE reportes_eventos SET fecha_evento=?, medicamento=?, edad=?, sexo=?, peso_kg=?, descripcion=?, sintomas=?, grave=?, desenlace=?, estado=?, actualizado=? WHERE id=?""",
                    (d["fecha_evento"], d["medicamento"], d["edad"], d["sexo"], d["peso_kg"], d["descripcion"], d["sintomas"], d["grave"], d["desenlace"], estado, now(), rid))
        con.execute("INSERT INTO reportes_historial (reporte_id, fecha, cambio) VALUES (?,?,?)",
                    (rid, now(), "; ".join(difs) + f" · estado: {estado}"))
    return estado


def obtener_reporte(con, rid):
    r = con.execute("SELECT * FROM reportes_eventos WHERE id=?", (rid,)).fetchone()
    return dict(r) if r else None


def listar_reportes(con, uid=None):
    if uid:
        return rows(con.execute("SELECT * FROM reportes_eventos WHERE usuario_id=? ORDER BY creado DESC, id DESC", (uid,)))
    return rows(con.execute("SELECT * FROM reportes_eventos ORDER BY creado DESC, id DESC"))


def historial_reporte(con, rid):
    return rows(con.execute("SELECT * FROM reportes_historial WHERE reporte_id=? ORDER BY id", (rid,)))


def eliminar_reporte(con, rid):
    r = obtener_reporte(con, rid)
    if not r:
        raise ValidationError("Reporte no encontrado.")
    if r["estado"] != "borrador":
        raise ValidationError("Solo se pueden eliminar borradores; los reportes completos se conservan para trazabilidad.")
    with tx(con):
        con.execute("DELETE FROM reportes_eventos WHERE id=?", (rid,))


# ------------------------------------------------------------------ indicadores de la app (solo datos de demostración)
def indicadores(con, uid=None):
    reps = listar_reportes(con, uid)
    comps = [completitud(r) for r in reps]
    n = len(reps)
    pct = lambda k: round(100 * sum(c["campos"][k] for c in comps) / n, 1) if n else 0.0
    citas = listar_citas(con, uid)
    segs = rows(con.execute("SELECT * FROM seguimientos" + (" WHERE usuario_id=?" if uid else ""), ((uid,) if uid else ())))
    return {
        "reportes": n,
        "reportes_completos": sum(r["estado"] == "completo" for r in reps),
        "borradores": sum(r["estado"] == "borrador" for r in reps),
        "pct_reportes_completos": round(100 * sum(r["estado"] == "completo" for r in reps) / n, 1) if n else 0.0,
        "pct_4_minimos": round(100 * sum(c["minimos_ok"] for c in comps) / n, 1) if n else 0.0,
        "pct_con_peso": pct("peso_kg"), "pct_con_edad": pct("edad"), "pct_con_sexo": pct("sexo"), "pct_con_desenlace": pct("desenlace"),
        "citas_programadas": sum(c["estado"] == "programada" for c in citas),
        "citas_canceladas": sum(c["estado"] == "cancelada" for c in citas),
        "citas_total": len(citas),
        "seguimientos": len(segs),
        "seguimientos_con_peso": sum(s["peso_kg"] is not None for s in segs),
    }


def reset_db(path: str | Path | None = None):
    """Solo para pruebas locales con SQLite."""
    p = Path(path) if path else DEFAULT_DB
    if p.exists():
        p.unlink()
