"""Catálogo de rutas y programas de acompañamiento de The Reset.

Son programas de ORGANIZACIÓN, EDUCACIÓN y SEGUIMIENTO. No prescriben tratamientos, dosis, frecuencias de
administración, ajustes de medicación, dietas, calorías ni rutinas de ejercicio: la personalización clínica
corresponde exclusivamente a los profesionales de salud.

Cada actividad: (semana 1–4, día 1–7, categoría, título, descripción, acción).
Acciones posibles: None | "cita:<Especialidad>" | "seguimiento" | "evento" | "alarma" | "registro:comida" |
"registro:habito" | "registro:actividad" | "preguntas".
"""
from __future__ import annotations

SEMANAS = 4

AVISO_GENERAL = ("Programa educativo y de organización. No indica medicamentos, dosis, frecuencias, dietas, calorías ni rutinas de ejercicio. "
                 "Cualquier decisión clínica corresponde a su profesional de salud.")

SENALES_ALARMA = [
    "Dolor abdominal intenso y persistente, con o sin vómito, que puede irradiarse a la espalda.",
    "Vómito o diarrea persistentes que no le permiten hidratarse, o signos de deshidratación (mareo intenso, orina muy escasa).",
    "Reacción alérgica: hinchazón de cara, labios o garganta, dificultad para respirar o ronchas extensas.",
    "Si además usa otros medicamentos para la diabetes: sudoración, temblor, confusión o sensación de desmayo.",
    "Cambios repentinos en la visión, dolor en el pecho o cualquier síntoma intenso que le preocupe.",
]
TEXTO_ALARMA = ("Ante cualquiera de estas señales, busque atención médica de inmediato o llame a la línea de emergencias (123 en Colombia). "
                "The Reset no diagnostica: esta lista solo sirve para orientarle a buscar ayuda profesional.")

PREGUNTAS_CONSULTA = [
    "¿Este tratamiento o programa es adecuado para mi situación y mis antecedentes?",
    "¿Qué controles y exámenes necesito, y cada cuánto debo volver a consulta?",
    "¿Qué síntomas debo vigilar y cuándo debo consultar de inmediato?",
    "¿Cómo coordino la alimentación y la actividad física con mi tratamiento?",
    "¿Qué hago si olvido algo de lo que me indicaron o tengo dudas entre consultas?",
]

OBJETIVOS_GENERALES = ["Organizar mis controles médicos", "Llevar un registro constante de mi evolución", "Documentar síntomas y su evolución",
                       "Mejorar mis hábitos de alimentación con orientación profesional", "Mantenerme activo de forma segura",
                       "Preparar mejor mis consultas", "Cuidar mi bienestar emocional"]

# ---------------------------------------------------------------- información de medicamentos (educativa)
MEDICAMENTOS = {
    "tirzepatida": {
        "principio_activo": "Tirzepatida",
        "clase": "Agonista dual de los receptores GIP y GLP-1",
        "marcas": [
            ("Mounjaro", "Autorizado para diabetes tipo 2 en adultos (EE. UU., FDA). En la Unión Europea (EMA) también está autorizado para el control del peso en adultos con obesidad, o con sobrepeso y al menos una comorbilidad relacionada."),
            ("Zepbound", "Nombre comercial en EE. UU. de la misma molécula, autorizado para el control crónico del peso en adultos con obesidad, o con sobrepeso y comorbilidades, y para apnea obstructiva del sueño moderada a grave en adultos con obesidad (FDA)."),
        ],
    },
    "semaglutida": {
        "principio_activo": "Semaglutida",
        "clase": "Agonista del receptor GLP-1",
        "marcas": [
            ("Ozempic", "Autorizado para diabetes tipo 2 en adultos; también para reducir el riesgo cardiovascular y renal en adultos con diabetes tipo 2 con esas condiciones (FDA)."),
            ("Wegovy", "Autorizado para el control crónico del peso en personas con obesidad (desde 12 años) o adultos con sobrepeso y comorbilidades, y para reducir el riesgo cardiovascular en adultos con enfermedad cardiovascular y obesidad o sobrepeso (FDA)."),
            ("Rybelsus", "Presentación oral de semaglutida autorizada para diabetes tipo 2 en adultos (FDA)."),
        ],
    },
    "liraglutida": {
        "principio_activo": "Liraglutida",
        "clase": "Agonista del receptor GLP-1",
        "marcas": [
            ("Victoza", "Autorizado para diabetes tipo 2 (desde 10 años) y para reducir el riesgo cardiovascular en adultos con diabetes tipo 2 y enfermedad cardiovascular (FDA)."),
            ("Saxenda", "Autorizado para el control crónico del peso en personas con obesidad (desde 12 años) o adultos con sobrepeso y comorbilidades (FDA)."),
        ],
    },
}
NOTA_INDICACIONES = ("Marcas con el mismo principio activo pueden tener indicaciones autorizadas distintas, y estas cambian según el país y la agencia. "
                     "En Colombia, verifique el registro sanitario vigente del INVIMA. Ningún medicamento es apropiado para todas las personas: "
                     "la decisión de usarlo, su indicación y su forma de uso las define exclusivamente un profesional autorizado.")


