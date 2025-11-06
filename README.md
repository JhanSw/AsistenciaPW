# Asistencia — Streamlit + Heroku Postgres + Login

## Despliegue Heroku (UI)
1. Conecta este repo a Heroku (Deploy → GitHub → Connect).
2. Add-on: Resources → Add-ons → **Heroku Postgres (Hobby Dev)**.
3. Manual deploy (Deploy → Manual deploy).
4. More → Run console:
   ```
   python -c "from db import init_database; init_database(); from db import ensure_default_admin; ensure_default_admin(); print('OK')"
   ```
5. Open app → Login: **admin / Admin2025!** (cámbiala en módulo **Usuarios**).

## Notas
- Tema azul pastel en `.streamlit/config.toml`.
- Botón **Limpiar** usa `st.rerun()` (fallback a `experimental_rerun`).
- Módulo **Usuarios** solo visible para admin.
