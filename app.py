import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
import tempfile
import os

# 1. BASE DE DATOS TÉCNICA SUSTENTADA (NASA POWER / PVGIS)
ciudades_data = {
    "Mes": ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"],
    "Guayaquil": {"hsp": [4.21, 4.15, 4.48, 4.55, 4.38, 4.15, 4.52, 4.98, 5.21, 5.08, 4.92, 4.65], "temp": 27.2, "fuente": "NASA POWER"},
    "Durán": {"hsp": [4.18, 4.10, 4.42, 4.50, 4.35, 4.12, 4.48, 4.95, 5.18, 5.05, 4.88, 4.62], "temp": 27.5, "fuente": "NASA POWER"},
    "Quito": {"hsp": [4.95, 4.75, 4.42, 4.15, 4.28, 4.75, 5.25, 5.48, 5.40, 4.98, 4.65, 4.78], "temp": 14.8, "fuente": "PVGIS / Global Solar Atlas"},
    "Cuenca": {"hsp": [4.55, 4.45, 4.32, 4.20, 3.95, 3.82, 4.05, 4.45, 4.72, 4.85, 4.92, 4.65], "temp": 15.2, "fuente": "NASA POWER"},
    "Manta": {"hsp": [4.92, 5.05, 5.25, 5.45, 5.22, 4.95, 5.08, 5.55, 5.85, 5.72, 5.58, 5.25], "temp": 25.8, "fuente": "Global Solar Atlas"}
}

st.set_page_config(page_title="Simulador Solar Profesional", layout="wide")

# Mantener estados de inversión
if 'costo_kwp' not in st.session_state: st.session_state.costo_kwp = 850.0

# --- SIDEBAR (CONFIGURACIÓN DE CLIENTE) ---
st.sidebar.header("📋 Datos de la Propuesta")
nombre_cliente = st.sidebar.text_input("Nombre del Cliente", "Cliente Ejemplo")
nombre_proyecto = st.sidebar.text_input("Nombre del Proyecto", "Instalación Solar")
tipo_proyecto = st.sidebar.selectbox("Tipo de Proyecto", ["Comercial", "Residencial"])
vendedor = st.sidebar.text_input("Asesor Técnico", "Ing. Solar")

st.title("☀️ Análisis de Retorno Solar con Motor Meteorológico")

# --- BLOQUE 1: CONFIGURACIÓN TÉCNICA ---
with st.container():
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        ciudad_sel = st.selectbox("📍 Ciudad", [c for c in ciudades_data.keys() if c != "Mes"])
    with col2:
        consumo_mensual = st.number_input("⚡ Consumo (kWh/mes)", value=500.0)
    with col3:
        pago_planilla = st.number_input("💵 Pago Planilla (USD)", value=50.0)
        costo_kwh = pago_planilla / consumo_mensual if consumo_mensual > 0 else 0
    with col4:
        deg_año1 = st.number_input("📉 Deg. Año 1 (%)", value=2.0) / 100
    with col5:
        atenuacion_anual = st.number_input("📉 Aten. Anual (%)", value=0.55) / 100

# --- BLOQUE 2: CÁLCULOS METEOROLÓGICOS (EL CORAZÓN DEL SISTEMA) ---
datos_clima = ciudades_data[ciudad_sel]
hsp_promedio = sum(datos_clima["hsp"]) / 12
temp_promedio = datos_clima["temp"]

# Factor de Corrección (PR): 0.82 base - pérdidas por calor (0.4% por cada grado sobre 15°C ambiente)
pr_ajustado = 0.82 - (max(0, temp_promedio - 15) * 0.0045)

# Potencia sugerida para cubrir el 100% del consumo
potencia_sugerida = consumo_mensual / (hsp_promedio * pr_ajustado * 30.44)

# PRODUCCIÓN ANUAL REAL SEGÚN CLIMA
generacion_anual_y1 = potencia_sugerida * hsp_promedio * pr_ajustado * 365

with st.expander("🌍 Panel de Datos Meteorológicos y Eficiencia", expanded=True):
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("HSP Promedio", f"{hsp_promedio:.2f} h/día")
    m2.metric("Temp. Ambiente", f"{temp_promedio}°C")
    m3.metric("Factor PR", f"{pr_ajustado:.2%}")
    m4.metric("Fuente", datos_clima["fuente"])

