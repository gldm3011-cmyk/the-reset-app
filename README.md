# The Reset — versión 3 (lista para operar)

Plataforma de acompañamiento para personas adultas que usan o consideran medicamentos GLP-1 (por ejemplo, Mounjaro/tirzepatida) **bajo supervisión médica**.
The Reset **no prescribe** medicamentos, dosis, frecuencias, dietas ni rutinas, y no reemplaza la atención médica.

## Qué cambió frente al prototipo

| Prototipo (v2) | Versión 3 |
|---|---|
| Usuarios y profesionales ficticios, selector de usuario | **Cuentas reales con correo y contraseña** para pacientes, profesionales y administración |
| Base SQLite que se borraba al reiniciar la nube | **PostgreSQL** (Supabase u otro) con `DATABASE_URL`; SQLite solo para pruebas locales |
| Directorio con perfiles inventados | Los profesionales **se registran** y aparecen solo cuando el administrador **verifica su registro** |
| Aviso de «no ingrese datos reales» | **Autorización de tratamiento de datos** (Ley 1581 de 2012), política y términos, descarga de datos y eliminación de la cuenta |
| Sin panel profesional | **Agenda del profesional**: enlace de videollamada, marcar cita como atendida, ver registros de sus pacientes (si el paciente lo permite) |
| Panel de análisis abierto | **Administración**: verificación de profesionales, cuentas, contraseñas temporales, indicador central y auditoría |

## Roles

- **Paciente** (18 años o más): crea su cuenta, elige ruta por medicamento y programas de 4 semanas, agenda citas, registra seguimiento y eventos adversos
  con indicador de completitud, controla si comparte sus registros, descarga sus datos o elimina su cuenta.
- **Profesional**: se registra con su número ReTHUS o tarjeta profesional; queda **en revisión** hasta que el administrador lo aprueba. Luego ve su agenda,
  agrega el enlace de la consulta virtual, marca citas atendidas y consulta el seguimiento de sus pacientes.
- **Administrador**: se crea automáticamente con `ADMIN_EMAIL` y `ADMIN_PASSWORD`. Aprueba, rechaza o suspende profesionales; activa o desactiva cuentas;
  genera contraseñas temporales; ve el indicador central (reportes con edad, sexo, peso y desenlace) y la auditoría de accesos.

## Seguridad incluida

- Contraseñas con PBKDF2-SHA256 (310.000 iteraciones y sal aleatoria); mínimo 8 caracteres con letras y números.
- Bloqueo de 15 minutos tras 5 intentos fallidos; mensajes de error que no revelan si un correo existe.
- Cierre de sesión por inactividad (30 minutos, configurable con `SESION_MINUTOS`).
- Control de acceso por rol: un profesional solo ve pacientes que agendaron con él y que comparten sus registros.
- Auditoría de inicios de sesión, cambios de contraseña, aprobaciones y consultas a datos de pacientes.
- En PostgreSQL se activa *Row Level Security* en todas las tablas, para que la API pública de Supabase no pueda leerlas.
- Enlaces de videollamada solo con `https://`; todo el texto de usuarios se escapa antes de mostrarse.

## Puesta en marcha en la nube (gratis para empezar)

### 1. Base de datos en Supabase
1. Cree un proyecto en <https://supabase.com> y anote la contraseña de la base.
2. Vaya a **Project Settings → Database → Connection string** y copie la de **Transaction pooler** (puerto 6543).
3. Reemplace `[YOUR-PASSWORD]` por su contraseña y agregue `?sslmode=require` al final. Si la contraseña tiene símbolos como `@` o `#`, escríbalos codificados (`%40`, `%23`).

La app crea todas las tablas sola la primera vez que arranca.

### 2. Código en GitHub
Suba el contenido de esta carpeta a su repositorio (por ejemplo `gldm3011-cmyk/the-reset-app`), reemplazando la versión anterior.
El `.gitignore` evita subir la base local y el archivo de secretos.

