import io
import pandas as pd
import streamlit as st

# Configuración de la página
st.set_page_config(
    page_title="Dashboard de Ventas y Despachos",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Panel Interactivo de Ventas y Despachos")
st.markdown(
    "Sube tu archivo Excel (`.xlsm`, `.xlsx`) para visualizar métricas,"
    " gráficos y limpiar los datos automáticamente."
)

# 1. Componente para cargar el archivo
uploaded_file = st.file_uploader(
    "Selecciona o arrastra tu archivo de datos", type=["xlsx", "xlsm", "csv"]
)

if uploaded_file is not None:
  try:
    # Lectura del archivo según su formato
    if uploaded_file.name.endswith(".csv"):
      df_raw = pd.read_csv(uploaded_file)
      sheet_names = [None]
    else:
      xl = pd.ExcelFile(uploaded_file)
      sheet_names = xl.sheet_names

    selected_sheet = st.selectbox(
        "Selecciona la hoja de trabajo:", sheet_names
    )

    # Selector de la fila de encabezados por si la tabla empieza más abajo
    header_row = st.number_input(
        "Fila donde están los encabezados (0 es la primera fila):",
        min_value=0,
        max_value=10,
        value=0,
        step=1,
    )

    if uploaded_file.name.endswith(".csv"):
      df = pd.read_csv(uploaded_file, header=header_row)
    else:
      df = pd.read_excel(
          uploaded_file, sheet_name=selected_sheet, header=header_row
      )

    # Eliminar columnas que no tengan nombre o sean totalmente nulas
    df = df.loc[:, ~df.columns.str.contains("^Unnamed")]
    df = df.dropna(how="all")

    st.success(
        f"¡Archivo cargado con éxito! Se procesaron {len(df):,} registros y"
        f" {len(df.columns)} columnas válidas."
    )

    df_procesado = df.copy()

    # 2. Resumen Ejecutivo (Métricas Principales)
    st.subheader("📈 Resumen Ejecutivo")
    numeric_cols = df_procesado.select_dtypes(
        include=["number"]
    ).columns.tolist()

    if numeric_cols:
      col_metrica = st.selectbox(
          "Métrica principal a analizar (Columna numérica):", numeric_cols
      )
      # Limpiar valores nulos de la métrica seleccionada
      df_procesado[col_metrica] = pd.to_numeric(
          df_procesado[col_metrica], errors="coerce"
      )

      total_suma = df_procesado[col_metrica].sum()
      promedio = df_procesado[col_metrica].mean()

      m1, m2, m3 = st.columns(3)
      m1.metric("Total de Registros", f"{len(df_procesado):,}")
      m2.metric(f"Suma Total de {col_metrica}", f"{total_suma:,.2f}")
      m3.metric(f"Promedio de {col_metrica}", f"{promedio:,.2f}")

      # 3. Visualización Gráfica Interactiva
      st.subheader("📊 Análisis Gráfico")
      categorical_cols = df_procesado.select_dtypes(
          include=["object", "category", "bool"]
      ).columns.tolist()

      if categorical_cols:
        col_cat = st.selectbox(
            "Agrupar gráfico por categoría:", categorical_cols
        )
        try:
          # Agrupar y asegurar datos limpios para el gráfico
          df_grouped = (
              df_procesado.groupby(col_cat)[col_metrica]
              .sum()
              .reset_index()
              .dropna()
          )
          if not df_grouped.empty:
            st.bar_chart(df_grouped.set_index(col_cat))
          else:
            st.info("No hay suficientes datos agrupados para mostrar el gráfico.")
        except Exception as chart_err:
          st.warning(
              f"No se pudo generar el gráfico con esta categoría: {chart_err}"
          )
      else:
        st.line_chart(df_procesado[col_metrica])
    else:
      st.info(
          "No se detectaron columnas numéricas válidas para generar métricas."
      )

    # 4. Vista previa de la tabla de datos
    with st.expander("🔍 Ver tabla de datos procesados"):
      st.dataframe(df_procesado, use_container_width=True)

    # 5. Botón de Descarga del Archivo Limpio
    st.subheader("📥 Exportar Reporte")


    def convertir_a_excel(df_to_save):
      output = io.BytesIO()
      with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_to_save.to_excel(writer, index=False, sheet_name="Consolidado_Limpio")
      return output.getvalue()


    excel_data = convertir_a_excel(df_procesado)

    st.download_button(
        label="📥 Descargar Excel Limpio",
        data=excel_data,
        file_name="reporte_visual_limpio.xlsx",
        mime=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
    )

  except Exception as e:
    st.error(f"Ocurrió un error al procesar el archivo: {e}")
