"""
Taller de Analítica de Datos con IA
-----------------------------------
La app tiene 4 pestañas que se recorren en orden:
  1 · Carga de datos          → subes un CSV o eliges uno del repositorio
  2 · EDA estándar            → calidad, estadísticas y gráficos básicos
  3 · Análisis de datos       → comparaciones (cuantitativo) y texto (cualitativo)
  4 · Análisis con IA         → la IA interpreta tus datos y resultados
"""
import io
import re
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from groq import Groq

st.set_page_config(
    page_title="Taller IA - Analítica Docente",
    layout="wide",
    initial_sidebar_state="expanded",
)

CARPETA = Path(__file__).parent
MODELOS = ["openai/gpt-oss-20b", "openai/gpt-oss-120b"]

# Orden lógico de variables ordinales (se usa para ordenar tablas y gráficos)
ORDEN_CATEGORIAS = {
    "participacion_clase": ["Nula", "Baja", "Media", "Alta"],
    "horario_estudio": ["Mañana", "Tarde", "Noche"],
}

# Palabras muy comunes que no aportan al conteo de palabras
STOPWORDS = set(
    """para como pero porque cuando sobre tambien también hasta donde desde todo todos otros otras
    antes algunos estos estas esos esas mucho muchos poco estar algo este esta esto entre cada muy
    fueron tuve tuvo tener tiene tenia había hubo siempre durante varias varios cual quien
    ellos ellas nosotros mismo misma eran sido estaba estuvo sentí siento""".split()
)

PLANTILLAS = {
    "Patrones en los comentarios": (
        "Lee los comentarios de texto libre y agrúpalos en 3 o 4 temas recurrentes. "
        "Indica qué temas aparecen más entre los estudiantes con nota baja (menor a 3.0) y si el "
        "problema parece de capacidad o de causas logísticas/externas."
    ),
    "Diferencias entre grupos": (
        "Con los resultados calculados, explica qué grupo o combinación de variables se sale del "
        "patrón general y propón 2 hipótesis que lo expliquen. Advierte si alguna lectura global "
        "podría engañar al desagregar por subgrupos (por ejemplo, una Paradoja de Simpson)."
    ),
    "Recomendación para la coordinación": (
        "Escribe un párrafo de máximo 80 palabras dirigido a la coordinación académica, con una "
        "recomendación concreta y accionable basada en los datos y en los resultados calculados."
    ),
    "Calidad de los datos": (
        "Revisa la muestra y el resumen: ¿qué problemas de calidad ves (vacíos, valores raros, "
        "formatos mezclados) y qué pasos de limpieza propones antes de analizar?"
    ),
    "Personalizado (escribe el tuyo)": "",
}


# =============================== Funciones de apoyo ===============================
def leer_csv(fuente):
    """Lee un CSV (bytes o ruta). Prueba UTF-8 y Latin-1, y el separador ';'."""
    def _abrir():
        return io.BytesIO(fuente) if isinstance(fuente, (bytes, bytearray)) else fuente

    df, codificacion = None, "utf-8"
    for codificacion in ("utf-8", "latin-1"):
        try:
            df = pd.read_csv(_abrir(), encoding=codificacion)
            break
        except UnicodeDecodeError:
            continue
    if df is not None and df.shape[1] == 1 and ";" in str(df.columns[0]):
        df = pd.read_csv(_abrir(), sep=";", encoding=codificacion)
    return df


def clasificar_columnas(df):
    """Separa las columnas en: numéricas, mixtas (número con texto), ids, textos y categóricas."""
    tipos = {"numericas": [], "mixtas": [], "ids": [], "textos": [], "categoricas": []}
    for col in df.columns:
        serie = df[col]
        if pd.api.types.is_numeric_dtype(serie):
            tipos["numericas"].append(col)
            continue
        como_texto = serie.dropna().astype(str)
        if como_texto.empty:
            tipos["categoricas"].append(col)
        elif pd.to_numeric(como_texto, errors="coerce").notna().mean() >= 0.9:
            tipos["mixtas"].append(col)
        elif serie.nunique() == serie.notna().sum() and como_texto.str.len().mean() < 20:
            tipos["ids"].append(col)
        elif como_texto.str.len().mean() >= 40:
            tipos["textos"].append(col)
        else:
            tipos["categoricas"].append(col)
    return tipos


