import os

import pandas as pd
import plotly.express as px
import streamlit as st

# ----------------------------------------------------------------------
# Configuración general de la página
# ----------------------------------------------------------------------
st.set_page_config(
    page_title="Dashboard de Producción - Campo Rubiales",
    page_icon="🛢️",
    layout="wide",
)

DATA_PATH = os.path.join("data", "datos.csv")
LOGO_PATH = os.path.join("assets", "logo_ecopetrol.png")

# ----------------------------------------------------------------------
# Paleta corporativa Ecopetrol (verde oscuro, verde lima, amarillo/dorado)
# ----------------------------------------------------------------------
VERDE_OSCURO = "#00543C"
VERDE_LIMA = "#8DC63F"
AMARILLO = "#FFC72C"
VERDE_PROFUNDO = "#004B36"
OLIVA = "#B5D334"

ECOPETROL_SEQ = [VERDE_OSCURO, VERDE_LIMA, AMARILLO, VERDE_PROFUNDO, OLIVA]
ECOPETROL_SCALE = [[0.0, AMARILLO], [0.5, VERDE_LIMA], [1.0, VERDE_OSCURO]]

ZONA_COLORS = {
    "Norte": VERDE_OSCURO, "Sur": VERDE_LIMA, "Centro": AMARILLO,
    "Oriente": VERDE_PROFUNDO, "Occidente": OLIVA,
}
ESTADO_COLORS = {"Activo": VERDE_LIMA, "En Mantenimiento": AMARILLO, "Cerrado": VERDE_OSCURO}
METODO_COLORS = {
    "Bombeo Mecanico": VERDE_OSCURO, "BES": VERDE_LIMA,
    "Flujo Natural": AMARILLO, "Gas Lift": OLIVA,
}


# ----------------------------------------------------------------------
# Carga de datos (con manejo de excepciones)
# ----------------------------------------------------------------------
@st.cache_data
def cargar_datos(path: str) -> pd.DataFrame:
    datos = pd.read_csv(path, parse_dates=["fecha_inicio_operacion", "fecha_ultimo_reporte"])
    datos["anio_inicio"] = datos["fecha_inicio_operacion"].dt.year
    return datos


try:
    df = cargar_datos(DATA_PATH)
except FileNotFoundError:
    st.error(
        f"⚠️ No se encontró el archivo de datos en `{DATA_PATH}`. "
        "Verifica que `datos.csv` exista dentro de la carpeta `data/` del proyecto."
    )
    st.stop()
except Exception as e:
    st.error(f"⚠️ Ocurrió un error inesperado al cargar los datos: {e}")
    st.stop()


# ----------------------------------------------------------------------
# Encabezado (con logo)
# ----------------------------------------------------------------------
col_logo, col_title = st.columns([1, 5])
with col_logo:
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, width=170)
with col_title:
    st.title("🛢️🦎 Producción de Crudo — Campo Rubiales")
    st.markdown(
        "##### Explora en tiempo real la producción, disponibilidad y patrones geológicos "
        "de los pozos del campo 🌎📊"
    )

st.markdown("---")


# ----------------------------------------------------------------------
# Barra lateral: filtros
# ----------------------------------------------------------------------
st.sidebar.header("🔎 Filtros")

metodo = sorted(df["metodo_extraccion"].dropna().unique())
metodo_sel = st.sidebar.multiselect("Método de extracción", metodo, default=metodo)

zonas = sorted(df["zona_operativa"].dropna().unique())
zonas_sel = st.sidebar.multiselect("Zona operativa", zonas, default=zonas)

estados = sorted(df["estado_operativo"].dropna().unique())
estados_sel = st.sidebar.multiselect("Estado operativo", estados, default=estados)

opciones_mant = sorted(df["requiere_mantenimiento"].unique().tolist())
mant_sel = st.sidebar.multiselect("¿Requiere mantenimiento?", opciones_mant, default=opciones_mant)

corte_min, corte_max = float(df["corte_agua_pct"].min()), float(df["corte_agua_pct"].max())
corte_rango = st.sidebar.slider("Corte de agua (%)", corte_min, corte_max, (corte_min, corte_max))

api_min, api_max = float(df["api_gravedad"].min()), float(df["api_gravedad"].max())
api_rango = st.sidebar.slider("Gravedad API", api_min, api_max, (api_min, api_max))

# --- Filtros nuevos ---
prod_min, prod_max = float(df["produccion_bpd"].min()), float(df["produccion_bpd"].max())
prod_rango = st.sidebar.slider("Producción diaria (BPD)", prod_min, prod_max, (prod_min, prod_max))

anio_min, anio_max = int(df["anio_inicio"].min()), int(df["anio_inicio"].max())
anio_rango = st.sidebar.slider("Año de inicio de operación", anio_min, anio_max, (anio_min, anio_max))

# ----------------------------------------------------------------------
# Aplicar filtros
# ----------------------------------------------------------------------
df_filtrado = df[
    df["zona_operativa"].isin(zonas_sel)
    & df["estado_operativo"].isin(estados_sel)
    & df["requiere_mantenimiento"].isin(mant_sel)
    & df["metodo_extraccion"].isin(metodo_sel)
    & df["corte_agua_pct"].between(corte_rango[0], corte_rango[1])
    & df["api_gravedad"].between(api_rango[0], api_rango[1])
    & df["produccion_bpd"].between(prod_rango[0], prod_rango[1])
    & df["anio_inicio"].between(anio_rango[0], anio_rango[1])
]

