"""Política de tratamiento de datos y términos de uso.

Los datos del responsable se toman de los secretos RESPONSABLE_NOMBRE, RESPONSABLE_NIT, RESPONSABLE_CORREO y RESPONSABLE_CIUDAD.
IMPORTANTE: es una plantilla basada en la Ley 1581 de 2012 y el Decreto 1074 de 2015. Debe revisarla un abogado antes de operar.
"""
from __future__ import annotations

import streamlit as st

from core.auth import POLITICA_VERSION
from core.conexion import config
from ui.estilo import e


def responsable():
    return {
        "nombre": config("RESPONSABLE_NOMBRE", "[Razón social del responsable — configurar]"),
        "nit": config("RESPONSABLE_NIT", "[NIT — configurar]"),
        "correo": config("RESPONSABLE_CORREO", "[correo de contacto — configurar]"),
        "ciudad": config("RESPONSABLE_CIUDAD", "[ciudad — configurar]"),
    }


def configurado() -> bool:
    return all(config(k) for k in ("RESPONSABLE_NOMBRE", "RESPONSABLE_NIT", "RESPONSABLE_CORREO"))


def politica_md() -> str:
    r = responsable()
    return f"""
**Política de tratamiento de datos personales de The Reset** · versión {POLITICA_VERSION}

**1. Responsable.** {r['nombre']}, NIT {r['nit']}, con domicilio en {r['ciudad']}, Colombia. Contacto para asuntos de datos personales: {r['correo']}.

**2. Datos que tratamos.** Datos de identificación y contacto (nombre, correo, ciudad), edad y sexo, y **datos sensibles de salud** que usted registra
voluntariamente: peso, síntomas, nivel de energía, medicamento que declara usar bajo supervisión médica, eventos adversos y su evolución,
y la información de sus citas. De los profesionales tratamos además su especialidad, número de registro profesional, disponibilidad y perfil.

**3. Finalidades.** (a) Crear y administrar su cuenta; (b) organizar su plan de acompañamiento, sus citas y sus registros de seguimiento;
(c) permitir que **los profesionales con los que usted agenda citas** consulten sus registros de seguimiento y de eventos, si usted lo mantiene
activado en su perfil; (d) verificar la identidad y el registro de los profesionales; (e) generar estadísticas **agregadas y anonimizadas**
para mejorar el servicio; (f) atender sus consultas y reclamos.

**4. Datos sensibles.** Usted no está obligado a suministrar datos sensibles. Si los registra, lo hace de forma facultativa y con su autorización
previa, expresa e informada. No vendemos ni cedemos sus datos con fines comerciales.

**5. Sus derechos** (artículo 8 de la Ley 1581 de 2012): conocer, actualizar y rectificar sus datos; solicitar prueba de la autorización;
ser informado del uso que se les da; presentar quejas ante la Superintendencia de Industria y Comercio; revocar la autorización o pedir la
supresión de sus datos; y acceder a ellos en forma gratuita. En **Perfil → Privacidad** puede descargar todos sus datos y eliminar su cuenta.

**6. Consultas y reclamos.** Escriba a {r['correo']}. Las consultas se responden en máximo diez (10) días hábiles y los reclamos en máximo
quince (15) días hábiles, en los términos de los artículos 14 y 15 de la Ley 1581 de 2012.

**7. Seguridad.** Contraseñas cifradas con un algoritmo de derivación de claves, conexión cifrada (HTTPS), control de acceso por roles y
registro de auditoría de los accesos. Los datos se alojan en proveedores de nube que pueden estar ubicados fuera de Colombia; esa transferencia
se realiza con proveedores que ofrecen niveles adecuados de protección.

**8. Vigencia.** Esta política rige desde su publicación. Los datos se conservan mientras su cuenta esté activa o mientras sea necesario para
cumplir obligaciones legales. Cualquier cambio sustancial se le informará y, cuando corresponda, se le pedirá una nueva autorización.
"""


def terminos_md() -> str:
    r = responsable()
    return f"""
**Términos de uso de The Reset** · versión {POLITICA_VERSION}

1. **The Reset no es un servicio médico.** Es una plataforma de acompañamiento y organización. No prescribe medicamentos, dosis, frecuencias,
dietas ni rutinas, no diagnostica y no reemplaza la consulta con su profesional de salud.
2. **Emergencias.** Ante síntomas graves, busque atención médica inmediata o llame a la línea de emergencias **123**.
3. **Eventos adversos.** Registrar un evento en The Reset no equivale a una notificación oficial de farmacovigilancia. Repórtelo a su
profesional de salud o ante el INVIMA.
4. **Profesionales.** Los profesionales del directorio son verificados por The Reset antes de aparecer, con base en el registro que declaran.
Cada profesional es responsable de la atención que presta y de sus honorarios.
5. **Su cuenta.** Es personal e intransferible. Usted es responsable de mantener su contraseña en reserva y de la veracidad de los datos que registra.
6. **Uso adecuado.** No está permitido usar la plataforma para fines ilícitos, suplantar a otras personas ni intentar acceder a datos ajenos.
7. **Edad.** El servicio está dirigido a personas mayores de 18 años.
8. **Contacto.** {r['nombre']} · {r['correo']}.
"""


def mostrar(tipo: str):
    st.markdown(politica_md() if tipo == "privacidad" else terminos_md())
    if not configurado():
        st.caption("⚠️ Plantilla legal: faltan los datos del responsable (configure RESPONSABLE_NOMBRE, RESPONSABLE_NIT y RESPONSABLE_CORREO) "
                   "y debe revisarla un abogado antes de operar.")


def enlaces():
    with st.expander("Política de tratamiento de datos"):
        mostrar("privacidad")
    with st.expander("Términos de uso"):
        mostrar("terminos")
