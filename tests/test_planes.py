"""Pruebas de rutas y programas: catálogo, inscripción, calendario, avance, pausas, registros y migración."""
import re
import sqlite3
from datetime import date, timedelta

import pytest

from core import db, planes, seed
from core.programas import (MEDICAMENTOS, ORDEN_PROGRAMAS, ORDEN_RUTAS, PROGRAMAS, ruta_sugerida)


@pytest.fixture
def con():
    c = db.connect(":memory:")
    seed.poblar(c)
    return c


@pytest.fixture
def uid(con):
    return db.crear_usuario(con, "Usuario Planes", 40, "Femenino", medicamento_declarado="Mounjaro (tirzepatida)")


# ---- catálogo
def test_catalogo_completo():
    assert set(ORDEN_RUTAS + ORDEN_PROGRAMAS) == set(PROGRAMAS)
    for pid, p in PROGRAMAS.items():
        semanas = {a[0] for a in p["actividades"]}
        assert semanas == {1, 2, 3, 4}, pid                                   # programa de 4 semanas
        assert all(1 <= a[1] <= 7 for a in p["actividades"]), pid
        for k in ("nombre", "descripcion", "profesional", "objetivos"):
            assert p[k], (pid, k)


def test_catalogo_sin_dosis_ni_prescripcion():
    """Ninguna actividad indica cantidades de medicamento, frecuencias de administración, calorías ni intensidades."""
    patron = re.compile(r"\b\d+(\.\d+)?\s*(mg|ml|ui|unidades|kcal|calor[ií]as)\b|\binyect(e|ar)\b|\baumente la dosis\b|\bsubir la dosis\b", re.I)
    for pid, p in PROGRAMAS.items():
        for a in p["actividades"]:
            texto = f"{a[3]} {a[4]}"
            assert not patron.search(texto), (pid, texto)


def test_marcas_y_principios_distinguidos():
    assert [m for m, _ in MEDICAMENTOS["tirzepatida"]["marcas"]] == ["Mounjaro", "Zepbound"]
    assert {m for m, _ in MEDICAMENTOS["semaglutida"]["marcas"]} >= {"Ozempic", "Wegovy"}
    assert {m for m, _ in MEDICAMENTOS["liraglutida"]["marcas"]} == {"Saxenda", "Victoza"}


@pytest.mark.parametrize("med,ruta", [("Mounjaro (tirzepatida)", "ruta_tirzepatida"), ("Zepbound (tirzepatida)", "ruta_tirzepatida"),
                                      ("Ozempic (semaglutida)", "ruta_semaglutida"), ("Wegovy (semaglutida)", "ruta_semaglutida"),
                                      ("Saxenda (liraglutida)", "ruta_liraglutida"), ("Victoza (liraglutida)", "ruta_liraglutida"),
                                      (None, "ruta_general"), ("Estoy considerando consultarlo", "ruta_general"), ("Metformina", "ruta_general")])
def test_ruta_sugerida(med, ruta):
    assert ruta_sugerida(med) == ruta


# ---- inscripción y calendario
def test_inscribir_crea_calendario(con, uid):
    inicio = date.today() - timedelta(days=2)
    iid = planes.inscribir(con, uid, "ruta_tirzepatida", inicio, ["Organizar controles con endocrinología"], {"dias": ["Lun"], "momento": "Mañana"})
    i = planes.obtener(con, iid)
    acts = planes.actividades(con, iid)
    assert i["estado"] == "activo" and i["medicamento_declarado"] == "Mounjaro (tirzepatida)"
    assert len(acts) == len(PROGRAMAS["ruta_tirzepatida"]["actividades"])
    a0 = acts[0]
    assert a0["fecha"] == (inicio + timedelta(days=(a0["semana"] - 1) * 7 + a0["dia"] - 1)).isoformat()
    assert max(date.fromisoformat(a["fecha"]) for a in acts) <= inicio + timedelta(days=27)        # dentro de 4 semanas
    assert i["objetivos"] == ["Organizar controles con endocrinología"] and i["preferencias"]["momento"] == "Mañana"


def test_no_duplica_inscripcion_vigente(con, uid):
    planes.inscribir(con, uid, "prog_nutricion", date.today(), ["x"])
    with pytest.raises(db.ValidationError, match="activo o en pausa"):
        planes.inscribir(con, uid, "prog_nutricion", date.today(), ["x"])
    iid = planes.vigente(con, uid, "prog_nutricion")["id"]
    planes.pausar(con, iid)
    with pytest.raises(db.ValidationError):
        planes.inscribir(con, uid, "prog_nutricion", date.today(), ["x"])                  # en pausa también cuenta
    planes.reanudar(con, iid); planes.finalizar(con, iid)
    assert planes.inscribir(con, uid, "prog_nutricion", date.today(), ["x"])                # tras finalizar se puede volver a inscribir


@pytest.mark.parametrize("kw,msg", [({"programa_id": "no_existe"}, "Programa"), ({"objetivos": []}, "objetivo"),
                                    ({"fecha_inicio": date.today() + timedelta(days=60)}, "fecha de inicio"),
                                    ({"preferencias": {"dias": ["Lunes!"]}}, "Días")])
def test_inscripcion_validaciones(con, uid, kw, msg):
    base = {"programa_id": "prog_actividad", "fecha_inicio": date.today(), "objetivos": ["x"], "preferencias": {}}
    base.update(kw)
    with pytest.raises(db.ValidationError, match=msg):
        planes.inscribir(con, uid, base["programa_id"], base["fecha_inicio"], base["objetivos"], base["preferencias"])


