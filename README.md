# App de Confirmación de Asistencia (Streamlit + Postgres)

Incluye:
- Autenticación con bcrypt (usuario por defecto: `admin` / `Admin2025!`)
- Módulos: Asistencia, Buscar, Nuevo, Usuarios (admin), Importar (admin)
- Filtros de búsqueda por Municipio / Provincia-Departamento / Entidad
- Descarga a Excel (.xlsx)
- Importar Excel con mapeo de columnas y upsert por Documento
- 4 momentos de asistencia con selector global (solo admin):
  - registro_dia1_manana
  - registro_dia1_tarde
  - registro_dia2_manana
  - registro_dia2_tarde

## Ejecución local
1. Crea una base de datos Postgres o configura `DATABASE_URL` en `.env`
2. `pip install -r requirements.txt`
3. `streamlit run main.py`

## Inicialización DB / Admin

```
python -c "from db import init_database, ensure_default_admin; init_database(); ensure_default_admin(); print('OK')"
```

## Heroku
- Procfile incluido; agrega Heroku Postgres como add-on.