# --- BLOQUE 3: COSTOS ---
st.subheader("💰 Inversión y Costos")
c_inv1, c_inv2 = st.columns(2)

def update_inv(): st.session_state.inv_total = st.session_state.costo_kwp * potencia_sugerida
def update_kwp(): st.session_state.costo_kwp = st.session_state.inv_total / potencia_sugerida if potencia_sugerida > 0 else 0

with c_inv1:
    st.number_input("Costo por kWp (USD)", key="costo_kwp", on_change=update_inv)
with c_inv2:
    if 'inv_total' not in st.session_state: update_inv()
    st.number_input("Inversión Total (USD)", key="inv_total", on_change=update_kwp)

# --- BLOQUE 4: TABLA DE PROYECCIÓN 25 AÑOS ---
ahorro_tributario_anual = (st.session_state.inv_total / 10) if tipo_proyecto == "Comercial" else 0.0
data_tabla = []
años, acumulados = [], []
suma_fin, año_payback = 0, None

for i in range(1, 26):
    rendimiento = (1 - deg_año1) * ((1 - atenuacion_anual)**(i-1)) if i > 1 else (1 - deg_año1)
    prod = generacion_anual_y1 * rendimiento
    ahorro_en = prod * costo_kwh
    beneficio_trib = ahorro_tributario_anual if i <= 10 else 0
    total_anual = ahorro_en + beneficio_trib
    suma_fin += total_anual
    
    años.append(i); acumulados.append(suma_fin)
    if suma_fin >= st.session_state.inv_total and año_payback is None: año_payback = i

    data_tabla.append({
        "Año": i, "Prod. kWh": f"{prod:,.0f}", "Ahorro USD": f"${ahorro_en:,.2f}",
        "Ahorro Trib.": f"${beneficio_trib:,.2f}", "Total Año": f"${total_anual:,.2f}", "Acumulado": f"${suma_fin:,.2f}"
    })

# --- RESULTADOS FINALES ---
st.divider()
r1, r2, r3, r4 = st.columns(4)
r1.metric("Potencia DC", f"{potencia_sugerida:.2f} kWp")
r2.metric("Generación Año 1", f"{generacion_anual_y1:,.0f} kWh")
r3.metric("Ahorro 25 Años", f"${suma_fin:,.2f}")
r4.metric("Retorno (Payback)", f"{año_payback} años" if año_payback else "+25 años")

st.dataframe(pd.DataFrame(data_tabla), use_container_width=True)

# --- EXPORTACIÓN PDF ---
def generar_pdf():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, f"PROPUESTA TÉCNICA: {nombre_proyecto}", 0, 1, 'C')
    
    pdf.ln(5)
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 10, "1. CONDICIONES METEOROLÓGICAS DE DISEÑO", 0, 1)
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 7, f"Ubicación: {ciudad_sel} | Fuente: {datos_clima['fuente']}", 0, 1)
    pdf.cell(0, 7, f"Horas Solar Pico (HSP): {hsp_promedio:.2f} h/día", 0, 1)
    pdf.cell(0, 7, f"Temperatura de Diseño: {temp_promedio} grados C", 0, 1)
    pdf.cell(0, 7, f"Performance Ratio (PR): {pr_ajustado:.2%}", 0, 1)

    pdf.ln(5)
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 10, "2. RESUMEN ENERGÉTICO Y FINANCIERO", 0, 1)
    pdf.set_font("Arial", "", 10)
    pdf.cell(90, 7, f"Potencia Sugerida: {potencia_sugerida:.2f} kWp"); pdf.cell(90, 7, f"Generación Estimada Año 1: {generacion_anual_y1:,.0f} kWh", 0, 1)
    pdf.cell(90, 7, f"Inversión Total: ${st.session_state.inv_total:,.2f}"); pdf.cell(90, 7, f"Payback Estimado: {año_payback} años", 0, 1)

    return pdf.output(dest='S').encode('latin-1')

st.sidebar.download_button("📥 Descargar Informe Técnico", data=generar_pdf(), file_name=f"Propuesta_{ciudad_sel}.pdf")
