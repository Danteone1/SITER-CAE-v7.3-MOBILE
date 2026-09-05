# SITER-CAE v7.3-MOBILE-READY

Versión preparada para cargar desde Android a GitHub y desplegar en Streamlit Community Cloud.

## Estructura mínima

```text
streamlit_app.py
siter_engine.py
requirements.txt
netlogo/
  territorial_lab_mobile.nlogo
```

## Despliegue

1. Crear repositorio en GitHub.
2. Subir **el contenido de esta carpeta**, no el ZIP.
3. En Streamlit Community Cloud seleccionar `streamlit_app.py` como Main file.
4. Opcional: publicar `netlogo/territorial_lab_mobile.nlogo` y definir el secreto `NETLOGO_MODEL_URL` con su URL pública.

## Uso

La aplicación funciona como herramienta de consultoría: el consultor configura una matriz de parámetros, ejecuta modelos Python y abre el ABM visual en NetLogo Web.

Los datos DUMMY son sintéticos. No deben presentarse como datos observados.
