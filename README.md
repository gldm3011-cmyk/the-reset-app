# The Reset — Prototipo funcional (versión 2, mobile-first)

Prototipo académico de **The Reset**: plataforma de acompañamiento para personas adultas que usan o consideran medicamentos GLP-1 (por ejemplo, Mounjaro/tirzepatida) **bajo supervisión médica**.

> ⚠️ **No es un servicio médico.** No prescribe medicamentos, dosis, frecuencias, dietas ni rutinas, y no sustituye a los profesionales de salud. Todos los usuarios y profesionales son **ficticios**: no ingrese datos médicos reales. Registrar un evento en la app **no equivale a una notificación oficial de farmacovigilancia**.

## Novedades de la versión 2

- **Interfaz tipo aplicación móvil:**
  - barra de navegación inferior (Inicio, Mis planes, Citas, Seguimiento, Perfil) y botón **Más** para Profesionales, Eventos adversos, Panel y Acerca;
  - tarjetas redondeadas, anillos de progreso, calendario semanal y paleta verde salvia, verde oscuro, blanco y crema;
  - diseño adaptable a celular y computador.
- **Mis planes:**
  - Explorar el catálogo y entrar a la ficha de cada programa.
  - Rutas por medicamento:
    - **Mounjaro · tirzepatida**
    - **Ozempic / Wegovy · semaglutida**
    - **Saxenda / Victoza · liraglutida**
    - **Acompañamiento general**
  - Programas de **nutrición**, **actividad física** y **seguimiento clínico**, de 4 semanas cada uno.
  - Inscripción con objetivos y preferencias, calendario de 4 semanas y actividades que se marcan como realizadas.
  - Observaciones por actividad y por semana, registros de comidas, hábitos y actividad, y progreso semanal y total.
  - Pausar y reanudar: al reanudar, las actividades pendientes se corren los días que duró la pausa. También se puede finalizar.
  - Sin inscripciones duplicadas.
- **Inicio renovado:** muestra el plan activo con su avance, el medicamento declarado, la próxima cita, los pendientes de la semana, accesos rápidos y un resumen de seguimiento.
- **Recarga sin perder el lugar:** la URL guarda el usuario y la sección (`?u=…&p=…&i=…`). Al recargar el navegador se vuelve al mismo plan.

### Rutas por medicamento: qué hacen y qué no

Cada ruta presenta información **educativa** del medicamento:
- distingue **marca**, **principio activo** e **indicaciones autorizadas**, que cambian según la marca, el país y la agencia (por ejemplo, Mounjaro y Zepbound son la misma molécula con indicaciones distintas en EE. UU.);
- recomienda verificar el registro sanitario vigente del INVIMA en Colombia;
- organiza controles con el especialista, el registro de síntomas y posibles efectos adversos, la evolución y bienestar, y el seguimiento nutricional y físico con profesionales;
- incluye **señales de alarma** para buscar atención médica, sin diagnosticar.

**Ninguna ruta** indica dosis, frecuencias de administración, ajustes de medicación ni decisiones clínicas. Una prueba automática revisa que ninguna actividad del catálogo contenga cantidades de medicamento ni calorías. La ruta «sugerida» depende solo del medicamento que el usuario **declara** en su perfil y no es una recomendación clínica.

## Funciones que se conservan

Registro y perfil · directorio de profesionales · citas (agendar, reprogramar, cancelar, sin reservas duplicadas) · seguimiento de salud (peso opcional, síntomas, energía, edición) · **eventos adversos** con indicador de completitud, borradores, actualización del desenlace e historial · panel de análisis con los datos históricos (54.170 reportes) **separados** de los datos ficticios · persistencia en SQLite.

## Estructura

