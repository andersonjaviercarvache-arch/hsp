import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# 1. Base de Datos Técnica Real
ciudades_data = {
    "Guayaquil": {"hsp": [4.12, 4.05, 4.38, 4.51, 4.32, 4.10, 4.45, 4.92, 5.15, 5.02, 4.85, 4.58], "temp": 27.5},
    "Durán": {"hsp": [4.08, 3.98, 4.35, 4.48, 4.28, 4.05, 4.40, 4.88, 5.10, 5.05, 4.90, 4.62], "temp": 27.8},
    "Quito": {"hsp": [4.85, 4.62, 4.28, 4.02, 4.15, 4.65, 5.18, 5.42, 5.35, 4.88, 4.55, 4.68], "temp": 14.5},
    "Cuenca": {"hsp": [4.45, 4.38, 4.25, 4.15, 3.85, 3.72, 3.95, 4.35, 4.62, 4.75, 4.82, 4.55], "temp": 15.0},
    "Manta": {"hsp": [4.82, 4.95, 5.15, 5.35, 5.12, 4.85, 4.98, 5.45, 5.75, 5.62, 5.48, 5.15], "temp": 26.2}
}

st.set_page_config(page_title="Dashboard Solar Pro", layout="wide")

# --- LÓGICA DE ESTADOS ---
if 'costo_kwp' not in st.session_state: st.session_state.costo_kwp = 825.0

# --- SIDEBAR ---
st.sidebar.header("⚙️ Configuración")
ciudad_sel = st.sidebar.selectbox("📍 Ciudad", list(ciudades_data.keys()))
consumo_mensual = st.sidebar.number_input("⚡ Consumo (kWh/mes)", value=300.0)
pago_planilla = st.sidebar.number_input("💵 Pago Planilla (USD)", value=30.0)
tipo_proy = st.sidebar.selectbox("🏢 Tipo", ["Residencial", "Comercial"])

# Cálculos Base
costo_kwh = pago_planilla / consumo_mensual if consumo_mensual > 0 else 0
info_c = ciudades_data[ciudad_sel]
pr = 0.82 - ((max(0, info_c["temp"] - 15)) * 0.0045)
hsp_avg = sum(info_c["hsp"]) / 12
pot_sug = consumo_mensual / (hsp_avg * pr * 30.44)

# Sincronización Inversión
def up_kwp(): st.session_state.inv_total = st.session_state.costo_kwp * pot_sug
def up_inv(): st.session_state.costo_kwp = st.session_state.inv_total / pot_sug

col_i1, col_i2 = st.sidebar.columns(2)
with col_i1: st.number_input("USD/kWp", key="costo_kwp", on_change=up_kwp)
with col_i2: 
    if 'inv_total' not in st.session_state: st.session_state.inv_total = st.session_state.costo_kwp * pot_sug
    st.number_input("Inversión", key="inv_total", on_change=up_inv)

# --- CÁLCULO DE FLUJO DE CAJA ---
años = np.arange(1, 26)
flujo_anual = []
acumulado = []
suma = 0
gen_ini = pot_sug * hsp_avg * pr * 365
ahorro_trib = (st.session_state.inv_total / 10) if tipo_proy == "Comercial" else 0

for a in años:
    # Degradación (2% año 1, 0.55% resto)
    rend = 0.98 * (0.9945**(a-1))
    ingreso = (gen_ini * rend * costo_kwh) + (ahorro_trib if a <= 10 else 0)
    suma += ingreso
    flujo_anual.append(ingreso)
    acumulado.append(suma)

# --- INTERFAZ PRINCIPAL ---
st.title("📊 Dashboard de Flujo de Caja Solar")
st.info(f"Costo calculado por kWh: **${costo_kwh:.4f}**")

# Métricas Clave
m1, m2, m3, m4 = st.columns(4)
m1.metric("Potencia Sistema", f"{pot_sug:.2f} kWp")
m2.metric("Inversión Inicial", f"${st.session_state.inv_total:,.2f}")
m3.metric("Ahorro Total (25a)", f"${suma:,.2f}")
payback = next((a for a, v in zip(años, acumulado) if v >= st.session_state.inv_total), ">25")
m4.metric("Retorno (Payback)", f"{payback} años")

st.markdown("---")

# --- GRÁFICOS INTERACTIVOS ---
col_g1, col_g2 = st.columns(2)

with col_g1:
    st.subheader("💰 Flujo de Caja Anual")
    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(x=años, y=flujo_anual, name="Ingreso Anual", marker_color='#2ecc71'))
    fig_bar.update_layout(xaxis_title="Año", yaxis_title="USD", height=400, margin=dict(l=20, r=20, t=30, b=20))
    st.plotly_chart(fig_bar, use_container_width=True)

with col_g2:
    st.subheader("📈 Recuperación Acumulada")
    fig_line = go.Figure()
    # Línea de inversión
    fig_line.add_trace(go.Scatter(x=años, y=[st.session_state.inv_total]*25, name="Inversión", line=dict(color='red', dash='dash')))
    # Línea de acumulado
    fig_line.add_trace(go.Scatter(x=años, y=acumulado, name="Flujo Acumulado", fill='tonexty', fillcolor='rgba(46, 204, 113, 0.2)', line=dict(color='#1f77b4')))
    fig_line.update_layout(xaxis_title="Año", yaxis_title="USD", height=400, margin=dict(l=20, r=20, t=30, b=20))
    st.plotly_chart(fig_line, use_container_width=True)

# Tabla de datos
with st.expander("📄 Ver Tabla de Datos Detallada"):
    df = pd.DataFrame({
        "Año": años,
        "Flujo Anual (USD)": flujo_anual,
        "Acumulado (USD)": acumulado
    })
    st.dataframe(df.style.format("${:,.2f}"), use_container_width=True)
