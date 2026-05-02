import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
import tempfile
import os

# 1. BASE DE DATOS TÉCNICA (Sustento de NASA POWER / PVGIS)
# Cada ciudad tiene su HSP específica y su temperatura media que afecta la eficiencia.
ciudades_data = {
    "Mes": ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"],
    "Guayaquil": {"hsp": [4.21, 4.15, 4.48, 4.55, 4.38, 4.15, 4.52, 4.98, 5.21, 5.08, 4.92, 4.65], "temp": 27.2, "fuente": "NASA POWER"},
    "Durán": {"hsp": [4.18, 4.10, 4.42, 4.50, 4.35, 4.12, 4.48, 4.95, 5.18, 5.05, 4.88, 4.62], "temp": 27.5, "fuente": "NASA POWER"},
    "Quito": {"hsp": [4.95, 4.75, 4.42, 4.15, 4.28, 4.75, 5.25, 5.48, 5.40, 4.98, 4.65, 4.78], "temp": 14.8, "fuente": "PVGIS / Global Solar Atlas"},
    "Cuenca": {"hsp": [4.55, 4.45, 4.32, 4.20, 3.95, 3.82, 4.05, 4.45, 4.72, 4.85, 4.92, 4.65], "temp": 15.2, "fuente": "NASA POWER"},
    "Manta": {"hsp": [4.92, 5.05, 5.25, 5.45, 5.22, 4.95, 5.08, 5.55, 5.85, 5.72, 5.58, 5.25], "temp": 25.8, "fuente": "Global Solar Atlas"}
}

st.set_page_config(page_title="Simulador Fotovoltaico Ecuador", layout="wide")

# Inicialización de estado para la inversión
if 'costo_kwp' not in st.session_state:
    st.session_state.costo_kwp = 850.0

# --- SIDEBAR ---
st.sidebar.header("📋 Parámetros de Propuesta")
nombre_cliente = st.sidebar.text_input("Cliente", "Empresa X")
tipo_proyecto = st.sidebar.selectbox("Tipo de Proyecto", ["Comercial", "Residencial"])

st.title("☀️ Sistema de Dimensionamiento Solar con Influencia Climática")
st.markdown("---")

# 2. SELECCIÓN Y CÁLCULOS CLIMÁTICOS
col_top1, col_top2, col_top3 = st.columns([1, 1, 1])

with col_top1:
    ciudad_sel = st.selectbox("📍 Seleccione Ciudad", list(ciudades_data.keys())[1:])
    consumo_kwh = st.number_input("⚡ Consumo Mensual (kWh)", value=1000.0)

# EXTRACCIÓN DE DATOS METEO
datos_clima = ciudades_data[ciudad_sel]
hsp_anual = sum(datos_clima["hsp"]) / 12  # Promedio diario anual
temp_ambiente = datos_clima["temp"]

# CÁLCULO DEL PERFORMANCE RATIO (PR) DINÁMICO
# A mayor temperatura, menor eficiencia de los módulos (Pérdidas Térmicas)
# Se asume coeficiente de potencia de -0.4%/°C y NOCT de 45°C
pérdidas_temp = max(0, (temp_ambiente + 20) - 25) * 0.004 
pr_final = 0.82 - pérdidas_temp  # 0.82 es el PR base (suciedad, cableado, inversor)

# POTENCIA NECESARIA (Dimensionamiento basado en la ciudad)
potencia_kwp = consumo_kwh / (hsp_anual * pr_final * 30.44)

with col_top2:
    st.metric("HSP Ciudad", f"{hsp_anual:.2f} h/día")
    st.metric("PR Estimado", f"{pr_final:.2%}")

with col_top3:
    pago_planilla = st.number_input("💵 Pago Mensual USD", value=120.0)
    precio_kwh = pago_planilla / consumo_kwh if consumo_kwh > 0 else 0
    st.info(f"Tarifa: ${precio_kwh:.4f} /kWh")

# 3. GENERACIÓN ENERGÉTICA INFLUENCIADA POR CLIMA
generacion_anual_y1 = potencia_kwp * hsp_anual * pr_final * 365

st.success(f"📈 Basado en el clima de **{ciudad_sel}**, su sistema de **{potencia_kwp:.2f} kWp** generará **{generacion_anual_y1:,.0f} kWh** en el primer año.")

# 4. ANÁLISIS FINANCIERO
st.markdown("### 💰 Configuración Económica")
c_inv1, c_inv2 = st.columns(2)

def update_inv(): st.session_state.inv_total = st.session_state.costo_kwp * potencia_kwp
def update_kwp(): st.session_state.costo_kwp = st.session_state.inv_total / potencia_kwp

with c_inv1:
    st.number_input("Costo por kWp (USD/kWp)", key="costo_kwp", on_change=update_inv)
with c_inv2:
    if 'inv_total' not in st.session_state: update_inv()
    st.number_input("Inversión Total (USD)", key="inv_total", on_change=update_kwp)

# Lógica de Payback
deg_anual = 0.0055 # 0.55% degradación estándar
ahorro_trib = (st.session_state.inv_total / 10) if tipo_proyecto == "Comercial" else 0
flujo_acumulado = 0
tabla_datos = []
payback_año = None

for año in range(1, 26):
    prod_año = generacion_anual_y1 * ((1 - deg_anual)**(año-1))
    ahorro_usd = prod_año * precio_kwh
    beneficio = ahorro_usd + (ahorro_trib if año <= 10 else 0)
    flujo_acumulado += beneficio
    
    if flujo_acumulado >= st.session_state.inv_total and payback_año is None:
        payback_año = año
        
    tabla_datos.append({
        "Año": año,
        "Producción (kWh)": f"{prod_año:,.0f}",
        "Ahorro USD": f"${ahorro_usd:,.2f}",
        "Acumulado": f"${flujo_acumulado:,.2f}"
    })

# 5. RESULTADOS FINALES
st.divider()
res1, res2, res3 = st.columns(3)
res1.metric("Retorno de Inversión", f"{payback_año} años" if payback_año else "+25 años")
res2.metric("Ahorro Total (25 años)", f"${flujo_acumulado:,.2f}")
res3.metric("Fuente Meteo", datos_clima["fuente"])

st.dataframe(pd.DataFrame(tabla_datos), use_container_width=True)