```
the_reset_app/
├── app.py                 Arranque, encabezado, enrutador y barra inferior
├── core/
│   ├── db.py              SQLite: esquema (con migración), validaciones, usuarios, citas, seguimiento, eventos, indicadores
│   ├── programas.py       Catálogo de rutas y programas (contenido educativo, sin dosis)
│   ├── planes.py          Inscripciones, calendario, avance, pausas, observaciones y registros
│   └── seed.py            Datos ficticios de demostración
├── ui/
│   ├── estilo.py          CSS mobile-first y componentes (anillos, calendario, tarjetas)
│   ├── nav.py             Navegación y mensajes
│   ├── vistas_planes.py   Explorar, ficha, inscripción y plan activo
│   └── vistas.py          Inicio, Citas, Seguimiento, Perfil, Más, Profesionales, Eventos, Panel
├── data/historico_resumen.csv     Resumen agregado de las bases limpias del proyecto
├── tests/                 54 pruebas automatizadas
├── tools/generar_resumen_historico.py
├── ejecutar_en_colab.ipynb
├── requirements.txt / requirements-dev.txt
└── .streamlit/config.toml
```

**Migración:** si ya tenía `data/the_reset_demo.db` de la versión 1, la app conserva sus usuarios, citas, seguimientos y reportes, y le agrega las tablas de planes (`inscripciones`, `plan_actividades`, `plan_notas` y `plan_registros`). Para empezar de cero use **Más → Restablecer la demostración** o borre ese archivo.

## 1. Ejecutar en su computador (recomendado para la presentación)

Requisitos: Python 3.10 o superior.

```bash
cd the_reset_app
python -m venv .venv
# Windows: .venv\Scripts\activate      macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Se abre en `http://localhost:8501`. Para ver la versión móvil en el computador, abra las herramientas de desarrollo del navegador (F12) y active el modo de dispositivo (Ctrl+Shift+M), o abra el enlace desde su celular.

## 2. Ejecutar en Google Colab

Abra `ejecutar_en_colab.ipynb` en Colab y ejecute las celdas en orden. El cuaderno:
1. sube y descomprime el ZIP;
2. instala las dependencias;
3. ejecuta las pruebas (opcional);
4. inicia la app;
5. crea un enlace público temporal con Cloudflare Tunnel (`https://….trycloudflare.com`).

El enlace dura mientras la sesión de Colab esté activa.

## 3. Publicar con un enlace permanente (Streamlit Community Cloud, gratuito)

1. Suba el contenido de `the_reset_app/` a un repositorio **público** de GitHub. El `.gitignore` excluye la base local.
2. Entre a <https://share.streamlit.io> → **Create app** → elija el repositorio, la rama y el archivo `app.py` → **Deploy**.
3. Comparta el enlace `https://<nombre>.streamlit.app`. Se ve bien desde el celular del profesor.

En la nube, la base SQLite vive en el servidor de la app: los datos se conservan mientras la app esté activa y vuelven a los datos de demostración si la plataforma la reinicia.

## 4. Pruebas automatizadas

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

Las 54 pruebas pasan con Streamlit 1.40.2 y con 1.66.1:
- **Planes:**
  - catálogo completo de 4 semanas y sin dosis;
  - marcas y principios activos distinguidos;
  - ruta sugerida por medicamento;
  - inscripción, calendario y validaciones;
  - no duplicar inscripciones;
  - avance, observaciones y notas;
  - semana actual;
  - pausar y reanudar con corrimiento de fechas;
  - registros del programa;
  - persistencia y migración desde la versión 1.
- **Funciones existentes:** registro, citas, seguimiento, eventos adversos e indicadores.
- **Interfaz (`streamlit.testing`):**
  - todas las secciones y la barra inferior;
  - registro, rechazo de menores de edad y cambio de usuario;
  - flujo completo de la ruta Mounjaro (explorar → ficha → inscribirse → marcar → pausar → reanudar);
  - registros y observaciones del plan de nutrición;
  - citas, directorio, eventos y pendientes desde el inicio;
  - recuperación del plan desde la URL.
