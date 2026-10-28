"""Mismo flujo completo sobre PostgreSQL real. Se ejecuta solo si existe TEST_DATABASE_URL (base desechable: se borra)."""
import os
from datetime import date, timedelta

import pytest

URL = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="Defina TEST_DATABASE_URL para probar con PostgreSQL")


@pytest.fixture
def con(monkeypatch):
    import psycopg
    with psycopg.connect(URL, autocommit=True) as c:
        c.execute("DROP SCHEMA public CASCADE"); c.execute("CREATE SCHEMA public")
    monkeypatch.setenv("DATABASE_URL", URL)
    from core import db
    c = db.connect()
    assert c.motor == "postgres"
    yield c
    c.close()


def test_flujo_completo_postgres(con):
    from core import auth, db, planes
    cid = auth.registrar_paciente(con, "ana@pg.co", "clave1234", "Ana PG", 40, "Femenino", True, True)
    with pytest.raises(db.ValidationError, match="Ya existe"):
        auth.registrar_paciente(con, "ANA@pg.co", "clave1234", "Ana PG", 40, "Femenino", True, True)
    uid = auth.iniciar_sesion(con, "ana@pg.co", "clave1234")["usuario_id"]
    pid = auth.obtener_cuenta(con, auth.registrar_profesional(con, "dra@pg.co", "Medica2027", "Dra. PG", "Nutrición", "R-1", 5, "Nutricionista",
                                                              "Cali", ["Virtual"], list(db.DIAS), True, True))["profesional_id"]
    db.cambiar_estado_profesional(con, pid, "aprobado")
    f = date.today() + timedelta(days=1)
    cita = db.crear_cita(con, uid, pid, f, "10:00", "Virtual")
    with pytest.raises(db.ValidationError):
        db.crear_cita(con, uid, pid, f, "10:00", "Virtual")
    # el índice único parcial también protege contra reservas duplicadas a nivel de base de datos
    with pytest.raises(db.IntegrityError):
        con.execute("INSERT INTO citas (usuario_id, profesional_id, fecha, hora, modalidad, estado, creado, actualizado) VALUES (?,?,?,?,?,'programada',?,?)",
                    (uid, pid, f.isoformat(), "10:00", "Virtual", db.now(), db.now()))
    db.reprogramar_cita(con, cita, f, "11:00")
    iid = planes.inscribir(con, uid, "ruta_tirzepatida", None, ["x"])
    planes.pausar(con, iid)
    con.execute("UPDATE inscripciones SET fecha_pausa=? WHERE id=?", ((date.today() - timedelta(days=2)).isoformat(), iid))
    antes = planes.actividades(con, iid)[0]["fecha"]
    assert planes.reanudar(con, iid) == 2
    assert planes.actividades(con, iid)[0]["fecha"] == (date.fromisoformat(antes) + timedelta(days=2)).isoformat()
    rid = db.guardar_reporte(con, uid, {"descripcion": "náuseas", "edad": 40, "sexo": "Femenino", "peso_kg": 80}, True)
    assert db.actualizar_reporte(con, rid, {"desenlace": "Recuperado"}) == "borrador"
    assert db.indicadores(con)["pct_4_minimos"] == 100.0
    assert len(db.exportar_datos(con, uid)) > 100
    auth.eliminar_cuenta_paciente(con, cid, "clave1234")
    assert con.execute("SELECT COUNT(*) FROM citas").fetchone()[0] == 0
