# 🧭 Trayectoria de IA: Analítica de Datos

Repositorio de apoyo para la clase **"IA para analítica de datos"** del Diplomado de IA para Docentes (EAFIT). Aquí están el código base de la app, los datasets del taller y la guía interactiva paso a paso.

- **Arquitectura del taller:** GitHub (control de versiones) → Streamlit (prototipado) → Groq (IA)
- **Duración de la sesión:** 2 horas
- **Perfil de los participantes:** docentes de distintas áreas (salud, humanidades, ingeniería, matemáticas), con tres rutas según su comodidad con el código: Explorador, Integrador y Experto.

## 📁 Contenido del repositorio

| Archivo | Descripción |
|---|---|
| `main_app.py` | Código base de la app en Streamlit. Incluye los puntos `# CRUCE-INTEGRADOR` y `# PIPELINE-EXPERTO` donde cada ruta agrega su propio código. |
| `requirements.txt` | Librerías necesarias para el despliegue (`streamlit`, `pandas`, `groq`, `plotly`, `numpy`). |
| `maestro.csv` | Dataset completo — 200 estudiantes, base de la que se derivan las tres vistas por nivel. |
| `basico.csv` | Vista recortada para la ruta Explorador (id, nota final, comentario). |
| `medio.csv` | Vista recortada para la ruta Integrador (participación, horario, nota final). |
| `experto.csv` | Vista completa para la ruta Experto, con ruido intencional (nulos y un valor en texto) para forzar limpieza de datos. |

Los datos son generados para fines pedagógicos de este taller; no corresponden a estudiantes reales.

## 🚀 Cómo empezar

Elige una de las dos rutas para tener tu propia copia editable:

### Opción A — Haz un fork de este repositorio
1. Da clic en **Fork** (arriba a la derecha de esta página).
2. Elige tu cuenta de GitHub como destino.
3. Confirma que tu copia haya quedado **pública** (Settings → visibilidad).

### Opción B — Crea tu propio repositorio desde cero
1. Ve a [github.com/new](https://github.com/new), nómbralo y marca **Public**.
2. Crea `main_app.py` y `requirements.txt` copiando el contenido de este repositorio.
3. Sube los 4 archivos CSV.

## ☁️ Desplegar en Streamlit Community Cloud

1. Entra a [share.streamlit.io](https://share.streamlit.io) con tu cuenta de GitHub.
2. **Create app** → elige tu repositorio (el fork o el que creaste) → *Main file path*: `main_app.py` → **Deploy**.
3. En `Settings → Secrets` de tu app, agrega:
   ```
   GROQ_API_KEY = "tu-llave-aquí"
   ```
   (genera tu llave gratuita en [console.groq.com](https://console.groq.com))
4. Sube uno de los CSV y da clic en "Analizar con IA" para confirmar que todo funciona.

## 📘 Guía interactiva del taller

La guía paso a paso (con las 3 misiones, el diagrama de flujo, autoevaluación y material de apoyo) vive en:

🔗 *[agrega aquí el link de tu guía publicada, por ejemplo en Netlify]*

## 🧠 Sobre el modelo de IA

El código usa la API de [Groq](https://console.groq.com/docs) con el modelo `llama-3.3-70b-versatile`. Los modelos disponibles cambian con el tiempo — si el despliegue falla por un modelo no encontrado, revisa la consola de Groq y actualiza el nombre en `main_app.py`.

## ✍️ Autor

**Jorge Iván Padilla Buriticá**
📧 [jipadillab@eafit.edu.co](mailto:jipadillab@eafit.edu.co)
🔗 [linkedin.com/in/jipadilla](https://www.linkedin.com/in/jipadilla)

## 📄 Uso

Material de uso académico para el Diplomado de IA para Docentes (EAFIT). Puedes usarlo, adaptarlo y compartirlo para fines educativos citando al autor.