def etiqueta_tipo(col, tipos):
    if col in tipos["ids"]:
        return "Identificador"
    if col in tipos["numericas"]:
        return "Número"
    if col in tipos["mixtas"]:
        return "Número con texto mezclado ⚠️"
    if col in tipos["textos"]:
        return "Texto libre"
    return "Categoría"


def limpieza_rapida(df):
    """Convierte a número lo que parece numérico y rellena vacíos numéricos con la mediana."""
    df = df.copy()
    tipos = clasificar_columnas(df)
    for col in tipos["mixtas"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]) and df[col].isna().any():
            df[col] = df[col].fillna(df[col].median())
    return df


def orden_de(col, serie):
    """Orden de categorías: el lógico si existe, si no el alfabético."""
    if col in ORDEN_CATEGORIAS:
        presentes = set(serie.dropna().unique())
        return [c for c in ORDEN_CATEGORIAS[col] if c in presentes]
    return sorted(serie.dropna().unique().tolist(), key=str)


def frecuencia_palabras(serie, top=15):
    conteo = {}
    for texto in serie.dropna().astype(str):
        for palabra in re.findall(r"[a-záéíóúñü]{4,}", texto.lower()):
            if palabra not in STOPWORDS:
                conteo[palabra] = conteo.get(palabra, 0) + 1
    ordenado = sorted(conteo.items(), key=lambda x: -x[1])[:top]
    return pd.DataFrame(ordenado, columns=["palabra", "frecuencia"])


def grafico_palabras(tabla, titulo):
    if tabla.empty:
        st.caption("Sin palabras para mostrar.")
        return
    fig = px.bar(tabla.sort_values("frecuencia"), x="frecuencia", y="palabra", orientation="h", title=titulo)
    st.plotly_chart(fig)


# ================================ Barra lateral =================================
st.title("Taller de Analítica de Datos con IA")
st.sidebar.header("🔑 Configuración de la IA")

api_key_input = st.sidebar.text_input(
    "Pega aquí tu API Key de Groq",
    type="password",
    placeholder="gsk_...",
    help="Se usa solo mientras esta pestaña está abierta. No queda guardada en el repositorio.",
)
api_key = api_key_input.strip()
if not api_key:
    try:  # Alternativa: llave guardada en Settings -> Secrets
        api_key = st.secrets.get("GROQ_API_KEY", "")
    except Exception:
        api_key = ""

if api_key:
    st.sidebar.success("Llave detectada ✅")
else:
    st.sidebar.warning("Falta la API Key. Pégala arriba para usar la pestaña 4.")

modelo_lista = st.sidebar.selectbox("Modelo de IA", MODELOS, index=0)
modelo_manual = st.sidebar.text_input(
    "¿Otro modelo? Escribe su ID (opcional)", placeholder="ej. openai/gpt-oss-120b"
)
modelo = modelo_manual.strip() or modelo_lista
temperatura = st.sidebar.slider("Creatividad (temperature)", 0.0, 1.5, 0.4, 0.1)
max_filas = st.sidebar.slider("Filas de datos que se envían a la IA", 20, 200, 100, 10)

# ==================================== Pestañas ===================================
tab1, tab2, tab3, tab4 = st.tabs(
    ["1 · Carga de datos", "2 · EDA estándar", "3 · Análisis de datos", "4 · Análisis con IA"]
)

df = None                 # DataFrame con el que trabajan las pestañas 2, 3 y 4
nombre_datos = ""
contexto_extra = ""       # Texto adicional que viaja a la IA (ver extensión en la pestaña 3)

