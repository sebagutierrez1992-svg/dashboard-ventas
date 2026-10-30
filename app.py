import io
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="Gestor de Pedidos & Despachos",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Estilos ejecutivos
st.markdown(
    """
    <style>
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        padding: 16px;
        border-radius: 12px;
    }
    div[data-testid="stMetricLabel"] { color: #94a3b8 !important; font-weight: 600 !important; }
    div[data-testid="stMetricValue"] { color: #38bdf8 !important; font-weight: 700 !important; }
    </style>
""",
    unsafe_allow_html=True,
)

st.title("📦 Sistema de Seguimiento y Carga de Pedidos")
st.caption(
    "Acumula y actualiza tu base de datos de pedidos subiendo planillas"
    " periódicas."
)

# Inicializar la base de datos en la memoria de la sesión
if "pedidos_db" not in st.session_state:
  st.session_state.pedidos_db = pd.DataFrame()

# Sidebar para carga acumulativa
with st.sidebar:
  st.header("📥 Cargar Nuevos Pedidos")
  uploaded_file = st.file_uploader(
      "Subir planilla (.xlsx, .xlsm, .csv):", type=["xlsx", "xlsm", "csv"]
  )

  if uploaded_file is not None:
    try:
      if uploaded_file.name.endswith(".csv"):
        df_nuevo = pd.read_csv(uploaded_file)
      else:
        xl = pd.ExcelFile(uploaded_file)
        sheet_selected = st.selectbox("Hoja:", xl.sheet_names)
        df_nuevo = pd.read_excel(uploaded_file, sheet_name=sheet_selected)

      df_nuevo = df_nuevo.loc[:, ~df_nuevo.columns.str.contains("^Unnamed")]
      df_nuevo = df_nuevo.dropna(how="all")
      df_nuevo.columns = [
          str(col).replace("_", " ").title().strip() for col in df_nuevo.columns
      ]

      if st.button("➕ Anexar / Actualizar a Base General", use_container_width=True):
        if st.session_state.pedidos_db.empty:
          st.session_state.pedidos_db = df_nuevo
        else:
          st.session_state.pedidos_db = pd.concat(
              [st.session_state.pedidos_db, df_nuevo], ignore_index=True
          )

        # Eliminar duplicados si existen registros idénticos
        st.session_state.pedidos_db = (
            st.session_state.pedidos_db.drop_duplicates()
        )
        st.success("¡Base de pedidos actualizada exitosamente!")
    except Exception as e:
      st.error(f"Error al leer el archivo: {e}")

  st.markdown("---")
  if not st.session_state.pedidos_db.empty:
    if st.button("🗑️ Limpiar Base Consolidada", use_container_width=True):
      st.session_state.pedidos_db = pd.DataFrame()
      st.rerun()

# Despliegue de datos y métricas
df_main = st.session_state.pedidos_db

if not df_main.empty:
  tab1, tab2, tab3 = st.tabs(
      ["📊 Vista General de Pedidos", "🔍 Detalle de Registros", "📥 Exportar Base"]
  )

  numeric_cols = df_main.select_dtypes(include=["number"]).columns.tolist()
  categorical_cols = df_main.select_dtypes(
      include=["object", "category", "bool"]
  ).columns.tolist()

  with tab1:
    st.subheader("📌 Resumen Consolidado")
    k1, k2, k3 = st.columns(3)

    k1.metric("Total Pedidos Registrados", f"{len(df_main):,}")

    if numeric_cols:
      col_m = k2.selectbox("Métrica Financiera/Cantidad:", numeric_cols)
      k2.metric(f"Monto Total {col_m}", f"${df_main[col_m].sum():,.2f}")
      k3.metric(f"Promedio por Pedido", f"${df_main[col_m].mean():,.2f}")

    st.markdown("---")
    st.subheader("📈 Distribución de Pedidos")
    c_left, c_right = st.columns(2)

    if categorical_cols:
      with c_left:
        group_col = st.selectbox(
            "Ver cantidad por estado / categoría:", categorical_cols, index=0
        )
        df_count = (
            df_main.groupby(group_col).size().reset_index(name="Cantidad")
        )

        fig_bar = px.bar(
            df_count,
            x=group_col,
            y="Cantidad",
            title=f"Pedidos por {group_col}",
            text="Cantidad",
            template="plotly_dark",
            color_discrete_sequence=["#38bdf8"],
        )
        st.plotly_chart(fig_bar, use_container_width=True)

      with c_right:
        if len(categorical_cols) > 1:
          pie_col = st.selectbox("Distribución Porcentual:", categorical_cols, index=1)
        else:
          pie_col = group_col

        df_pie = df_main.groupby(pie_col).size().reset_index(name="Cantidad")
        fig_pie = px.pie(
            df_pie,
            names=pie_col,
            values="Cantidad",
            title=f"Proporción por {pie_col}",
            hole=0.4,
            template="plotly_dark",
        )
        st.plotly_chart(fig_pie, use_container_width=True)

  with tab2:
    st.subheader("📋 Consolidado Total de Pedidos")
    st.dataframe(df_main, use_container_width=True, height=500)

  with tab3:
    st.subheader("📥 Exportar Histórico Completo")

    def descargar_excel(df_download):
      buffer = io.BytesIO()
      with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_download.to_excel(
            writer, index=False, sheet_name="Pedidos_Consolidados"
        )
      return buffer.getvalue()

    st.download_button(
        label="📥 Descargar Base Completa (.xlsx)",
        data=descargar_excel(df_main),
        file_name="historico_pedidos_actualizado.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
else:
  st.info(
      "👈 Comienza cargando tu primera planilla en el panel lateral para dar de"
      " alta los pedidos."
  )
