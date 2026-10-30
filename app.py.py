import io
import pandas as pd
import streamlit as st

# Configuración de la página
st.set_page_config(
    page_title="Dashboard de Ventas y Despachos",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Automatizador y Dashboard de Ventas y Despachos")
st.markdown(
    "Sube tu archivo Excel (`.xlsx`, `.xlsm`) o CSV para procesarlo,"
    " limpiarlo y exportarlo automáticamente."
)

# 1. Componente para cargar el archivo
uploaded_file = st.file_uploader(
    "Arrastra o selecciona tu archivo de datos", type=["xlsx", "xlsm", "csv"]
)

if uploaded_file is not None:
  try:
    # Lectura del archivo según su formato
    if uploaded_file.name.endswith(".csv"):
      df = pd.read_csv(uploaded_file)
    else:
      xl = pd.ExcelFile(uploaded_file)
      selected_sheet = st.selectbox(
          "Selecciona la hoja a procesar:", xl.sheet_names
      )
      df = pd.read_excel(uploaded_file, sheet_name=selected_sheet)

    st.success(
        f"¡Archivo cargado correctamente! Se encontraron {len(df)} filas y"
        f" {len(df.columns)} columnas."
    )

    # Vista previa de los datos
    with st.expander("🔍 Ver vista previa de los datos originales"):
      st.dataframe(df.head(10))

    # 2. Opciones de Limpieza y Transformación
    st.subheader("⚙️ Opciones de Procesamiento")
    col1, col2 = st.columns(2)

    with col1:
      remover_duplicados = st.checkbox(
          "Eliminar filas duplicadas", value=True
      )
    with col2:
      llenar_nulos = st.checkbox(
          "Rellenar campos vacíos (0 en números / N/A en texto)", value=False
      )

    df_procesado = df.copy()

    if remover_duplicados:
      df_procesado = df_procesado.drop_duplicates()

    if llenar_nulos:
      for col in df_procesado.select_dtypes(include=["number"]).columns:
        df_procesado[col] = df_procesado[col].fillna(0)
      for col in df_procesado.select_dtypes(include=["object"]).columns:
        df_procesado[col] = df_procesado[col].fillna("N/A")

    # 3. Métricas y Resumen Rápido
    st.subheader("📈 Resumen Ejecutivo")
    numeric_cols = df_procesado.select_dtypes(
        include=["number"]
    ).columns.tolist()

    if numeric_cols:
      col_metrica = st.selectbox(
          "Selecciona columna numérica para calcular totales:", numeric_cols
      )
      total_suma = df_procesado[col_metrica].sum()
      promedio = df_procesado[col_metrica].mean()

      m1, m2, m3 = st.columns(3)
      m1.metric("Total Registros", f"{len(df_procesado):,}")
      m2.metric(f"Suma Total de {col_metrica}", f"{total_suma:,.2f}")
      m3.metric(f"Promedio de {col_metrica}", f"{promedio:,.2f}")
    else:
      st.info(
          "No se detectaron columnas numéricas para calcular métricas"
          " automáticas."
      )

    # 4. Botón de Descarga del Archivo Limpio
    st.subheader("📥 Descargar Reporte Automatizado")


    def convertir_a_excel(df):
      output = io.BytesIO()
      with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Datos_Procesados")
      return output.getvalue()


    excel_data = convertir_a_excel(df_procesado)

    st.download_button(
        label="📥 Descargar Excel Limpio y Consolidado",
        data=excel_data,
        file_name="reporte_ventas_despacho_limpio.xlsx",
        mime=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
    )

  except Exception as e:
    st.error(f"Ocurrió un error al procesar el archivo: {e}")