# ------------------------------- 1 · Carga de datos -------------------------------
with tab1:
    st.subheader("Carga de datos")
    origen = st.radio(
        "¿De dónde quieres cargar los datos?",
        ["Subir un archivo CSV", "Usar un CSV del repositorio"],
        horizontal=True,
    )

    if origen == "Subir un archivo CSV":
        archivo = st.file_uploader("Sube tu CSV (basico.csv / medio.csv / experto.csv)", type="csv")
        if archivo is not None:
            try:
                st.session_state["df_original"] = leer_csv(archivo.getvalue())
                st.session_state["nombre_datos"] = archivo.name
            except Exception as e:
                st.error(f"No pude leer ese archivo: {e}")
    else:
        csvs = sorted(p.name for p in CARPETA.glob("*.csv"))
        if csvs:
            elegido = st.selectbox("CSV encontrados en el repositorio", csvs)
            if st.button("Cargar este archivo", key="btn_cargar_repo"):
                try:
                    st.session_state["df_original"] = leer_csv(CARPETA / elegido)
                    st.session_state["nombre_datos"] = elegido
                except Exception as e:
                    st.error(f"No pude leer ese archivo: {e}")
        else:
            st.warning("No hay archivos .csv en la carpeta del repositorio. Sube uno con la otra opción.")

    df_original = st.session_state.get("df_original")
    if df_original is None:
        st.info("Aún no hay datos cargados. Sube un archivo o elige uno del repositorio.")
    else:
        nombre_datos = st.session_state.get("nombre_datos", "datos")
        limpiar = st.checkbox(
            "Limpieza rápida (convierte a número lo que parezca numérico y rellena vacíos numéricos con la mediana)",
            value=False,
        )
        df = limpieza_rapida(df_original) if limpiar else df_original

        tipos = clasificar_columnas(df)
        st.success(f"Datos cargados: **{nombre_datos}** — {df.shape[0]} filas × {df.shape[1]} columnas")
        c1, c2, c3 = st.columns(3)
        c1.metric("Columnas numéricas", len(tipos["numericas"]))
        c2.metric("Columnas categóricas", len(tipos["categoricas"]))
        c3.metric("Columnas de texto libre", len(tipos["textos"]))
        st.markdown("**Vista previa (primeras 20 filas):**")
        st.dataframe(df.head(20))

# --------------------------------- 2 · EDA estándar --------------------------------
with tab2:
    st.subheader("Exploración estándar de los datos (EDA)")
    if df is None:
        st.info("Primero carga tus datos en la pestaña 1.")
    else:
        tipos = clasificar_columnas(df)
        num, cat = tipos["numericas"], tipos["categoricas"]

        # Resumen general
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Filas", df.shape[0])
        c2.metric("Columnas", df.shape[1])
        c3.metric("Filas duplicadas", int(df.duplicated().sum()))
        c4.metric("Celdas vacías", int(df.isna().sum().sum()))

        # Calidad de los datos
        st.markdown("### Calidad de los datos")
        calidad = pd.DataFrame(
            {
                "columna": df.columns,
                "tipo detectado": [etiqueta_tipo(c, tipos) for c in df.columns],
                "vacíos": df.isna().sum().values,
                "% vacíos": (df.isna().mean() * 100).round(1).values,
                "valores únicos": df.nunique().values,
            }
        )
        st.dataframe(calidad)
        for col in tipos["mixtas"]:
            no_numerico = pd.to_numeric(df[col], errors="coerce").isna() & df[col].notna()
            raros = df.loc[no_numerico, col].astype(str).unique().tolist()
            st.warning(
                f"⚠️ La columna **{col}** parece numérica pero tiene texto mezclado: {raros[:5]}. "
                "Puedes corregirlo con la 'Limpieza rápida' de la pestaña 1."
            )
        hay_vacios = calidad[calidad["vacíos"] > 0]
        if not hay_vacios.empty:
            st.plotly_chart(px.bar(hay_vacios, x="columna", y="vacíos", title="Celdas vacías por columna"))

        # Estadísticas descriptivas
        if num:
            st.markdown("### Estadísticas de las variables numéricas")
            st.dataframe(df[num].describe().T.round(2))

        # Distribución de una variable
        st.markdown("### Distribución de una variable")
        explorables = num + cat
        if explorables:
            variable = st.selectbox("Elige una variable", explorables, key="eda_variable")
            if variable in num:
                col_a, col_b = st.columns(2)
                col_a.plotly_chart(px.histogram(df, x=variable, title=f"Histograma de {variable}"))
                col_b.plotly_chart(px.box(df, y=variable, title=f"Diagrama de caja de {variable}"))
            else:
                conteo = df[variable].value_counts(dropna=False).reset_index()
                conteo.columns = [variable, "cantidad"]
                orden = orden_de(variable, df[variable])
                st.plotly_chart(
                    px.bar(conteo, x=variable, y="cantidad", title=f"Frecuencia de {variable}",
                           category_orders={variable: orden} if orden else None)
                )
        else:
            st.caption("No hay variables numéricas ni categóricas para graficar.")

        # Correlaciones
        if len(num) >= 2:
            st.markdown("### Correlaciones entre variables numéricas")
            corr = df[num].corr().round(2)
            st.plotly_chart(
                px.imshow(corr, text_auto=True, zmin=-1, zmax=1, color_continuous_scale="RdBu_r", aspect="auto")
            )

