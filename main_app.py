import streamlit as st
import pandas as pd
from groq import Groq

st.set_page_config(page_title="Taller IA - Analítica Docente", layout="wide")
st.title("Taller de Analítica de Datos con IA")

archivo = st.file_uploader("Sube tu CSV (basico.csv / medio.csv / experto.csv)", type="csv")

if archivo is not None:
    df = pd.read_csv(archivo)
    st.dataframe(df.head())

    # CRUCE-INTEGRADOR
    # (Nivel Integrador: pega aquí tu bloque de cruce y gráfico)

    # PIPELINE-EXPERTO
    # (Nivel Experto: pega aquí tu bloque de limpieza y análisis desagregado)

    st.subheader("Pregúntale a la IA sobre estos datos")
    prompt_usuario = st.text_area("Escribe tu instrucción:", height=180)

    if st.button("Analizar con IA"):
        api_key = st.secrets.get("GROQ_API_KEY", "")
        if not api_key:
            st.error("No se encontró GROQ_API_KEY en Secrets. Revisa el paso 3 de Desplegar.")
        else:
            client = Groq(api_key=api_key)
            respuesta = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "Eres un analista de datos educativos."},
                    {"role": "user", "content": prompt_usuario + "\n\nDatos:\n" + df.to_string()}
                ]
            )
            st.write(respuesta.choices[0].message.content)
else:
    st.info("Sube un archivo CSV para comenzar.")
