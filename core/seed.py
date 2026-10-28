"""Datos de DEMOSTRACIÓN. Todas las personas son ficticias; ningún dato corresponde a pacientes o profesionales reales."""
from __future__ import annotations

from datetime import date, timedelta

from . import db, planes

PROFESIONALES = [
    ("Dra. Valeria Ríos (ficticia)", "Endocrinología", 12, "Endocrinóloga demo. Acompaña tratamientos metabólicos supervisados y control de diabetes tipo 2.", "Bogotá", ["Virtual", "Presencial"], ["Lun", "Mié", "Vie"]),
    ("Dr. Andrés Calderón (ficticio)", "Endocrinología", 8, "Endocrinólogo demo. Seguimiento de pacientes con obesidad y resistencia a la insulina.", "Medellín", ["Virtual"], ["Mar", "Jue"]),
    ("Nut. Camila Herrera (ficticia)", "Nutrición", 7, "Nutricionista demo. Planes de alimentación y educación nutricional.", "Bogotá", ["Virtual", "Presencial"], ["Lun", "Mar", "Jue"]),
    ("Nut. Mateo Salazar (ficticio)", "Nutrición", 5, "Nutricionista demo enfocado en hábitos sostenibles.", "Cali", ["Virtual"], ["Mié", "Vie", "Sáb"]),
    ("Dra. Sofía Paredes (ficticia)", "Medicina deportiva", 10, "Médica deportóloga demo. Prescripción segura de actividad física.", "Bogotá", ["Presencial", "Virtual"], ["Mar", "Jue", "Sáb"]),
    ("Dr. Julián Ortega (ficticio)", "Medicina deportiva", 6, "Médico deportólogo demo. Programas de inicio gradual de ejercicio.", "Barranquilla", ["Virtual"], ["Lun", "Mié"]),
    ("Dra. Natalia Gómez (ficticia)", "Medicina general", 9, "Médica general demo. Controles periódicos y coordinación con especialistas.", "Bogotá", ["Virtual", "Presencial"], ["Lun", "Mar", "Mié", "Jue", "Vie"]),
    ("Dr. Felipe Rojas (ficticio)", "Medicina general", 4, "Médico general demo. Atención virtual y seguimiento.", "Bucaramanga", ["Virtual"], ["Mar", "Vie"]),
]


def proximo_dia(prof, desde: date, salto=0):
    d = desde
    hallados = 0
    for _ in range(60):
        d += timedelta(days=1)
        if db.atiende_ese_dia(prof, d):
            if hallados == salto:
                return d
            hallados += 1
    raise RuntimeError("Sin días disponibles")


