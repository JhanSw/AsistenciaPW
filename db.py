
import os
import bcrypt
import psycopg2
from psycopg2.extras import execute_values
from urllib.parse import urlparse
import pandas as pd

SLOTS = [
    "registro_dia1_manana",
    "registro_dia1_tarde",
    "registro_dia2_manana",
    "registro_dia2_tarde",
]

def get_connection():
    url = os.environ.get("DATABASE_URL")
    if not url:
        host = os.environ.get("DB_HOST","127.0.0.1")
        user = os.environ.get("DB_USER","postgres")
        password = os.environ.get("DB_PASSWORD","")
        dbname = os.environ.get("DB_NAME","sistema_asistencia")
        port = int(os.environ.get("DB_PORT","5432"))
        sslmode = os.environ.get("DB_SSLMODE","prefer")
        return psycopg2.connect(host=host, user=user, password=password, dbname=dbname, port=port, sslmode=sslmode)
    else:
        result = urlparse(url)
        sslmode = "require" if (result.hostname or "").endswith("amazonaws.com") else os.environ.get("DB_SSLMODE","prefer")
        return psycopg2.connect(
            dbname=result.path[1:],
            user=result.username,
            password=result.password,
            host=result.hostname,
            port=result.port or 5432,
            sslmode=sslmode
        )

def init_database():
    conn = get_connection()
    with conn:
        with conn.cursor() as cur:
            try:
                cur.execute("CREATE EXTENSION IF NOT EXISTS unaccent;")
            except Exception:
                pass

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
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS assistance (
              id SERIAL PRIMARY KEY,
              person_id INT NOT NULL REFERENCES people(id) ON DELETE CASCADE,
              timestamp_utc TIMESTAMP DEFAULT NOW(),
              slot TEXT CHECK (slot IN ('registro_dia1_manana','registro_dia1_tarde','registro_dia2_manana','registro_dia2_tarde'))
            );
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
              id SERIAL PRIMARY KEY,
              username VARCHAR(100) UNIQUE NOT NULL,
              password_hash VARCHAR(200) NOT NULL,
              is_admin BOOLEAN NOT NULL DEFAULT FALSE,
              is_active BOOLEAN NOT NULL DEFAULT TRUE,
              created_at TIMESTAMP DEFAULT NOW()
            );
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS attendance_slots (
              person_id INT PRIMARY KEY REFERENCES people(id) ON DELETE CASCADE,
              registro_dia1_manana TIMESTAMP NULL,
              registro_dia1_tarde  TIMESTAMP NULL,
              registro_dia2_manana TIMESTAMP NULL,
              registro_dia2_tarde  TIMESTAMP NULL
            );
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS settings (
              key TEXT PRIMARY KEY,
              value TEXT NOT NULL
            );
            """)

            cur.execute("""
            INSERT INTO settings(key, value)
            VALUES ('active_slot', 'registro_dia1_manana')
            ON CONFLICT (key) DO NOTHING;
            """)

def ensure_default_admin():
    conn = get_connection()
    with conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM users;")
            count = cur.fetchone()[0]
            if count == 0:
                username = "admin"
                password = "Admin2025!"
                hash_ = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
                cur.execute("""
                INSERT INTO users (username, password_hash, is_admin, is_active)
                VALUES (%s, %s, TRUE, TRUE);
                """, (username, hash_))

def get_user(username):
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT id, username, password_hash, is_admin, is_active FROM users WHERE username=%s", (username,))
        return cur.fetchone()

def create_user(username, password, is_admin=False, is_active=True):
    conn = get_connection()
    with conn:
        with conn.cursor() as cur:
            hash_ = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            cur.execute("""
            INSERT INTO users (username, password_hash, is_admin, is_active)
            VALUES (%s, %s, %s, %s) RETURNING id;
            """, (username, hash_, is_admin, is_active))
            return cur.fetchone()[0]

def update_user(user_id, username=None, is_admin=None, is_active=None, password=None):
    sets = []
    params = []
    if username is not None:
        sets.append("username=%s")
        params.append(username)
    if is_admin is not None:
        sets.append("is_admin=%s")
        params.append(is_admin)
    if is_active is not None:
        sets.append("is_active=%s")
        params.append(is_active)
    if password is not None and password.strip():
        hash_ = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        sets.append("password_hash=%s")
        params.append(hash_)
    if not sets:
        return
    params.append(user_id)
    sql = "UPDATE users SET " + ", ".join(sets) + " WHERE id=%s"
    conn = get_connection()
    with conn:
        with conn.cursor() as cur:
            cur.execute(sql, tuple(params))

def delete_user(user_id):
    conn = get_connection()
    with conn:
        with conn.cursor() as cur:
            cur.execute("SELECT username FROM users WHERE id=%s", (user_id,))
            row = cur.fetchone()
            if not row: return
            if row[0] == "admin":
                raise ValueError("No se puede eliminar el usuario por defecto 'admin'.")
            cur.execute("DELETE FROM users WHERE id=%s", (user_id,))

def search_people(q="", municipality="", department="", entity="", limit=500):
    conn = get_connection()
    sql = """
    SELECT id, region, department, municipality, document, names, phone, email, position, entity
    FROM people
    WHERE 1=1
    """
    params = []
    if q:
        sql += " AND (unaccent(lower(names)) LIKE unaccent(lower(%s)) OR document ILIKE %s) "
        like = f"%{q}%"
        params.extend([like, like])
    if municipality:
        sql += " AND unaccent(lower(municipality)) LIKE unaccent(lower(%s)) "
        params.append(f"%{municipality}%")
    if department:
        sql += " AND unaccent(lower(department)) LIKE unaccent(lower(%s)) "
        params.append(f"%{department}%")
    if entity:
        sql += " AND unaccent(lower(entity)) LIKE unaccent(lower(%s)) "
        params.append(f"%{entity}%")
    sql += " ORDER BY id DESC LIMIT %s"
    params.append(limit)

    with conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
    return pd.DataFrame(rows, columns=cols)

def search_people_with_slots(q="", municipality="", department="", entity="", limit=500):
    conn = get_connection()
    sql = """
    SELECT p.id, p.region, p.department, p.municipality, p.document, p.names, p.phone, p.email, p.position, p.entity,
           s.registro_dia1_manana, s.registro_dia1_tarde, s.registro_dia2_manana, s.registro_dia2_tarde
    FROM people p
    LEFT JOIN attendance_slots s ON s.person_id = p.id
    WHERE 1=1
    """
    params = []
    if q:
        sql += " AND (unaccent(lower(p.names)) LIKE unaccent(lower(%s)) OR p.document ILIKE %s) "
        like = f"%{q}%"
        params.extend([like, like])
    if municipality:
        sql += " AND unaccent(lower(p.municipality)) LIKE unaccent(lower(%s)) "
        params.append(f"%{municipality}%")
    if department:
        sql += " AND unaccent(lower(p.department)) LIKE unaccent(lower(%s)) "
        params.append(f"%{department}%")
    if entity:
        sql += " AND unaccent(lower(p.entity)) LIKE unaccent(lower(%s)) "
        params.append(f"%{entity}%")
    sql += " ORDER BY p.id DESC LIMIT %s"
    params.append(limit)

    with conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
    return pd.DataFrame(rows, columns=cols)

UPSERT_PEOPLE_SQL = """
INSERT INTO people (region, department, municipality, document, names, phone, email, position, entity)
VALUES %s
ON CONFLICT (document) DO UPDATE
SET
  region = COALESCE(NULLIF(EXCLUDED.region, ''), people.region),
  department = COALESCE(NULLIF(EXCLUDED.department, ''), people.department),
  municipality = COALESCE(NULLIF(EXCLUDED.municipality, ''), people.municipality),
  names = COALESCE(NULLIF(EXCLUDED.names, ''), people.names),
  phone = COALESCE(NULLIF(EXCLUDED.phone, ''), people.phone),
  email = COALESCE(NULLIF(EXCLUDED.email, ''), people.email),
  position = COALESCE(NULLIF(EXCLUDED.position, ''), people.position),
  entity = COALESCE(NULLIF(EXCLUDED.entity, ''), people.entity);