# ----------------------- 3 · Análisis cuantitativo y cualitativo ------------------------
resumen_analisis = ""
with tab3:
    st.subheader("Análisis de datos: cuantitativo y cualitativo")
    if df is None:
        st.info("Primero carga tus datos en la pestaña 1.")
    else:
        tipos = clasificar_columnas(df)
        num, cat, textos = tipos["numericas"], tipos["categoricas"], tipos["textos"]
        partes = [f"Archivo: {nombre_datos} ({df.shape[0]} filas, columnas: {', '.join(map(str, df.columns))})"]

        # ---------- Cuantitativo ----------
        st.markdown("## 📊 Análisis cuantitativo")
        objetivo = None
        if not num:
            st.warning("No hay columnas numéricas para analizar. Usa la 'Limpieza rápida' de la pestaña 1 "
                       "si hay números guardados como texto.")
        else:
            idx = num.index("nota_final") if "nota_final" in num else 0
            objetivo = st.selectbox("Variable numérica a analizar", num, index=idx, key="objetivo")
            serie_obj = df[objetivo].dropna()
            partes.append(
                f"Variable analizada: {objetivo}. Promedio {serie_obj.mean():.2f}, mediana {serie_obj.median():.2f}, "
                f"mínimo {serie_obj.min():.2f}, máximo {serie_obj.max():.2f}, desviación {serie_obj.std():.2f}."
            )

            if cat:
                grupos = st.multiselect(
                    f"Compara '{objetivo}' según estas categorías (máximo 3)",
                    cat, default=cat[:1], max_selections=3, key="grupos",
                )
                if grupos:
                    tabla = (
                        df.groupby(grupos, observed=True)[objetivo]
                        .agg(cantidad="count", promedio="mean", mediana="median", desviacion="std")
                        .round(2)
                        .reset_index()
                    )
                    st.dataframe(tabla)
                    ordenes = {g: orden_de(g, df[g]) for g in grupos}
                    color = grupos[1] if len(grupos) > 1 else None
                    st.plotly_chart(
                        px.bar(tabla, x=grupos[0], y="promedio", color=color, barmode="group",
                               title=f"Promedio de {objetivo} por {' y '.join(grupos)}",
                               category_orders=ordenes)
                    )
                    st.plotly_chart(
                        px.box(df, x=grupos[0], y=objetivo, color=color,
                               title=f"Distribución de {objetivo} por {' y '.join(grupos)}",
                               category_orders=ordenes)
                    )
                    partes.append(f"Promedio de {objetivo} por {' y '.join(grupos)}:\n{tabla.to_string(index=False)}")

            if len(cat) >= 2:
                st.markdown("**Cruce de dos categorías (mapa de calor del promedio)**")
                f1, f2 = st.columns(2)
                fila = f1.selectbox("Categoría en las filas", cat, index=0, key="cruce_fila")
                columna = f2.selectbox("Categoría en las columnas", cat, index=1, key="cruce_columna")
                if fila != columna:
                    pivote = df.pivot_table(index=fila, columns=columna, values=objetivo, aggfunc="mean").round(2)
                    pivote = pivote.reindex(index=orden_de(fila, df[fila]), columns=orden_de(columna, df[columna]))
                    st.plotly_chart(
                        px.imshow(pivote, text_auto=".2f", color_continuous_scale="RdYlGn", aspect="auto",
                                  title=f"Promedio de {objetivo}: {fila} × {columna}")
                    )
                    partes.append(f"Cruce {fila} × {columna} (promedio de {objetivo}):\n{pivote.to_string()}")
                else:
                    st.caption("Elige dos categorías distintas para ver el cruce.")

            otras = [c for c in num if c != objetivo]
            if otras:
                correl = df[otras + [objetivo]].corr()[objetivo].drop(objetivo).round(2).sort_values()
                st.markdown(f"**Correlación de las demás variables numéricas con {objetivo}**")
                tabla_corr = correl.reset_index()
                tabla_corr.columns = ["variable", "correlación"]
                st.plotly_chart(px.bar(tabla_corr, x="correlación", y="variable", orientation="h"))
                partes.append(f"Correlación con {objetivo}:\n{correl.to_string()}")

        # ---------- Cualitativo ----------
        st.markdown("## 💬 Análisis cualitativo (texto libre)")
        if not textos:
            st.info("No detecté columnas de texto libre en estos datos (por ejemplo, comentarios). "
                    "Usa el archivo basico.csv o experto.csv para esta sección.")
        else:
            col_texto = st.selectbox("Columna de texto a analizar", textos, key="col_texto")
            st.markdown("**Palabras más frecuentes**")
            frec = frecuencia_palabras(df[col_texto], top=15)
            grafico_palabras(frec, "Top 15 palabras")
            if not frec.empty:
                partes.append("Palabras más frecuentes en los comentarios: " + ", ".join(
                    f"{r.palabra} ({r.frecuencia})" for r in frec.head(10).itertuples()))

            st.markdown("**¿Qué temas se mencionan y cómo se relacionan con la nota?**")
            claves_txt = st.text_input(
                "Palabras clave (separadas por coma; basta con el inicio de la palabra)",
                value="internet, conexi, conect, trabajo, tiempo, coordin, computador, turnos, señal, plataforma",
                key="claves",
            )
            claves = [k.strip().lower() for k in claves_txt.split(",") if k.strip()]
            textos_min = df[col_texto].fillna("").astype(str).str.lower()
            if claves:
                menciona = textos_min.apply(lambda t: any(k in t for k in claves))
            else:
                menciona = pd.Series(False, index=df.index)
            st.metric("Comentarios que mencionan alguna palabra clave", f"{int(menciona.sum())} de {len(df)}")

            if objetivo is not None:
                minimo, maximo = float(df[objetivo].min()), float(df[objetivo].max())
                if minimo < maximo:
                    umbral = st.slider(
                        f"Umbral de {objetivo} para separar 'bajo' de 'alto'",
                        minimo, maximo, min(max(3.0, minimo), maximo), key="umbral",
                    )
                    bajo = df[objetivo] < umbral
                    tabla_m = (
                        pd.DataFrame({
                            "menciona": menciona.map({True: "Menciona palabra clave", False: "No la menciona"}),
                            objetivo: df[objetivo],
                        })
                        .groupby("menciona")[objetivo].agg(cantidad="count", promedio="mean").round(2).reset_index()
                    )
                    st.dataframe(tabla_m)
                    if bajo.sum() > 0 and (~bajo).sum() > 0:
                        pct_bajo, pct_alto = menciona[bajo].mean() * 100, menciona[~bajo].mean() * 100
                        a, b = st.columns(2)
                        a.metric(f"% que menciona el tema ({objetivo} < {umbral:.1f})", f"{pct_bajo:.0f}%")
                        b.metric(f"% que menciona el tema ({objetivo} ≥ {umbral:.1f})", f"{pct_alto:.0f}%")
                        partes.append(
                            f"Palabras clave usadas: {', '.join(claves)}. Entre los que tienen {objetivo} < {umbral:.1f}, "
                            f"{pct_bajo:.0f}% menciona alguna; entre los que tienen {objetivo} >= {umbral:.1f}, {pct_alto:.0f}%.\n"
                            f"Promedio de {objetivo} según mencione o no el tema:\n{tabla_m.to_string(index=False)}"
                        )
                        w1, w2 = st.columns(2)
                        with w1:
                            grafico_palabras(frecuencia_palabras(df.loc[bajo, col_texto], 10), f"Palabras: {objetivo} bajo")
                        with w2:
                            grafico_palabras(frecuencia_palabras(df.loc[~bajo, col_texto], 10), f"Palabras: {objetivo} alto")
            with st.expander("Ver comentarios que mencionan una palabra clave"):
                cols_ver = ([objetivo] if objetivo else []) + [col_texto]
                st.dataframe(df.loc[menciona, cols_ver].head(30))

        # EXTENSIÓN (Integrador / Experto): agrega aquí tu propio análisis.
        # Todo lo que sumes a `contexto_extra` (contexto_extra += "texto") viaja a la IA en la pestaña 4.

        if contexto_extra:
            partes.append("Análisis adicional:\n" + contexto_extra)
        resumen_analisis = "\n\n".join(partes)[:7000]