def _ruta_medicamento(clave, especialista="Endocrinología"):
    nombre = MEDICAMENTOS[clave]["principio_activo"].lower()
    return [
        (1, 1, "Educación", "Bienvenida y objetivos del programa", "Conozca cómo funciona la ruta y elija qué quiere organizar estas cuatro semanas.", None),
        (1, 2, "Educación", f"Qué es la {nombre} y qué indicaciones tiene", "Lea la ficha informativa: principio activo, marcas e indicaciones autorizadas. No reemplaza la información de su médico.", None),
        (1, 3, "Control", f"Agendar control con {especialista.lower()}", "Organice su cita de control. El acompañamiento especializado es la base de un tratamiento supervisado.", f"cita:{especialista}"),
        (1, 4, "Registro", "Registro inicial de bienestar", "Registre cómo se siente hoy. El peso es opcional.", "seguimiento"),
        (1, 6, "Control", "Preparar preguntas para su consulta", "Revise la lista de preguntas sugeridas y anote las suyas.", "preguntas"),
        (2, 1, "Educación", "Conocer las señales de alarma", "Identifique cuándo buscar atención médica inmediata.", "alarma"),
        (2, 2, "Seguimiento", "Registro semanal de síntomas", "Anote síntomas y cómo evolucionan. Si algo le preocupa, consulte a su profesional.", "seguimiento"),
        (2, 3, "Nutrición", "Agendar orientación con nutrición", "La alimentación debe orientarla un nutricionista según su caso.", "cita:Nutrición"),
        (2, 5, "Nutrición", "Registrar comidas durante tres días", "Un registro sencillo ayuda a su nutricionista a orientarle.", "registro:comida"),
        (3, 1, "Seguimiento", "Documentar la evolución de un síntoma", "Si tuvo un síntoma o posible evento adverso, regístrelo y actualice su desenlace.", "evento"),
        (3, 2, "Actividad", "Agendar valoración con medicina deportiva", "Antes de cambiar su actividad física, consulte qué es seguro para usted.", "cita:Medicina deportiva"),
        (3, 4, "Actividad", "Registrar la actividad realizada", "Anote qué actividad hizo y cómo se sintió.", "registro:actividad"),
        (3, 6, "Registro", "Registro semanal de bienestar", "Peso opcional, energía y observaciones.", "seguimiento"),
        (4, 1, "Control", "Preparar el resumen para su control", "Revise sus registros de las cuatro semanas para compartirlos en consulta.", "preguntas"),
        (4, 3, "Control", f"Control de seguimiento con {especialista.lower()}", "Asista a su control y comparta su evolución.", f"cita:{especialista}"),
        (4, 5, "Seguimiento", "Actualizar desenlaces pendientes", "Si algún reporte quedó con desenlace desconocido, actualícelo.", "evento"),
        (4, 7, "Educación", "Revisar su progreso y próximos pasos", "Revise lo logrado y defina con su profesional cómo continuar.", None),
    ]


