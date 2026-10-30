import io
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="Control de Ventas y Despachos - Grupo Maritex",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Estilos CSS modernos tipo tarjeta ejecutiva
st.markdown(
    """
    <style>
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        padding: 16px;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
    }
    div[data-testid="stMetricLabel"] { color: #94a3b8 !important; font-weight: 600 !important; font-size: 0.85rem !important; }
    div[data-testid="stMetricValue"] { color: #38bdf8 !important; font-weight: 700 !important; font-size: 1.6rem !important; }
    </style>
""",
    unsafe_allow_html=True,
)

st.title("📦 Panel de Control: Ventas y Despachos")
st.caption(
    "Sistema de visualización ejecutiva y actualización acumulativa de"
    " planillas."
)

# Inicializar la base de datos acumulativa en la sesión
if "pedidos_db" not in st.session_state:
  st.session_state.pedidos_db = pd.DataFrame()

# Panel lateral para carga y actualización de archivos
with st.sidebar:
  st.header("⚙️ Gestión de Planillas")
  uploaded_file = st.file_uploader(
      "Cargar reporte (.xlsx, .xlsm, .csv):", type=["xlsx", "xlsm", "csv"]
  )

  if uploaded_file is not None:
    try:
      if uploaded_file.name.endswith(".csv"):
        df_nuevo = pd.read_csv(uploaded_file)
      else:
        xl = pd.ExcelFile(uploaded_file)
        sheet_selected = st.selectbox("Seleccionar hoja:", xl.sheet_names)
        df_nuevo = pd.read_excel(uploaded_file, sheet_name=sheet_selected)

      # Limpieza de columnas vacías o fantasmas
      df_nuevo = df_nuevo.loc[:, ~df_nuevo.columns.str.contains("^Unnamed")]
      df_nuevo = df_nuevo.dropna(how="all")

      if st.button(
          "🔄 Sincronizar y Actualizar Pedidos", use_container_width=True
      ):
        if st.session_state.pedidos_db.empty:
          st.session_state.pedidos_db = df_nuevo
        else:
          # Buscar columna identificadora de pedido
          id_col = None
          for col in df_nuevo.columns:
            if "pedido" in col.lower() or "nº" in col.lower():
              id_col = col
              break

          if id_col and id_col in st.session_state.pedidos_db.columns:
            # Actualizar registros existentes y agregar nuevos (Upsert)
            base_actual = st.session_state.pedidos_db.set_index(id_col)
            nuevo_ingreso = df_nuevo.set_index(id_col)
            base_actual.update(nuevo_ingreso)
            # Combinar agregando los que no existían
            df_combinado = pd.concat(
                [base_actual, nuevo_ingreso[~nuevo_ingreso.index.isin(base_actual.index)]]
            ).reset_index()
            st.session_state.pedidos_db = df_combinado
          else:
            # Si no hay ID claro, simplemente concatener y quitar duplicados exactos
            st.session_state.pedidos_db = pd.concat(
                [st.session_state.pedidos_db, df_nuevo], ignore_index=True
            ).drop_duplicates()

        st.success("¡Base de datos de pedidos actualizada con éxito!")
    except Exception as e:
      st.error(f"Error procesando el archivo: {e}")

  st.markdown("---")
  if not st.session_state.pedidos_db.empty:
    if st.button("🗑️ Vaciar Histórico Consolidado", use_container_width=True):
      st.session_state.pedidos_db = pd.DataFrame()
      st.rerun()

# Cuerpo Principal del Dashboard
df_main = st.session_state.pedidos_db

if not df_main.empty:
  # Normalizar nombres de columnas clave si existen para facilitar gráficos
  cols_lower = {c.lower(): c for c in df_main.columns}

  tab1, tab2, tab3 = st.tabs(
      [
          "📊 Dashboard Ejecutivo",
          "📋 Detalle General de Pedidos",
          "📥 Exportar Consolidado",
      ]
  )

  with tab1:
    st.subheader("📌 Indicadores Clave de Rendimiento")

    # Calcular métricas automáticas si existen las columnas típicas
    total_pedidos = len(df_main)

    # Buscar columna de venta total
    col_venta = next(
        (
            cols_lower[c]
            for c in cols_lower
            if "total" in c or "venta" in c or "monto" in c
        ),
        None,
    )
    col_estado_despacho = next(
        (cols_lower[c] for c in cols_lower if "despach" in c), None
    )
    col_comuna = next((cols_lower[c] for c in cols_lower if "comuna" in c), None)

    m1, m2, m3 = st.columns(3)
    m1.metric("Total de Pedidos", f"{total_pedidos:,}")

    if col_venta and pd.to_numeric(df_main[col_venta], errors="coerce").notnull().any():
      val_total_ventas = pd.to_numeric(df_main[col_venta], errors="coerce").sum()
      val_promedio = pd.to_numeric(df_main[col_venta], errors="coerce").mean()
      m2.metric("Venta Consolidada Total", f"${val_total_ventas:,.2f}")
      m3.metric("Ticket Promedio", f"${val_promedio:,.2f}")
    else:
      m2.metric("Estado del Sistema", "Operativo")
      m3.metric("Registros Activos", f"{total_pedidos:,}")

    st.markdown("---")
    st.subheader("📈 Análisis Visual de Despachos y Comunas")

    g1, g2 = st.columns(2)

    with g1:
      if col_comuna:
        df_comuna = (
            df_main.groupby(col_comuna)
            .size()
            .reset_index(name="Cantidad")
            .sort_values(by="Cantidad", ascending=False)
            .head(10)
        )
        fig_comuna = px.bar(
            df_comuna,
            x=col_comuna,
            y="Cantidad",
            title="Top 10 Comunas con Mayor Demanda",
            text="Cantidad",
            template="plotly_dark",
            color_discrete_sequence=["#0ea5e9"],
        )
        st.plotly_chart(fig_comuna, use_container_width=True)
      else:
        st.info("No se detectó columna de Comuna para graficar.")

    with g2:
      if col_estado_despacho:
        df_estado = (
            df_main.groupby(col_estado_despacho)
            .size()
            .reset_index(name="Cantidad")
        )
        fig_estado = px.pie(
            df_estado,
            names=col_estado_despacho,
            values="Cantidad",
            title="Estado Actual de Despachos",
            hole=0.45,
            template="plotly_dark",
            color_discrete_sequence=px.colors.qualitative.Pastel,
        )
        st.plotly_chart(fig_estado, use_container_width=True)
      else:
        st.info("No se detectó columna de Estado de Despacho.")

  with tab2:
    st.subheader("📋 Tabla Interactiva de Pedidos Acumulados")
    st.dataframe(df_main, use_container_width=True, height=500)

  with tab3:
    st.subheader("📥 Descargar Reporte Consolidado")

    def convertir_excel(df_to_export):
      output = io.BytesIO()
      with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_to_export.to_excel(
            writer, index=False, sheet_name="Pedidos_Actualizados"
        )
      return output.getvalue()

    st.download_button(
        label="📥 Descargar Excel Consolidado (.xlsx)",
        data=convertir_excel(df_main),
        file_name="reporte_pedidos_actualizado.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
else:
  st.info(
      "👈 Comienza cargando tu planilla de pedidos en el menú lateral para"
      " activar el panel visual y el sistema de actualización."
  )