# ---- avance, observaciones y notas
def test_marcar_y_progreso(con, uid):
    iid = planes.inscribir(con, uid, "ruta_tirzepatida", date.today(), ["x"])
    s1 = planes.actividades(con, iid, 1)
    for a in s1[:2]:
        planes.marcar(con, a["id"], True)
    pr = planes.progreso(con, iid)
    assert pr["hechas"] == 2 and pr["pct"] == round(100 * 2 / pr["total"], 1)
    assert pr["por_semana"][0]["hechas"] == 2 and pr["semana_actual"] == 1
    assert len(pr["pendientes_semana"]) == len(s1) - 2
    planes.marcar(con, s1[0]["id"], False)
    assert planes.progreso(con, iid)["hechas"] == 1
    planes.observar(con, s1[1]["id"], "Llevé mis registros")
    assert planes.actividades(con, iid, 1)[1]["observacion"] == "Llevé mis registros"
    planes.agregar_nota(con, iid, 1, "Semana tranquila")
    assert planes.notas(con, iid)[0]["texto"] == "Semana tranquila"
    with pytest.raises(db.ValidationError):
        planes.agregar_nota(con, iid, 5, "x")


def test_semana_actual_y_pendientes_usuario(con, uid):
    iid = planes.inscribir(con, uid, "prog_seguimiento", date.today() - timedelta(days=8), ["x"])
    assert planes.progreso(con, iid)["semana_actual"] == 2
    pend = planes.pendientes_usuario(con, uid)
    assert pend and all(p["semana"] == 2 for p in pend if p["inscripcion_id"] == iid)


def test_pausar_y_reanudar(con, uid, monkeypatch):
    hoy = date.today()
    iid = planes.inscribir(con, uid, "prog_actividad", hoy, ["x"])
    a = planes.actividades(con, iid)
    planes.marcar(con, a[0]["id"], True)
    planes.pausar(con, iid)
    assert planes.obtener(con, iid)["estado"] == "pausado"
    with pytest.raises(db.ValidationError, match="Reanude"):
        planes.marcar(con, a[1]["id"], True)                                          # en pausa no se registran avances
    monkeypatch.setattr(planes, "_hoy", lambda: hoy + timedelta(days=5))               # simula 5 días de pausa
    assert planes.reanudar(con, iid) == 5
    b = planes.actividades(con, iid)
    assert b[0]["fecha"] == a[0]["fecha"]                                              # la completada no se mueve
    assert b[1]["fecha"] == (date.fromisoformat(a[1]["fecha"]) + timedelta(days=5)).isoformat()
    i = planes.obtener(con, iid)
    assert i["estado"] == "activo" and i["dias_pausa"] == 5
    assert planes.progreso(con, iid)["hechas"] == 1                                    # el avance se conserva


def test_registros_del_programa(con, uid):
    iid = planes.inscribir(con, uid, "prog_actividad", date.today(), ["x"])
    planes.registrar(con, iid, "actividad", date.today(), "Caminata en el parque", 30, "me sentí bien")
    r = planes.registros(con, iid)[0]
    assert (r["tipo"], r["minutos"], r["detalle"]) == ("actividad", 30, "Caminata en el parque")
    with pytest.raises(db.ValidationError):
        planes.registrar(con, iid, "actividad", date.today() + timedelta(days=1), "futuro")
    with pytest.raises(db.ValidationError):
        planes.registrar(con, iid, "medicamento", date.today(), "no permitido")         # no existe registro de medicación
    with pytest.raises(db.ValidationError):
        planes.registrar(con, iid, "actividad", date.today(), "x", 900)


# ---- persistencia y migración
def test_persistencia_tras_reconectar(tmp_path):
    p = tmp_path / "planes.db"
    c = db.connect(p); seed.poblar(c)
    u = db.crear_usuario(c, "Persiste", 30, "Femenino")
    iid = planes.inscribir(c, u, "ruta_general", date.today(), ["x"])
    planes.marcar(c, planes.actividades(c, iid)[0]["id"], True); c.close()
    c2 = db.connect(p)
    assert planes.obtener(c2, iid)["estado"] == "activo"
    assert planes.progreso(c2, iid)["hechas"] == 1


def test_migracion_desde_base_version_1(tmp_path):
    """Una base creada por la versión anterior (sin tablas de planes) conserva sus datos y recibe las tablas nuevas."""
    p = tmp_path / "v1.db"
    old = sqlite3.connect(p)
    old.executescript("""CREATE TABLE usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL, edad INTEGER NOT NULL, sexo TEXT NOT NULL,
                         ciudad TEXT, correo_demo TEXT, peso_kg REAL, medicamento_declarado TEXT, fecha_registro TEXT NOT NULL, es_demo INTEGER NOT NULL DEFAULT 0);
                         INSERT INTO usuarios (nombre, edad, sexo, fecha_registro, es_demo, medicamento_declarado) VALUES ('Usuario V1', 50, 'Masculino', '2026-01-01', 1, 'Ozempic');""")
    old.commit(); old.close()
    c = db.connect(p)
    assert c.execute("PRAGMA user_version").fetchone()[0] == db.SCHEMA_VERSION
    assert db.obtener_usuario(c, 1)["nombre"] == "Usuario V1"
    assert {"inscripciones", "plan_actividades", "plan_notas", "plan_registros"} <= {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert seed.poblar_planes(c) is True                                          # la demo recibe planes de ejemplo
    assert planes.listar(c, 1)


def test_seed_planes_demo(con):
    ana = planes.listar(con, 1)
    assert {i["programa_id"] for i in ana} == {"ruta_tirzepatida", "prog_nutricion"}
    assert seed.poblar_planes(con) is False                                       # no duplica
