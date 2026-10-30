from __future__ import annotations

from datetime import timedelta
from html import escape

import altair as alt
import pandas as pd
import streamlit as st

from services.commercial_dashboard_service import prepare_commercial_base


CHANNELS = {
    "30": "Ecommerce B2C",
    "31": "NOLK",
    "32": "Ecommerce",
    "34": "Mercado Libre",
    "35": "Paris",
}


def _money(value) -> str:
    parsed = pd.to_numeric(value, errors="coerce")
    number = 0.0 if pd.isna(parsed) else float(parsed)
    return "$" + f"{number:,.0f}".replace(",", ".")


def _safe_text(value, default="—") -> str:
    text = str(value or "").strip()
    return text if text else default


def _first_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    normalized = {
        str(column).strip().lower(): column
        for column in df.columns
    }
    for candidate in candidates:
        if candidate.lower() in normalized:
            return normalized[candidate.lower()]
    return None


def _styles() -> None:
    st.markdown(
        """
        <style>
        .mkt-head{display:flex;justify-content:space-between;align-items:flex-start;gap:18px;padding:4px 2px 18px;border-bottom:1px solid #24343f;margin-bottom:18px}
        .mkt-kicker{font-size:.68rem;font-weight:900;letter-spacing:.11em;color:#ffc400;text-transform:uppercase;margin-bottom:7px}
        .mkt-title{font-size:2.05rem;font-weight:900;line-height:1.05;letter-spacing:-.035em;color:#fff;margin:0}
        .mkt-sub{font-size:.86rem;color:#9fb0bc;margin-top:8px}
        .mkt-pill{display:inline-flex;align-items:center;gap:8px;border:1px solid #275747;background:#09291f;color:#c9f7e5;border-radius:999px;padding:8px 12px;font-size:.75rem;font-weight:800;white-space:nowrap}
        .mkt-pill i{width:8px;height:8px;border-radius:50%;background:#27d78b;box-shadow:0 0 0 4px rgba(39,215,139,.12)}
        .mkt-card{height:126px;border:1px solid #2b3d49;border-radius:13px;background:linear-gradient(145deg,#111b23,#0b131a);padding:15px 16px;box-sizing:border-box}
        .mkt-card-label{font-size:.66rem;color:#8da2b1;font-weight:850;text-transform:uppercase;letter-spacing:.06em}
        .mkt-card-value{font-size:1.55rem;color:#fff;font-weight:900;line-height:1.2;margin-top:13px}
        .mkt-card-foot{font-size:.69rem;color:#79909f;margin-top:7px}
        .mkt-card.yellow{border-bottom:3px solid #ffc400}.mkt-card.green{border-bottom:3px solid #20c77a}.mkt-card.blue{border-bottom:3px solid #3c91e6}.mkt-card.purple{border-bottom:3px solid #8d5cff}.mkt-card.gray{border-bottom:3px solid #8796a0}
        .mkt-section{margin:19px 0 10px}.mkt-section strong{display:block;color:#fff;font-size:1rem}.mkt-section span{color:#8196a5;font-size:.73rem}
        .mkt-status{border:1px solid #574a14;background:#211d08;border-radius:12px;padding:14px 16px;color:#e8edf0;font-size:.82rem;line-height:1.55}
        .mkt-status strong{color:#ffc400}.mkt-source{border:1px solid #2c3e49;border-radius:11px;background:#0c151c;padding:12px 14px;color:#9dafbb;font-size:.73rem}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _prepare_sales(sales_df: pd.DataFrame | None) -> pd.DataFrame:
    base = prepare_commercial_base(sales_df)
    if base.empty:
        return base

    work = base[base["_VendedorCodigo"].isin(CHANNELS)].copy()
    work["Canal marketing"] = work["_VendedorCodigo"].map(CHANNELS)
    work["Venta neta"] = pd.to_numeric(
        work.get("VentaFirmadaConIVA", 0), errors="coerce"
    ).fillna(0)
    work["Unidades"] = pd.to_numeric(
        work.get("CantidadFirmada", 0), errors="coerce"
    ).fillna(0)
    work["SKU"] = (
        work.get("SKU", "")
        .fillna("")
        .astype(str)
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
    )
    return work


def _product_performance(
    sales: pd.DataFrame,
    stock: pd.DataFrame | None,
    period_days: int,
) -> pd.DataFrame:
    description_col = _first_column(
        sales,
        ["Descripción", "Descripcion", "Producto", "Nombre Producto", "Artículo"],
    )
    document_col = "Numero" if "Numero" in sales.columns else None

    aggregations = {
        "Ventas": ("Venta neta", "sum"),
        "Unidades vendidas": ("Unidades", "sum"),
    }
    if document_col:
        aggregations["Documentos"] = (document_col, "nunique")

    products = sales.groupby("SKU", as_index=False).agg(**aggregations)
    products = products[products["SKU"].ne("")].copy()

    if description_col:
        descriptions = (
            sales[["SKU", description_col]]
            .dropna()
            .assign(**{description_col: lambda x: x[description_col].astype(str).str.strip()})
        )
        descriptions = descriptions[descriptions[description_col].ne("")]
        descriptions = descriptions.drop_duplicates("SKU")
        products = products.merge(descriptions, on="SKU", how="left")
        products.rename(columns={description_col: "Producto"}, inplace=True)
    else:
        products["Producto"] = products["SKU"]

    stock_view = pd.DataFrame(columns=["SKU", "Stock disponible"])
    if stock is not None and not stock.empty and {"Código", "Disponible"}.issubset(stock.columns):
        stock_view = stock[["Código", "Disponible"]].copy()
        stock_view.rename(
            columns={"Código": "SKU", "Disponible": "Stock disponible"},
            inplace=True,
        )
        stock_view["SKU"] = (
            stock_view["SKU"].fillna("").astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
        )
        stock_view["Stock disponible"] = pd.to_numeric(
            stock_view["Stock disponible"], errors="coerce"
        ).fillna(0)
        stock_view = stock_view.groupby("SKU", as_index=False)["Stock disponible"].sum()

    products = products.merge(stock_view, on="SKU", how="left")
    products["Stock disponible"] = products["Stock disponible"].fillna(0)
    products["Venta diaria"] = products["Unidades vendidas"].clip(lower=0) / max(period_days, 1)
    products["Cobertura días"] = products.apply(
        lambda row: (
            row["Stock disponible"] / row["Venta diaria"]
            if row["Venta diaria"] > 0
            else None
        ),
        axis=1,
    )

    def recommendation(row) -> str:
        stock_qty = float(row["Stock disponible"])
        cover = row["Cobertura días"]
        if stock_qty <= 0:
            return "Pausar promoción"
        if cover is not None and cover <= 15:
            return "Stock crítico"
        if cover is not None and cover >= 90:
            return "Oportunidad de campaña"
        return "Mantener / observar"

    products["Recomendación"] = products.apply(recommendation, axis=1)
    products["Cobertura días"] = products["Cobertura días"].map(
        lambda value: round(float(value), 1) if pd.notna(value) else None
    )
    products["Ventas"] = products["Ventas"].round(0)
    products["Unidades vendidas"] = products["Unidades vendidas"].round(0)
    products["Stock disponible"] = products["Stock disponible"].round(0)
    return products.sort_values("Ventas", ascending=False)


def render(ctx: dict) -> None:
    _styles()
    sales_meta = ctx.get("sales_meta") or {}
    stock_meta = ctx.get("stock_meta") or {}
    sales = _prepare_sales(ctx.get("sales_df"))
    stock = ctx.get("stock_consolidated")

    st.markdown(
        """
        <div class="mkt-head">
          <div>
            <div class="mkt-kicker">MARITEX · ANÁLISIS</div>
            <h1 class="mkt-title">Marketing Comercial</h1>
            <div class="mkt-sub">Ventas por canal, rendimiento de productos y oportunidades según stock disponible.</div>
          </div>
          <div class="mkt-pill"><i></i>ERP Ventas + Stock WMS</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if sales.empty:
        st.warning(
            "No existen ventas asociadas a los canales e-commerce configurados "
            "(B2C, NOLK, Ecommerce, Mercado Libre y Paris)."
        )
        return

    minimum = sales["Fecha_dt"].min().date()
    maximum = sales["Fecha_dt"].max().date()
    default_start = max(minimum, maximum - timedelta(days=29))

    f1, f2 = st.columns([1.2, 2], gap="medium")
    with f1:
        period = st.date_input(
            "Período",
            value=(default_start, maximum),
            min_value=minimum,
            max_value=maximum,
            key="marketing_period",
        )
    with f2:
        channel_options = sorted(sales["Canal marketing"].dropna().unique().tolist())
        selected_channels = st.multiselect(
            "Canales",
            options=channel_options,
            default=channel_options,
            key="marketing_channels",
        )

    start_date, end_date = (period if isinstance(period, (tuple, list)) and len(period) == 2 else (default_start, maximum))
    filtered = sales[
        sales["Fecha_dt"].dt.date.between(start_date, end_date)
        & sales["Canal marketing"].isin(selected_channels)
    ].copy()

    if filtered.empty:
        st.info("No existen ventas para los filtros seleccionados.")
        return

    net_sales = float(filtered["Venta neta"].sum())
    documents = int(filtered["Numero"].nunique()) if "Numero" in filtered.columns else len(filtered)
    units = float(filtered["Unidades"].sum())
    active_skus = int(filtered.loc[filtered["SKU"].ne(""), "SKU"].nunique())
    ticket = net_sales / documents if documents else 0

    cards = [
        ("Ventas e-commerce", _money(net_sales), "Facturas + boletas - NC", "yellow"),
        ("Pedidos / documentos", f"{documents:,}".replace(",", "."), "Documentos comerciales únicos", "blue"),
        ("Unidades vendidas", f"{units:,.0f}".replace(",", "."), "Cantidad neta del período", "green"),
        ("SKU vendidos", f"{active_skus:,}".replace(",", "."), "Productos con movimiento", "purple"),
        ("Ticket promedio", _money(ticket), "Venta e-commerce por documento", "gray"),
    ]
    columns = st.columns(5, gap="small")
    for column, (label, value, foot, color) in zip(columns, cards):
        with column:
            st.markdown(
                f'<div class="mkt-card {color}"><div class="mkt-card-label">{escape(label)}</div>'
                f'<div class="mkt-card-value">{escape(value)}</div><div class="mkt-card-foot">{escape(foot)}</div></div>',
                unsafe_allow_html=True,
            )

    overview_tab, products_tab, attribution_tab = st.tabs(
        ["Resumen", "Productos y stock", "Atribución y campañas"]
    )

    with overview_tab:
        st.markdown(
            '<div class="mkt-section"><strong>Rendimiento comercial</strong><span>Evolución y participación por canal e-commerce.</span></div>',
            unsafe_allow_html=True,
        )
        daily = filtered.assign(Fecha=filtered["Fecha_dt"].dt.date).groupby("Fecha", as_index=False)["Venta neta"].sum()
        by_channel = filtered.groupby("Canal marketing", as_index=False).agg(
            Ventas=("Venta neta", "sum"),
            Unidades=("Unidades", "sum"),
        )
        left, right = st.columns([1.65, 1], gap="medium")
        with left:
            daily_chart = (
                alt.Chart(daily)
                .mark_area(line={"color": "#ffc400", "strokeWidth": 2}, color="#ffc400", opacity=0.16)
                .encode(
                    x=alt.X("Fecha:T", title=None),
                    y=alt.Y("Venta neta:Q", title="Venta ($)"),
                    tooltip=[alt.Tooltip("Fecha:T", title="Fecha"), alt.Tooltip("Venta neta:Q", title="Venta", format=",.0f")],
                )
                .properties(height=310)
            )
            st.altair_chart(daily_chart, use_container_width=True)
        with right:
            channel_chart = (
                alt.Chart(by_channel.sort_values("Ventas", ascending=False))
                .mark_bar(color="#ffc400", cornerRadiusEnd=4)
                .encode(
                    y=alt.Y("Canal marketing:N", sort="-x", title=None),
                    x=alt.X("Ventas:Q", title="Venta ($)"),
                    tooltip=["Canal marketing", alt.Tooltip("Ventas:Q", format=",.0f"), alt.Tooltip("Unidades:Q", format=",.0f")],
                )
                .properties(height=310)
            )
            st.altair_chart(channel_chart, use_container_width=True)

        channel_table = by_channel.sort_values("Ventas", ascending=False).copy()
        channel_table["Participación"] = (
            channel_table["Ventas"] / max(net_sales, 1) * 100
        )
        st.dataframe(
            channel_table,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Ventas": st.column_config.NumberColumn(format="$ %.0f"),
                "Unidades": st.column_config.NumberColumn(format="%.0f"),
                "Participación": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f%%"),
            },
        )

    with products_tab:
        period_days = max((end_date - start_date).days + 1, 1)
        products = _product_performance(filtered, stock, period_days)
        st.markdown(
            '<div class="mkt-section"><strong>Decisiones de producto</strong><span>Cruce de ventas del período con stock actual disponible.</span></div>',
            unsafe_allow_html=True,
        )
        recommendation_options = products["Recomendación"].dropna().unique().tolist()
        recommendation_filter = st.multiselect(
            "Recomendación",
            options=recommendation_options,
            default=recommendation_options,
            key="marketing_recommendation",
        )
        product_view = products[products["Recomendación"].isin(recommendation_filter)].copy()
        st.dataframe(
            product_view[[
                "SKU", "Producto", "Ventas", "Unidades vendidas", "Stock disponible",
                "Cobertura días", "Recomendación",
            ]],
            hide_index=True,
            use_container_width=True,
            height=470,
            column_config={
                "Ventas": st.column_config.NumberColumn(format="$ %.0f"),
                "Unidades vendidas": st.column_config.NumberColumn(format="%.0f"),
                "Stock disponible": st.column_config.NumberColumn(format="%.0f"),
                "Cobertura días": st.column_config.NumberColumn(format="%.1f"),
            },
        )

    with attribution_tab:
        st.markdown(
            '<div class="mkt-section"><strong>Atribución de campañas</strong><span>Estado de conexiones necesarias para calcular inversión, conversiones y ROAS.</span></div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            <div class="mkt-status">
              <strong>Primera etapa activa:</strong> ventas ERP por canal y cruce con stock.<br>
              <strong>Siguiente conexión:</strong> VTEX marketingData/UTM para asociar pedidos a campañas.<br>
              <strong>Después:</strong> Google Ads y Meta Ads para inversión, CPC, CPA y ROAS real.
            </div>
            """,
            unsafe_allow_html=True,
        )
        status = pd.DataFrame(
            [
                {"Fuente": "ERP Ventas", "Estado": "Conectada", "Aporta": "Venta, unidades, documentos y canal"},
                {"Fuente": "Stock WMS / Supabase", "Estado": "Conectada", "Aporta": "Disponibilidad y cobertura por SKU"},
                {"Fuente": "VTEX marketingData", "Estado": "Pendiente", "Aporta": "UTM, campaña, cupón y pedido"},
                {"Fuente": "Google Ads", "Estado": "Pendiente", "Aporta": "Inversión, clics, conversiones y ROAS"},
                {"Fuente": "Meta Ads", "Estado": "Pendiente", "Aporta": "Campañas Facebook e Instagram"},
            ]
        )
        st.dataframe(status, hide_index=True, use_container_width=True)

    st.markdown(
        f'<div class="mkt-source">Ventas: {escape(_safe_text(sales_meta.get("filename"), "ERP Ventas"))} · '
        f'Stock: {escape(_safe_text(stock_meta.get("source") or stock_meta.get("filename"), "WMS / Supabase"))}</div>',
        unsafe_allow_html=True,
    )