def poblar(con) -> bool:
    """Carga los datos de ejemplo si aún no existen (aunque ya haya cuentas reales). Devuelve True si cargó datos."""
    if con.execute("SELECT COUNT(*) FROM usuarios WHERE es_demo=1").fetchone()[0] > 0:
        return False
    pids = [db.crear_profesional(con, *p) for p in PROFESIONALES]
    hoy = date.today()
    u1 = db.crear_usuario(con, "Ana Demo", 42, "Femenino", ciudad="Bogotá", correo_demo="ana.demo@ejemplo.com", peso_kg=88.0,
                          medicamento_declarado="Mounjaro (tirzepatida)", es_demo=True, fecha_registro=(hoy - timedelta(days=42)).isoformat())
    u2 = db.crear_usuario(con, "Carlos Demo", 55, "Masculino", ciudad="Medellín", es_demo=True, fecha_registro=(hoy - timedelta(days=20)).isoformat())
    # Citas futuras en días válidos para cada profesional
    for uid, pid, salto, hora, mod, motivo in [(u1, pids[0], 0, "09:00", "Virtual", "Control de seguimiento"), (u1, pids[2], 1, "10:00", "Virtual", "Revisión del plan de alimentación"),
                                               (u1, pids[4], 2, "15:00", "Presencial", "Valoración para actividad física"), (u2, pids[6], 0, "11:00", "Virtual", "Primera consulta")]:
        p = db.obtener_profesional(con, pid)
        db.crear_cita(con, uid, pid, proximo_dia(p, hoy, salto), hora, mod, motivo)
    # Una cita cancelada para mostrar el historial
    p = db.obtener_profesional(con, pids[6])
    c = db.crear_cita(con, u1, pids[6], proximo_dia(p, hoy, 3), "16:00", "Virtual", "Control general")
    db.cancelar_cita(con, c)
    # Seguimiento semanal de la usuaria demo (6 semanas)
    pesos = [88.0, 87.4, 86.9, 86.1, None, 85.2]
    sint = ["Náuseas", "Náuseas,Disminución del apetito", None, "Estreñimiento", "Fatiga", None]
    for i, (w, s_) in enumerate(zip(pesos, sint)):
        db.crear_seguimiento(con, u1, hoy - timedelta(days=35 - 7 * i), peso_kg=w, sintomas=s_, energia=[3, 3, 4, 4, 3, 4][i],
                             observaciones="Registro de demostración" if w else "Sin báscula esta semana")
    db.crear_seguimiento(con, u2, hoy - timedelta(days=7), peso_kg=101.5, energia=3, observaciones="Registro inicial de demostración")
    # Plan: algunos ítems completados
    for it in db.listar_plan(con, u1)[:4]:
        db.marcar_item(con, it["id"], True)
    # Reportes de eventos: uno completo, dos borradores (uno se completará en la demo)
    db.guardar_reporte(con, u1, {"fecha_evento": hoy - timedelta(days=30), "medicamento": "Mounjaro (tirzepatida)", "edad": 42, "sexo": "Femenino", "peso_kg": 87.4,
                                 "descripcion": "Náuseas leves los dos días siguientes a la aplicación.", "sintomas": ["Náuseas"], "grave": "No", "desenlace": "Recuperado"}, como_borrador=False)
    db.guardar_reporte(con, u1, {"fecha_evento": hoy - timedelta(days=8), "medicamento": "Mounjaro (tirzepatida)", "edad": 42, "sexo": "Femenino",
                                 "descripcion": "Enrojecimiento en el sitio de inyección.", "sintomas": ["Reacción en el sitio de inyección"], "grave": "No", "desenlace": "Desconocido"}, como_borrador=True)
    db.guardar_reporte(con, u2, {"medicamento": "Semaglutida", "descripcion": "Mareo ocasional.", "sintomas": ["Mareo"]}, como_borrador=True)
    poblar_planes(con)
    return True


def poblar_planes(con) -> bool:
    """Inscripciones de demostración. También se ejecuta sobre bases creadas con la versión anterior (migración)."""
    demo = con.execute("SELECT id FROM usuarios WHERE es_demo=1 ORDER BY id LIMIT 1").fetchone()
    if not demo or con.execute("SELECT COUNT(*) FROM inscripciones WHERE usuario_id=?", (demo[0],)).fetchone()[0] > 0:
        return False
    uid, hoy = demo[0], date.today()
    r = planes.inscribir(con, uid, "ruta_tirzepatida", hoy - timedelta(days=9),
                         ["Organizar controles con endocrinología", "Registrar síntomas y su evolución"],
                         {"dias": ["Lun", "Mié", "Vie"], "momento": "Mañana", "modalidad": "Virtual", "recordatorios": True})
    for a in planes.actividades(con, r, 1)[:4]:
        planes.marcar(con, a["id"], True)
    planes.observar(con, planes.actividades(con, r, 1)[0]["id"], "Quiero llegar a mis controles con mis registros al día.")
    planes.agregar_nota(con, r, 1, "Primera semana: anoté náuseas leves los dos primeros días. Las comentaré en mi control.")
    n = planes.inscribir(con, uid, "prog_nutricion", hoy - timedelta(days=3), ["Semana 1: conocer su punto de partida"],
                         {"dias": ["Mar", "Jue"], "momento": "Tarde", "modalidad": "Indiferente", "recordatorios": False})
    planes.marcar(con, planes.actividades(con, n, 1)[0]["id"], True)
    planes.registrar(con, n, "comida", hoy - timedelta(days=1), "Desayuno: huevo, arepa y fruta. Almuerzo: sopa, arroz y pollo.", nota="Registro de demostración")
    return True