PROGRAMAS = {
    "ruta_tirzepatida": {
        "tipo": "Ruta por medicamento", "nombre": "Ruta Mounjaro · Tirzepatida", "corto": "Mounjaro",
        "subtitulo": "Acompañamiento para personas que usan tirzepatida bajo supervisión médica",
        "descripcion": ("Organiza sus controles con endocrinología, el registro de síntomas y posibles efectos adversos, su evolución y bienestar, "
                        "y el seguimiento nutricional y de actividad física. Incluye recordatorios de citas y registros, nunca instrucciones de dosificación."),
        "medicamento": "tirzepatida", "profesional": "Endocrinología", "apoyo": ["Nutrición", "Medicina deportiva"],
        "icono": "💉", "color": "#DCE9C5",
        "objetivos": ["Organizar controles con endocrinología", "Registrar síntomas y su evolución", "Documentar posibles efectos adversos con datos completos",
                      "Llevar seguimiento nutricional y de actividad con profesionales", "Preparar mejor cada consulta"],
        "actividades": _ruta_medicamento("tirzepatida"),
    },
    "ruta_semaglutida": {
        "tipo": "Ruta por medicamento", "nombre": "Ruta Ozempic / Wegovy · Semaglutida", "corto": "Semaglutida",
        "subtitulo": "Acompañamiento para personas que usan semaglutida bajo supervisión médica",
        "descripcion": ("Ruta educativa para organizar controles médicos, registrar síntomas y evolución, documentar posibles eventos adversos "
                        "y coordinar el seguimiento nutricional y de actividad física con sus profesionales."),
        "medicamento": "semaglutida", "profesional": "Endocrinología", "apoyo": ["Nutrición", "Medicina deportiva"],
        "icono": "💊", "color": "#E4ECE6",
        "objetivos": ["Organizar controles médicos", "Registrar síntomas y evolución", "Seguimiento de posibles eventos adversos",
                      "Coordinar nutrición y actividad física con profesionales"],
        "actividades": _ruta_medicamento("semaglutida"),
    },
    "ruta_liraglutida": {
        "tipo": "Ruta por medicamento", "nombre": "Ruta Saxenda / Victoza · Liraglutida", "corto": "Liraglutida",
        "subtitulo": "Acompañamiento para personas que usan liraglutida bajo supervisión médica",
        "descripcion": "Ruta para organizar citas y controles, registrar síntomas y seguimiento, y recibir apoyo nutricional y físico de profesionales.",
        "medicamento": "liraglutida", "profesional": "Endocrinología", "apoyo": ["Nutrición", "Medicina deportiva"],
        "icono": "🩺", "color": "#EFE9D8",
        "objetivos": ["Organizar citas y controles", "Registrar síntomas y seguimiento", "Apoyo nutricional y físico con profesionales"],
        "actividades": _ruta_medicamento("liraglutida"),
    },
    "ruta_general": {
        "tipo": "Ruta por medicamento", "nombre": "Acompañamiento general", "corto": "General",
        "subtitulo": "Para quienes aún no usan estos medicamentos o están considerando consultarlo",
        "descripcion": ("Le ayuda a preparar una consulta informada con un profesional, registrar sus objetivos generales y entender por qué "
                        "la evaluación médica es indispensable antes de considerar cualquier medicamento."),
        "medicamento": None, "profesional": "Medicina general", "apoyo": ["Endocrinología", "Nutrición"],
        "icono": "🌿", "color": "#F3EFE2",
        "objetivos": ["Definir objetivos generales de salud", "Preparar una consulta informada", "Entender la importancia de la evaluación médica"],
        "actividades": [
            (1, 1, "Educación", "Bienvenida: qué puede y qué no puede hacer esta ruta", "The Reset organiza y educa; no recomienda medicamentos.", None),
            (1, 2, "Registro", "Registrar sus objetivos generales", "Escriba qué le gustaría lograr y por qué.", None),
            (1, 4, "Educación", "Por qué la evaluación médica es indispensable", "Los medicamentos tienen indicaciones específicas y no son para todas las personas.", None),
            (2, 1, "Control", "Preparar preguntas para la consulta", "Use la lista sugerida y agregue sus propias preguntas.", "preguntas"),
            (2, 3, "Control", "Agendar consulta con medicina general", "Una primera valoración ayuda a definir el camino adecuado.", "cita:Medicina general"),
            (2, 5, "Registro", "Registro inicial de bienestar", "Peso opcional, energía y observaciones.", "seguimiento"),
            (3, 1, "Nutrición", "Registrar hábitos de alimentación", "Un registro sencillo para conversarlo con un profesional.", "registro:habito"),
            (3, 3, "Actividad", "Registrar su actividad cotidiana", "Anote cuánto se mueve hoy, sin metas impuestas.", "registro:actividad"),
            (3, 5, "Educación", "Conocer las señales de alarma", "Saber cuándo buscar atención médica.", "alarma"),
            (4, 1, "Control", "Asistir a su consulta y registrar las recomendaciones", "Anote lo que le indicó su profesional.", None),
            (4, 4, "Control", "Agendar orientación con nutrición o endocrinología si se la indican", "Solo si su médico lo considera necesario.", "cita:Nutrición"),
            (4, 7, "Educación", "Revisar su progreso", "Revise lo logrado y sus próximos pasos.", None),
        ],
    },
    "prog_nutricion": {
        "tipo": "Programa de acompañamiento", "nombre": "Plan de nutrición", "corto": "Nutrición",
        "subtitulo": "Hábitos de alimentación con orientación de su nutricionista",
        "descripcion": ("Programa de ejemplo de cuatro semanas con objetivos educativos semanales, registro de comidas y hábitos, espacio para "
                        "observaciones y revisión con nutricionista. No incluye dietas restrictivas, calorías prescritas ni menús clínicos individualizados."),
        "medicamento": None, "profesional": "Nutrición", "apoyo": [], "icono": "🥑", "color": "#E7EFD3",
        "objetivos": ["Semana 1: conocer su punto de partida", "Semana 2: regularidad en horarios y comidas", "Semana 3: planear compras y leer etiquetas",
                      "Semana 4: revisar con su nutricionista"],
        "actividades": [
            (1, 1, "Educación", "Objetivo de la semana: conocer su punto de partida", "Sin cambiar nada todavía, observe cómo come habitualmente.", None),
            (1, 2, "Registro", "Registrar comidas del día", "Anote qué comió y a qué hora.", "registro:comida"),
            (1, 4, "Registro", "Registrar hidratación", "Anote cuánta agua tomó durante el día.", "registro:habito"),
            (1, 6, "Registro", "Registrar comidas de un día de fin de semana", "Compare con un día entre semana.", "registro:comida"),
            (2, 1, "Educación", "Objetivo de la semana: regularidad", "Aprenda por qué los horarios regulares ayudan a organizar la alimentación.", None),
            (2, 3, "Registro", "Registrar horarios de comida", "Anote los horarios reales durante dos días.", "registro:habito"),
            (2, 5, "Registro", "Registrar cómo se sintió después de comer", "Saciedad, molestias o energía.", "registro:comida"),
            (3, 1, "Educación", "Objetivo de la semana: compras y etiquetas", "Aprenda a leer la información nutricional de las etiquetas.", None),
            (3, 3, "Registro", "Planear la lista de compras", "Anote la lista de la semana para revisarla con su nutricionista.", "registro:habito"),
            (3, 5, "Registro", "Registrar comidas del día", "Un registro más para comparar su evolución.", "registro:comida"),
            (4, 1, "Control", "Agendar revisión con nutricionista", "Lleve sus registros a la cita.", "cita:Nutrición"),
            (4, 4, "Control", "Revisión con nutricionista", "Su nutricionista definirá las recomendaciones adecuadas para usted.", None),
            (4, 6, "Educación", "Revisar su progreso", "Revise lo logrado y anote observaciones.", None),
        ],
    },
    "prog_actividad": {
        "tipo": "Programa de acompañamiento", "nombre": "Plan de actividad física", "corto": "Actividad física",
        "subtitulo": "Actividad segura, siempre con evaluación profesional",
        "descripcion": ("Programa de ejemplo de cuatro semanas con calendario de seguimiento, registro de la actividad realizada, objetivos y "
                        "observaciones, y seguimiento con medicina deportiva. No prescribe intensidades ni rutinas sin evaluación profesional."),
        "medicamento": None, "profesional": "Medicina deportiva", "apoyo": [], "icono": "👟", "color": "#E4ECE6",
        "objetivos": ["Valoración antes de cambiar su actividad", "Registrar su actividad real", "Seguimiento con medicina deportiva"],
        "actividades": [
            (1, 1, "Control", "Agendar valoración con medicina deportiva", "Antes de cambiar su actividad física, consulte qué es seguro para usted.", "cita:Medicina deportiva"),
            (1, 3, "Registro", "Registrar su actividad cotidiana actual", "Anote cuánto se mueve hoy, sin metas impuestas.", "registro:actividad"),
            (1, 5, "Registro", "Anotar su objetivo personal", "Escriba qué le gustaría lograr para conversarlo con su profesional.", None),
            (2, 1, "Registro", "Registrar la actividad que su profesional aprobó", "Tipo de actividad, duración y cómo se sintió.", "registro:actividad"),
            (2, 4, "Registro", "Registrar pausas activas", "Anote pausas durante el día.", "registro:actividad"),
            (2, 6, "Educación", "Señales para detenerse y consultar", "Dolor en el pecho, mareo intenso o falta de aire: deténgase y busque atención.", "alarma"),
            (3, 2, "Registro", "Registrar la actividad realizada", "Continúe registrando lo que hace.", "registro:actividad"),
            (3, 5, "Registro", "Registrar cómo se sintió esta semana", "Energía, molestias o mejoras.", "seguimiento"),
            (4, 1, "Control", "Agendar seguimiento con medicina deportiva", "Revise su evolución con el profesional.", "cita:Medicina deportiva"),
            (4, 4, "Registro", "Registrar la actividad realizada", "Último registro del programa.", "registro:actividad"),
            (4, 6, "Educación", "Revisar su progreso", "Revise lo logrado y sus próximos pasos con su profesional.", None),
        ],
    },
    "prog_seguimiento": {
        "tipo": "Programa de acompañamiento", "nombre": "Plan de seguimiento clínico", "corto": "Seguimiento clínico",
        "subtitulo": "Controles, síntomas, evolución y señales de alarma",
        "descripcion": ("Programa de ejemplo de cuatro semanas con calendario de controles, registro de síntomas, peso opcional, registro de "
                        "eventos adversos y su estado de evolución, preparación de consultas y alertas para buscar atención ante señales de alarma. No diagnostica."),
        "medicamento": None, "profesional": "Medicina general", "apoyo": ["Endocrinología"], "icono": "📋", "color": "#EFE9D8",
        "objetivos": ["Calendario de controles", "Síntomas y evolución documentados", "Eventos adversos con datos completos", "Consultas mejor preparadas"],
        "actividades": [
            (1, 1, "Control", "Agendar control médico", "Organice su próximo control.", "cita:Medicina general"),
            (1, 2, "Seguimiento", "Registro de síntomas", "Anote síntomas, si los hay, y su intensidad.", "seguimiento"),
            (1, 4, "Registro", "Registro de peso (opcional)", "Solo si desea registrarlo.", "seguimiento"),
            (1, 6, "Educación", "Conocer las señales de alarma", "Saber cuándo buscar atención médica inmediata.", "alarma"),
            (2, 1, "Seguimiento", "Registrar la evolución de sus síntomas", "¿Mejoraron, siguen igual o empeoraron?", "seguimiento"),
            (2, 3, "Seguimiento", "Documentar un posible evento adverso", "Use el formulario estructurado con los datos mínimos.", "evento"),
            (2, 5, "Control", "Preparar preguntas para su consulta", "Use la lista sugerida.", "preguntas"),
            (3, 1, "Seguimiento", "Actualizar el estado de evolución", "Actualice el desenlace de sus reportes pendientes.", "evento"),
            (3, 4, "Registro", "Registro de peso (opcional)", "Solo si desea registrarlo.", "seguimiento"),
            (4, 1, "Control", "Asistir a su control médico", "Comparta sus registros.", "cita:Medicina general"),
            (4, 4, "Seguimiento", "Revisar reportes incompletos", "Complete los datos que falten.", "evento"),
            (4, 6, "Educación", "Revisar su progreso", "Revise lo logrado y próximos pasos.", None),
        ],
    },
}