# --------------------------------- 4 · Análisis con IA --------------------------------
with tab4:
    st.subheader("Análisis con IA")
    if df is None:
        st.info("Primero carga tus datos en la pestaña 1.")
    else:
        st.caption(f"Modelo: **{modelo}** · Creatividad: {temperatura} · Configúralo en el menú de la izquierda 👈")
        preset = st.selectbox("Elige una plantilla o escribe la tuya", list(PLANTILLAS.keys()))
        instruccion = st.text_area("Instrucción para la IA", value=PLANTILLAS[preset], height=150, key=f"prompt_{preset}")

        o1, o2 = st.columns(2)
        incluir_resumen = o1.checkbox("Incluir el resumen de la pestaña 3", value=True)
        incluir_datos = o2.checkbox(f"Incluir una muestra de los datos ({max_filas} filas)", value=True)

        partes_msg = [instruccion.strip()]
        if incluir_resumen and resumen_analisis:
            partes_msg.append("Resultados calculados en la app:\n" + resumen_analisis)
        if incluir_datos:
            partes_msg.append(f"Datos (CSV, primeras {max_filas} filas):\n" + df.head(max_filas).to_csv(index=False))
        mensaje = "\n\n".join(p for p in partes_msg if p)

        tokens = len(mensaje) // 4
        st.caption(f"Tamaño aproximado del mensaje: ~{tokens:,} tokens")
        if tokens > 6000:
            st.warning("El mensaje es grande. Si aparece un error de límite (413/429), baja las filas en el menú "
                       "izquierdo o desmarca la muestra de datos.")

        if st.button("Analizar con IA", type="primary", key="btn_ia"):
            if not api_key:
                st.error("Falta tu API Key de Groq. Pégala en el menú de la izquierda 👈")
            elif not instruccion.strip():
                st.warning("Escribe primero una instrucción para la IA.")
            else:
                try:
                    cliente = Groq(api_key=api_key)
                    with st.spinner("La IA está analizando..."):
                        respuesta = cliente.chat.completions.create(
                            model=modelo,
                            temperature=temperatura,
                            messages=[
                                {"role": "system",
                                 "content": "Eres un analista de datos educativos. Responde en español, de forma clara y concisa."},
                                {"role": "user", "content": mensaje},
                            ],
                        )
                    texto = respuesta.choices[0].message.content
                    st.session_state["respuesta_ia"] = texto or "(La IA no devolvió texto. Prueba de nuevo o cambia de modelo.)"
                    st.session_state["mensaje_enviado"] = mensaje
                except Exception as e:
                    st.error(f"No se pudo obtener respuesta de la IA: {e}")
                    st.info(
                        "Si el error menciona límite (429), espera 30 segundos y reintenta. "
                        "Si menciona tamaño (413), baja las filas en el menú izquierdo. "
                        "Si dice que el modelo no existe, cambia el modelo en el menú izquierdo."
                    )

        if st.session_state.get("respuesta_ia"):
            st.markdown("### Respuesta de la IA")
            st.markdown(st.session_state["respuesta_ia"])
            st.download_button("Descargar respuesta (.md)", st.session_state["respuesta_ia"],
                               file_name="respuesta_ia.md", key="descarga_ia")
            with st.expander("Ver el mensaje completo que se envió a la IA"):
                st.text(st.session_state.get("mensaje_enviado", ""))