"""

def upsert_people_bulk(rows):
    if not rows:
        return 0
    conn = get_connection()
    with conn:
        with conn.cursor() as cur:
            execute_values(cur, UPSERT_PEOPLE_SQL, rows, page_size=1000)
            return cur.rowcount

def get_active_slot():
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT value FROM settings WHERE key='active_slot'")
        row = cur.fetchone()
    return row[0] if row else SLOTS[0]

def set_active_slot(slot: str):
    if slot not in SLOTS:
        raise ValueError("Slot inválido")
    conn = get_connection()
    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO settings(key, value) VALUES ('active_slot', %s)
                ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value
            """, (slot,))

def ensure_attendance_slots(person_id: int):
    conn = get_connection()
    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO attendance_slots(person_id) VALUES (%s)
                ON CONFLICT (person_id) DO NOTHING
            """, (person_id,))

def mark_attendance_for_slot(person_id: int, slot: str):
    if slot not in SLOTS:
        raise ValueError("Slot inválido")
    conn = get_connection()
    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO assistance (person_id, slot) VALUES (%s, %s)
                RETURNING id
            """, (person_id, slot))
            ensure_attendance_slots(person_id)
            cur.execute(f"""
                UPDATE attendance_slots
                SET {slot} = COALESCE({slot}, NOW())
                WHERE person_id = %s
            """, (person_id,))

def find_person_by_document(document: str):
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("""
        SELECT id, region, department, municipality, document, names, phone, email, position, entity
        FROM people WHERE document=%s
        """, (document,))
        return cur.fetchone()

def create_person(**kwargs):
    fields = ["region","department","municipality","document","names","phone","email","position","entity"]
    cols = ",".join(fields)
    vals = [kwargs.get(k) for k in fields]
    placeholders = ",".join(["%s"]*len(fields))
    conn = get_connection()
    with conn:
        with conn.cursor() as cur:
            cur.execute(f"INSERT INTO people ({cols}) VALUES ({placeholders}) RETURNING id;", vals)
            return cur.fetchone()[0]
