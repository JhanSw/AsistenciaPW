# Asistencia — Streamlit + Heroku Postgres + Login + CRUD

## Novedades
- Tema azul pastel.
- Contador de resultados en Buscar.
- Edición rápida por ID (municipio, depto, entidad, nombres).
- CRUD de usuarios: crear, editar (usuario y admin), activar/inactivar, cambiar contraseña, eliminar.
- Botón Limpiar corregido (usa `st.rerun()` con fallback).

## Despliegue (Heroku UI)
1. Conecta el repo a Heroku (Deploy → GitHub → Connect).
2. Resources → Add-ons → **Heroku Postgres (Hobby Dev)**.
3. Deploy → Manual deploy.
4. More → Run console:
   ```
   python -c "from db import init_database; init_database(); from db import ensure_default_admin; ensure_default_admin(); print('OK')"
   ```
5. Open app → Login: **admin / Admin2025!** (cámbiala en **Usuarios**).
