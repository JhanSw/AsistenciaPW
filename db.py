import os
from urllib.parse import urlparse
from datetime import datetime, timezone

import pandas as pd
import psycopg2
import psycopg2.pool

DATABASE_URL = os.getenv("DATABASE_URL", "")

if DATABASE_URL:
    parsed = urlparse(DATABASE_URL)
    DB_HOST = parsed.hostname
    DB_USER = parsed.username
    DB_PASSWORD = parsed.password
    DB_NAME = parsed.path.lstrip("/")
    DB_PORT = parsed.port or 5432
    SSLMODE = "require"
else:
    def _get_env(name, default=""):
        return str(os.getenv(name, default))
    DB_HOST = _get_env("DB_HOST", "localhost")
    DB_USER = _get_env("DB_USER", "postgres")
    DB_PASSWORD = _get_env("DB_PASSWORD", "")
    DB_NAME = _get_env("DB_NAME", "sistema_asistencia")
    DB_PORT = int(_get_env("DB_PORT", "5432"))
    SSLMODE = _get_env("DB_SSLMODE", "prefer")

POOL = psycopg2.pool.SimpleConnectionPool(
    1, 10,
    host=DB_HOST,
    user=DB_USER,
    password=DB_PASSWORD,
    dbname=DB_NAME,
    port=DB_PORT,
    sslmode=SSLMODE,
    connect_timeout=10,
)

def get_db_connection():
    return POOL.getconn()

def put_db_connection(conn):
    POOL.putconn(conn)

def init_database():
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS people (
            id SERIAL PRIMARY KEY,
            region VARCHAR(255),
            department VARCHAR(255),
            municipality VARCHAR(255),
            document VARCHAR(50) UNIQUE NOT NULL,
            names VARCHAR(255) NOT NULL,
            phone VARCHAR(50),
            email VARCHAR(255),
            position VARCHAR(255),
            entity VARCHAR(255)
        );
    """ )
    cur.execute("""
        CREATE TABLE IF NOT EXISTS assistance (
            id SERIAL PRIMARY KEY,
            person_id INT NOT NULL,
            timestamp_utc TIMESTAMP DEFAULT NOW()
        );
    """ )
    conn.commit(); cur.close(); put_db_connection(conn)

def get_person_by_document(document):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute("""SELECT id, region, department, municipality, document, names, phone, email, position, entity
                    FROM people WHERE document=%s""", (str(document),))
    row = cur.fetchone(); cur.close(); put_db_connection(conn)
    if not row: return None
    cols = ["id","region","department","municipality","document","names","phone","email","position","entity"]
    return dict(zip(cols, row))

def add_person(region, department, municipality, document, names, phone, email, position, entity):
    conn = get_db_connection(); cur = conn.cursor()
    try:
        cur.execute("""INSERT INTO people (region, department, municipality, document, names, phone, email, position, entity)
                     VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",                    (region, department, municipality, document, names, phone, email, position, entity))
        pid = cur.fetchone()[0]; conn.commit(); return pid
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        cur.execute("SELECT id FROM people WHERE document=%s", (document,))
        r = cur.fetchone(); return r[0] if r else None
    finally:
        cur.close(); put_db_connection(conn)

def add_assistance(person_id):
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO assistance (person_id, timestamp_utc) VALUES (%s, %s) RETURNING id",                (person_id, now_utc))
    aid = cur.fetchone()[0]; conn.commit(); cur.close(); put_db_connection(conn)
    return aid

def get_all_people():
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute("""
        SELECT p.*, la.last_ts AS last_assistance_utc
        FROM people p
        LEFT JOIN (
            SELECT person_id, MAX(timestamp_utc) AS last_ts
            FROM assistance
            GROUP BY person_id
        ) la ON p.id = la.person_id
        ORDER BY p.names
    """ )
    rows = cur.fetchall(); cols = [d.name for d in cur.description]
    cur.close(); put_db_connection(conn)
    return [dict(zip(cols, r)) for r in rows]

def get_all_assistances():
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute("""
        SELECT a.id, p.names, p.document, a.timestamp_utc
        FROM assistance a
        JOIN people p ON a.person_id = p.id
        ORDER BY a.timestamp_utc DESC
    """ )
    rows = cur.fetchall(); cols = [d.name for d in cur.description]
    cur.close(); put_db_connection(conn)
    return [dict(zip(cols, r)) for r in rows]

def remove_assistance(assistance_id):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute("DELETE FROM assistance WHERE id=%s", (assistance_id,))
    conn.commit(); ok = cur.rowcount > 0
    cur.close(); put_db_connection(conn)
    return ok
