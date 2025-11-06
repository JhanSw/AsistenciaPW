# Sistema de Asistencia — Streamlit en Heroku (Postgres)

## Despliegue
```bash
heroku login
git init
heroku create asistencia-streamlit-uni
heroku buildpacks:set heroku/python -a asistencia-streamlit-uni
heroku addons:create heroku-postgresql:hobby-dev -a asistencia-streamlit-uni

git add .
git commit -m "deploy"
git branch -M main
git push heroku main

# Crear tablas
heroku run python -c "from db import init_database; init_database(); print('OK')" -a asistencia-streamlit-uni

# Abrir
heroku open -a asistencia-streamlit-uni
```
