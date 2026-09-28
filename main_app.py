import streamlit as st
import pandas as pd
import plotly.express as px
from groq import Groq

st.set_page_config(
    page_title="Taller IA - Analítica Docente",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.title("Taller de Analítica de Datos con IA")

# ---------- Barra lateral (menú izquierdo): configuración de la IA ----------
st.sidebar.header("🔑 Configuración de la IA")

api_key_input = st.sidebar.text_input(
    "Pega aquí tu API Key de Groq",
    type="password",
    placeholder="gsk_...",
    help="Se usa solo mientras esta pestaña está abierta. No queda guardada en el repositorio.",
)

api_key = api_key_input.strip()
if not api_key:
    # Alternativa: si la llave está en Settings -> Secrets, se usa automáticamente
    try:
        api_key = st.secrets.get("GROQ_API_KEY", "")
    except Exception:
        api_key = ""

if api_key:
    st.sidebar.success("Llave detectada ✅")
else:
    st.sidebar.warning("Falta la API Key. Pégala arriba para poder usar la IA.")

MODELOS = ["openai/gpt-oss-20b", "openai/gpt-oss-120b"]
modelo_lista = st.sidebar.selectbox("Modelo de IA", MODELOS, index=0)
modelo_manual = st.sidebar.text_input(
    "¿Otro modelo? Escribe su ID (opcional)",
    placeholder="ej. openai/gpt-oss-120b",
)
modelo = modelo_manual.strip() or modelo_lista

temperatura = st.sidebar.slider("Creatividad (temperature)", 0.0, 1.5, 0.4, 0.1)
max_filas = st.sidebar.slider("Filas que se envían a la IA", 20, 200, 100, 10)

# ---------- Carga de datos ----------
archivo = st.file_uploader("Sube tu CSV (basico.csv / medio.csv / experto.csv)", type="csv")

if archivo is not None:
    df = pd.read_csv(archivo)
    st.dataframe(df.head())

    # Texto con los resultados que calculas abajo, para que la IA también los vea
    contexto_extra = ""

    # CRUCE-INTEGRADOR
    # (Nivel Integrador: pega aquí tu bloque de cruce y gráfico)

    # PIPELINE-EXPERTO
    # (Nivel Experto: pega aquí tu bloque de limpieza y análisis desagregado)

    st.subheader("Pregúntale a la IA sobre estos datos")
    prompt_usuario = st.text_area("Escribe tu instrucción:", height=180)

    if st.button("Analizar con IA"):
        if not api_key:
            st.error("Falta tu API Key de Groq. Pégala en el menú de la izquierda 👈")
        elif not prompt_usuario.strip():
            st.warning("Escribe primero una instrucción para la IA.")
        else:
            mensaje = prompt_usuario + "\n\nDatos (CSV):\n" + df.head(max_filas).to_csv(index=False)
            if contexto_extra:
                mensaje += "\n\nResultados calculados en la app:\n" + contexto_extra
            try:
                client = Groq(api_key=api_key)
                with st.spinner("La IA está analizando..."):
                    respuesta = client.chat.completions.create(
                        model=modelo,
                        temperature=temperatura,
                        messages=[
                            {
                                "role": "system",
                                "content": "Eres un analista de datos educativos. Responde en español, de forma clara y concisa.",
                            },
                            {"role": "user", "content": mensaje},
                        ],
                    )
                st.write(respuesta.choices[0].message.content)
            except Exception as e:
                st.error(f"No se pudo obtener respuesta de la IA: {e}")
                st.info(
                    "Si el error menciona límite (429), espera 30 segundos y reintenta. "
                    "Si menciona tamaño (413), baja 'Filas que se envían a la IA' en el menú izquierdo. "
                    "Si dice que el modelo no existe, cambia el modelo en el menú izquierdo."
                )
else:
    st.info("Sube un archivo CSV para comenzar.")