ORDEN_RUTAS = ["ruta_tirzepatida", "ruta_semaglutida", "ruta_liraglutida", "ruta_general"]
ORDEN_PROGRAMAS = ["prog_nutricion", "prog_actividad", "prog_seguimiento"]

MEDICAMENTOS_DECLARABLES = ["No declaro", "Mounjaro (tirzepatida)", "Zepbound (tirzepatida)", "Ozempic (semaglutida)", "Wegovy (semaglutida)",
                            "Rybelsus (semaglutida)", "Saxenda (liraglutida)", "Victoza (liraglutida)", "Estoy considerando consultarlo", "Otro"]


def ruta_sugerida(medicamento: str | None) -> str:
    """Ruta de acompañamiento según el medicamento DECLARADO por el usuario (no es una recomendación clínica)."""
    m = (medicamento or "").lower()
    if any(k in m for k in ("tirzepat", "mounjaro", "zepbound")):
        return "ruta_tirzepatida"
    if any(k in m for k in ("semaglut", "ozempic", "wegovy", "rybelsus")):
        return "ruta_semaglutida"
    if any(k in m for k in ("liraglut", "saxenda", "victoza")):
        return "ruta_liraglutida"
    return "ruta_general"


def programa(pid: str) -> dict:
    if pid not in PROGRAMAS:
        raise KeyError(pid)
    return PROGRAMAS[pid]