### 3. Despliegue en Streamlit Community Cloud
1. En <https://share.streamlit.io> abra su app (o **Create app** → repositorio → `app.py`).
2. En **Settings → Secrets** pegue el contenido de `.streamlit/secrets.example.toml` con sus valores reales:
   `DATABASE_URL`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `RESPONSABLE_NOMBRE`, `RESPONSABLE_NIT`, `RESPONSABLE_CORREO`, `RESPONSABLE_CIUDAD`.
3. Guarde y reinicie la app (**Reboot**). Ingrese con el correo y la contraseña de administrador.

### 4. Primer día de operación
1. Ingrese como administrador y cambie la contraseña en **Mi cuenta**.
2. Pida a los profesionales que se registren en **Soy profesional**; verifique cada registro en ReTHUS y apruébelos en **Verificar**.
3. Comparta el enlace de la app con los pacientes.

## Ejecutar en su computador

```bash
pip install -r requirements.txt
# Windows (PowerShell): $env:ADMIN_EMAIL="admin@prueba.co"; $env:ADMIN_PASSWORD="Admin2027x"
export ADMIN_EMAIL=admin@prueba.co ADMIN_PASSWORD=Admin2027x
streamlit run app.py
```

Sin `DATABASE_URL` usa `data/the_reset.db` (SQLite).
Para una **demostración con datos de ejemplo** agregue `THE_RESET_DEMO=1`: se cargan profesionales y pacientes ficticios con la contraseña `Demo12345`
(por ejemplo `ana.demo@ejemplo.com` o `profesional1@demo.thereset`). **No use ese modo en producción.**

## Pruebas

```bash
pip install -r requirements-dev.txt
python -m pytest -q                                   # 67 pruebas en SQLite
TEST_DATABASE_URL=postgresql://... python -m pytest -q  # + flujo completo en PostgreSQL (base desechable: se borra)
```

Cubren cuentas, contraseñas, bloqueo, roles, verificación de profesionales, citas, enlaces, privacidad, exportación y eliminación de datos,
planes, eventos adversos y todas las pantallas por rol (Streamlit 1.40.2 y 1.66.1).

## Antes de abrir al público (pendientes que no son de código)

- **Revisión legal** de la política de tratamiento de datos y los términos (`ui/legal.py`) por un abogado. Son plantillas basadas en la Ley 1581 de 2012.
- **Registro Nacional de Bases de Datos** ante la SIC, si su empresa está obligada.
- **Copias de seguridad**: el plan gratuito de Supabase no incluye copias automáticas diarias; actívelas en un plan pago o programe exportaciones.
- **Telesalud**: si los profesionales atienden por video, cada uno debe cumplir la Resolución 2654 de 2019; The Reset solo guarda el enlace.

## Limitaciones conocidas

- **Recuperación de contraseña** por correo: no se envían correos; el administrador genera una contraseña temporal desde **Cuentas**.
- **Pagos** (suscripción premium, comisiones): no están integrados; requieren una pasarela certificada y un contrato comercial.
- **Videollamada**: se usa un enlace externo (Meet, Zoom, Teams) que agrega el profesional.
- **Recargar la página** cierra la sesión (Streamlit no guarda sesiones entre recargas); basta con volver a ingresar.

## Estructura

```
app.py                  Arranque, sesión, enrutamiento por rol y barra inferior
core/conexion.py        SQLite o PostgreSQL con la misma interfaz
core/db.py              Esquema, migraciones, citas, seguimiento, eventos, exportación y supresión
core/auth.py            Cuentas, contraseñas, bloqueo, roles, administración y auditoría
core/planes.py          Programas de 4 semanas: inscripción, calendario, pausas y registros
core/programas.py       Catálogo educativo de rutas y programas (sin dosis)
core/seed.py            Datos de ejemplo (solo con THE_RESET_DEMO=1)
ui/acceso.py            Inicio de sesión, registro, cambio de contraseña
ui/legal.py             Política de datos y términos de uso
ui/vistas.py            Paciente · ui/vistas_planes.py Planes · ui/vistas_pro.py Profesional · ui/vistas_admin.py Administración
tests/                  Pruebas automatizadas
```