st.markdown(f"**Pozos que cumplen los filtros:** {len(df_filtrado)} de {len(df)}")

if df_filtrado.empty:
    st.warning("No hay pozos que cumplan los filtros seleccionados.")
    st.stop()

# ----------------------------------------------------------------------
# KPIs
# ----------------------------------------------------------------------
total_pozos = len(df_filtrado)
pozos_activos = (df_filtrado["estado_operativo"] == "Activo").sum()
disponibilidad = (pozos_activos / total_pozos) * 100
produccion_total = df_filtrado["produccion_bpd"].sum()

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("Pozos filtrados", f"{total_pozos}")
kpi2.metric("Pozos activos", f"{pozos_activos}")
kpi3.metric("Disponibilidad", f"{disponibilidad:.1f} %")
kpi4.metric("Producción total (BPD)", f"{produccion_total:,.0f}")

st.markdown("---")

# ----------------------------------------------------------------------
# Vista previa del DataFrame filtrado
# ----------------------------------------------------------------------
mostrar_tabla = st.checkbox("Mostrar vista previa del conjunto de datos filtrado")
if mostrar_tabla:
    n_filas = st.slider("Filas a mostrar", min_value=5, max_value=10, value=5)
    st.dataframe(df_filtrado.head(n_filas), use_container_width=True)

st.markdown("---")

# ----------------------------------------------------------------------
# Gráfico 1: barras horizontales — producción total por zona operativa
# ----------------------------------------------------------------------
col1, col2 = st.columns(2)

with col1:
    st.subheader("📊 Producción total por zona operativa")
    prod_zona = (
        df_filtrado.groupby("zona_operativa", as_index=False)["produccion_bpd"]
        .sum()
        .sort_values("produccion_bpd", ascending=True)
    )
    fig1 = px.bar(
        prod_zona,
        x="produccion_bpd",
        y="zona_operativa",
        orientation="h",
        color="zona_operativa",
        color_discrete_map=ZONA_COLORS,
        text_auto=".0f",
        labels={"produccion_bpd": "Producción total (BPD)", "zona_operativa": "Zona"},
    )
    fig1.update_layout(showlegend=False, plot_bgcolor="white", margin=dict(t=10, b=10))
    st.plotly_chart(fig1, use_container_width=True)

# ----------------------------------------------------------------------
# Gráfico 2: donut — distribución de pozos por estado operativo
# ----------------------------------------------------------------------
with col2:
    st.subheader("🥯 Distribución de pozos por estado operativo")
    conteo_estado = df_filtrado["estado_operativo"].value_counts().reset_index()
    conteo_estado.columns = ["estado_operativo", "cantidad"]
    fig2 = px.pie(
        conteo_estado,
        names="estado_operativo",
        values="cantidad",
        hole=0.45,
        color="estado_operativo",
        color_discrete_map=ESTADO_COLORS,
    )
    fig2.update_traces(textinfo="percent+label")
    fig2.update_layout(margin=dict(t=10, b=10))
    st.plotly_chart(fig2, use_container_width=True)

st.markdown("---")

# ----------------------------------------------------------------------
# Gráfico 3: histograma — distribución de corte de agua por zona
# ----------------------------------------------------------------------
st.subheader("📈 Distribución del corte de agua (%) por zona operativa")
fig3 = px.histogram(
    df_filtrado,
    x="corte_agua_pct",
    color="zona_operativa",
    color_discrete_map=ZONA_COLORS,
    marginal="box",
    nbins=25,
    opacity=0.85,
    labels={"corte_agua_pct": "Corte de agua (%)", "zona_operativa": "Zona"},
)
fig3.update_layout(barmode="overlay", plot_bgcolor="white", margin=dict(t=10, b=10))
st.plotly_chart(fig3, use_container_width=True)

st.markdown("---")

# ----------------------------------------------------------------------
# Gráfico 4 (bonus): correlación — gravedad API vs. corte de agua
# ----------------------------------------------------------------------
st.subheader("🧪 Correlación: gravedad API vs. corte de agua (tamaño = producción BPD)")
fig4 = px.scatter(
    df_filtrado,
    x="api_gravedad",
    y="corte_agua_pct",
    color="metodo_extraccion",
    size="produccion_bpd",
    size_max=28,
    color_discrete_map=METODO_COLORS,
    hover_data=["id_pozo", "zona_operativa", "estado_operativo", "produccion_bpd"],
    labels={
        "api_gravedad": "Gravedad API",
        "corte_agua_pct": "Corte de agua (%)",
        "metodo_extraccion": "Método de extracción",
    },
)
fig4.update_layout(plot_bgcolor="white", margin=dict(t=10, b=10))
st.plotly_chart(fig4, use_container_width=True)

correlacion = df_filtrado["api_gravedad"].corr(df_filtrado["corte_agua_pct"])
st.caption(f"Coeficiente de correlación de Pearson: **{correlacion:.2f}**")

st.markdown("---")
st.caption("Dashboard de práctica con datos sintéticos — Sprint 7 de TripleTen. Por: Sebastián Martínez")