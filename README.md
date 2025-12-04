# Módulo de Certificados (público)

- `routes/certificates.py`: lector del Excel (Documento / Nombre completo / ASISTENCIA) y generador de PDF encima de la plantilla.
- Pon tu plantilla en `assets/Certificado Congreso Gobernación.pdf` (o `assets/certificado_base.pdf`).

## Cómo funciona
1. Entra a la app y elige **Certificados** en el menú (es público).
2. Sube el Excel. Se aceptan encabezados flexibles (se normalizan a: `document`, `names`, `percent`).
3. Escribe el documento. Si la asistencia >= 75%, se habilita **Descargar certificado (PDF)**.

> Si tu proyecto tiene autenticación para el resto de módulos, la mantuvimos en un *expander* de “Ingreso administrador (opcional)”.

## Dependencias
Asegúrate de tener en `requirements.txt` (o instaladas):
```
pandas
streamlit
reportlab
PyPDF2
openpyxl
```
