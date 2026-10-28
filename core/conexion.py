"""Conexión a la base de datos: SQLite (local) o PostgreSQL (producción).

- Si existe la variable DATABASE_URL (o el secreto de Streamlit con ese nombre) y empieza por «postgres», se usa PostgreSQL.
- Si no, se usa un archivo SQLite local (data/the_reset.db o la ruta de THE_RESET_DB).

Las funciones de la app escriben SQL con marcadores «?» y leen filas como diccionarios; este módulo traduce
esas diferencias para que el mismo código funcione en los dos motores.
"""
from __future__ import annotations

import os
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path

try:  # psycopg solo es necesario en producción
    import psycopg
    from psycopg import errors as pg_errors
except Exception:  # pragma: no cover
    psycopg = None
    pg_errors = None

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def config(clave: str, defecto=None):
    """Lee una configuración de las variables de entorno o de st.secrets."""
    v = os.environ.get(clave)
    if v not in (None, ""):
        return v
    try:
        import streamlit as st
        if clave in st.secrets:
            return str(st.secrets[clave])
    except Exception:
        pass
    return defecto


def url_bd() -> str | None:
    u = config("DATABASE_URL")
    return u if u and u.startswith(("postgres://", "postgresql://")) else None


# ------------------------------------------------------------------ errores comunes a ambos motores
IntegrityError: tuple = (sqlite3.IntegrityError,) + ((pg_errors.IntegrityError,) if pg_errors else ())


# ------------------------------------------------------------------ filas
class Fila(dict):
    """Fila que se lee por nombre de columna (fila["id"]) o por posición (fila[0])."""

    def __getitem__(self, k):
        if isinstance(k, int):
            return list(self.values())[k]
        return super().__getitem__(k)

    def keys(self):  # dict(fila) funciona igual que con sqlite3.Row
        return super().keys()


def _fabrica_filas(cursor):
    nombres = [c.name for c in (cursor.description or [])]
    return lambda valores: Fila(zip(nombres, valores))


class _Resultado:
    def __init__(self, cur, lastrowid=None, filas=None):
        self._cur, self.lastrowid, self._filas = cur, lastrowid, filas

    def fetchone(self):
        if self._filas is not None:
            return self._filas.pop(0) if self._filas else None
        return self._cur.fetchone()

    def fetchall(self):
        if self._filas is not None:
            out, self._filas = self._filas, []
            return out
        return self._cur.fetchall()

    def __iter__(self):
        return iter(self.fetchall())

    @property
    def rowcount(self):
        return self._cur.rowcount


_INSERT = re.compile(r"^\s*INSERT\s", re.I)


class ConexionPostgres:
    """Adaptador con la misma interfaz que sqlite3.Connection para el subconjunto que usa la app."""
    motor = "postgres"

    def __init__(self, url: str):
        if psycopg is None:
            raise RuntimeError("Falta el paquete psycopg: ejecute «pip install psycopg[binary]».")
        self.url = url
        self._en_tx = 0
        self._abrir()

    def _abrir(self):
        # prepare_threshold=None evita sentencias preparadas: necesario con el pooler de Supabase (modo transacción)
        self.raw = psycopg.connect(self.url, autocommit=True, prepare_threshold=None, row_factory=_fabrica_filas, connect_timeout=15)

    @staticmethod
    def _sql(sql: str) -> str:
        return sql.replace("%", "%%").replace("?", "%s")

    def _reintentar(self, fn):
        try:
            return fn()
        except psycopg.OperationalError:
            if self._en_tx:
                raise
            self._abrir()          # la conexión se cerró (inactividad o red): se reabre una vez
            return fn()

    def execute(self, sql, params=()):
        params = tuple(params or ())
        insert = bool(_INSERT.match(sql)) and "RETURNING" not in sql.upper()
        q = self._sql(sql) + (" RETURNING id" if insert else "")

        def run():
            cur = self.raw.cursor()
            cur.execute(q, params)
            if insert:
                fila = cur.fetchone()
                return _Resultado(cur, lastrowid=fila["id"] if fila else None, filas=[])
            return _Resultado(cur)
        return self._reintentar(run)

    def executemany(self, sql, seq):
        def run():
            cur = self.raw.cursor()
            cur.executemany(self._sql(sql), [tuple(p) for p in seq])
            return _Resultado(cur)
        return self._reintentar(run)

    def executescript(self, script: str):
        for stmt in script.split(";"):
            stmt = "\n".join(l for l in stmt.splitlines() if not l.strip().startswith("--")).strip()
            if stmt:
                self.raw.execute(stmt)

    @contextmanager
    def transaccion(self):
        self._en_tx += 1
        try:
            if self._en_tx == 1:
                with self.raw.transaction():
                    yield self
            else:
                yield self
        finally:
            self._en_tx -= 1

    def commit(self):   # autocommit: cada sentencia fuera de una transacción ya queda guardada
        pass

    def rollback(self):
        pass

    def close(self):
        self.raw.close()

    def columnas(self, tabla):
        return {r["column_name"] for r in self.execute("SELECT column_name FROM information_schema.columns WHERE table_name=?", (tabla,))}


class ConexionSQLite(sqlite3.Connection):
    motor = "sqlite"

    @contextmanager
    def transaccion(self):
        try:
            yield self
            self.commit()
        except Exception:
            self.rollback()
            raise

    def columnas(self, tabla):
        return {r[1] for r in self.execute(f"PRAGMA table_info({tabla})")}


def abrir(ruta_sqlite: str | Path | None = None):
    """Abre la conexión adecuada según la configuración."""
    url = None if ruta_sqlite else url_bd()
    if url:
        return ConexionPostgres(url)
    p = Path(ruta_sqlite or config("THE_RESET_DB") or DATA_DIR / "the_reset.db")
    if str(p) != ":memory:":
        p.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(p), check_same_thread=False, factory=ConexionSQLite)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA journal_mode = WAL")
    return con
