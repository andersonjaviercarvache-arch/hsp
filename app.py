import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
import tempfile
import os

# 1. BASE DE DATOS TÉCNICA SUSTENTADA (NASA POWER / PVGIS / NREL)
# Valores promediados para optimización fotovoltaica en Ecuador
ciudades_data = {
    "Mes": ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"],
    "Guayaquil": {"hsp": [4.21, 4.15, 4.48, 4.55, 4.38, 4.15, 4.52, 4.98, 5.21, 5.08, 4.92, 4.65], "temp": 27.2, "fuente": "NASA POWER / NREL"},
    "Durán": {"hsp": [4.18, 4.10, 4.42, 4.50, 4.35, 4.12, 4.48, 4.95, 5.18, 5.05, 4.88, 4.62], "temp": 27.5, "fuente": "NASA POWER / PVGIS"},
    "Quito": {"hsp": [4.95, 4.75, 4.42, 4.15, 4.28, 4.75, 5.25, 5.48, 5.40, 4.98, 4.65, 4.78], "temp": 14.8, "fuente": "PVGIS / Global Solar Atlas"},
    "Cuenca": {"hsp": [4.55, 4.45, 4.32, 4.20, 3.95, 3.82, 4.05, 4.45, 4.72, 4.85, 4.92, 4.65], "temp": 15.2, "fuente": "NASA POWER / PVGIS"},
    "Esmeraldas": {"hsp": [3.75, 3.92, 4.22, 4.35, 4.28, 3.95, 3.85, 4.15, 4.25, 4.18, 4.05, 3.82], "temp": 26.8, "fuente": "NASA POWER / NREL"},
    "Quinindé": {"hsp": [3.65, 3.78, 4.02, 4.20, 4.15, 3.88, 3.75, 4.05, 4.18, 4.12, 4.02, 3.72], "temp": 26.2, "fuente": "NASA POWER / PVGIS"},
    "Santo Domingo": {"hsp": [3.55, 3.65, 3.95, 4.12, 4.05, 3.72, 3.68, 3.92, 4.05, 4.02, 3.98, 3.65], "temp": 24.5, "fuente": "Global Solar Atlas"},
    "Loja": {"hsp": [4.75, 4.62, 4.58, 4.45, 4.22, 4.05, 4.18, 4.65, 5.05, 5.22, 5.35, 5.02], "temp": 16.2, "fuente": "PVGIS / NASA POWER"},
    "Manta": {"hsp": [4.92, 5.05, 5.25, 5.45, 5.22, 4.95, 5.08, 5.55, 5.85, 5.72, 5.58, 5.25], "temp": 25.8, "fuente": "Global Solar Atlas / NREL"}
}

st.set_page_config(page_title="HSP Ecuador - Sustento Técnico", layout="wide")

if 'costo_kwp' not in st.session_state:
    st.session_state.costo_kwp = 825.0

# --- SIDEBAR ---
st.sidebar.header("📋 Datos de la Propuesta")
nombre_cliente = st.sidebar.text_input("Nombre del Cliente", "Cliente Ejemplo")
nombre_proyecto = st.sidebar.text_input("Nombre del Proyecto", "Instalación Solar")
tipo_proyecto = st.sidebar.selectbox("Tipo de Proyecto", ["Comercial", "Residencial"])
vendedor = st.sidebar.text_input("Asesor Técnico", "Ing. Solar")

st.title("☀️ Análisis Solar con Sustento Meteorológico Real")
st.markdown(f"### Proyecto: {tipo_proyecto}")

# 2. PARÁMETROS TÉCNICOS
with st.container():
    col_input1, col_input2, col_input3, col_input4, col_input5 = st.columns(5)
    with col_input1:
        lista_ciudades = [c for c in ciudades_data.keys() if c != "Mes"]
        ciudad_sel = st.selectbox("📍 Ciudad", lista_ciudades)
    with col_input2:
        consumo_mensual = st.number_input("⚡ Consumo (kWh/mes)", value=300.0, step=10.0)
    with col_input3:
        pago_planilla = st.number_input("💵 Pago Planilla (USD)", value=27.60, format="%.2f")
        costo_kwh = pago_planilla / consumo_mensual if consumo_mensual > 0 else 0
        st.info(f"Costo kWh: ${costo_kwh:.4f}")
    with col_input4:
        deg_año1 = st.number_input("📉 Deg. Año 1 (%)", value=2.0) / 100
    with col_input5:
        atenuacion_anual = st.number_input("📉 Aten. Anual (%)", value=0.55) / 100

# Cálculos Técnicos
temp_ciudad = ciudades_data[ciudad_sel]["temp"]
fuente_ciudad = ciudades_data[ciudad_sel]["fuente"]
hsp_promedio_base = sum(ciudades_data[ciudad_sel]["hsp"]) / 12
# Factor PR basado en pérdidas por temperatura (STC 25°C)
pr_ajustado = 0.82 - ((max(0, temp_ciudad - 15)) * 0.0045)
pot_sug = consumo_mensual / (hsp_promedio_base * pr_ajustado * 30.44)
gen_anual_inicial = pot_sug * hsp_promedio_base * pr_ajustado * 365

# --- INFO METEOROLÓGICA CON SUSTENTO ---
with st.expander("🌍 Sustento de Irradiación y Clima", expanded=True):
    m_col1, m_col2, m_col3 = st.columns([2, 1, 1])
    with m_col1:
        st.markdown(f"**Fuente de Datos:** {fuente_ciudad}")
        st.caption("Datos basados en el promedio de los últimos 20 años de radiación solar satelital.")
    with m_col2:
        st.metric("HSP Anual", f"{hsp_promedio_base:.2f} kWh/m²/día")
    with m_col3:
        st.metric("Temp. Media", f"{temp_ciudad}°C")

# --- CONFIGURACIÓN DE INVERSIÓN ---
st.subheader("💰 Inversión")
col_c1, col_c2 = st.columns(2)

def update_from_kwp():
    st.session_state.inv_total = st.session_state.costo_kwp * pot_sug
def update_from_inv():
    st.session_state.costo_kwp = st.session_state.inv_total / pot_sug if pot_sug > 0 else 0

with col_c1:
    st.number_input("Costo por kWp (USD)", key="costo_kwp", on_change=update_from_kwp)
with col_c2:
    if 'inv_total' not in st.session_state:
        st.session_state.inv_total = st.session_state.costo_kwp * pot_sug
    st.number_input("Inversión Total (USD)", key="inv_total", on_change=update_from_inv)

costo_planta_total = st.session_state.inv_total
ahorro_tributario_anual = (costo_planta_total / 10) if tipo_proyecto == "Comercial" else 0.0

# 4. TABLA DE PROYECCIÓN
data_tabla = []
años_list, acumulados_list = [], []
suma_fin, año_payback = 0, None

for i in range(1, 26):
    rendimiento_pct = (1 - deg_año1) * ((1 - atenuacion_anual)**(i-1)) if i > 1 else (1 - deg_año1)
    prod = gen_anual_inicial * rendimiento_pct
    ahorro_en = prod * costo_kwh
    beneficio_trib = ahorro_tributario_anual if i <= 10 else 0
    total_anual = ahorro_en + beneficio_trib
    suma_fin += total_anual
    
    años_list.append(i)
    acumulados_list.append(suma_fin)
    if suma_fin >= costo_planta_total and año_payback is None: año_payback = i

    data_tabla.append({
        "Año": i,
        "Índice de Degradación": f"-{rendimiento_pct:.3f}", 
        "Prod. (kWh/año)": f"{prod:,.0f}",
        "Ahorro Energía": f"${ahorro_en:,.2f}",
        "Ahorro Trib.": f"${beneficio_trib:,.2f}",
        "Ahorro Total Año": f"${total_anual:,.2f}",
        "Acumulado": f"${suma_fin:,.2f}"
    })

# 5. RESULTADOS
st.markdown("---")
payback_text = f"{año_payback} años" if año_payback else "> 25 años"
c1, c2, c3, c4 = st.columns(4)
c1.metric("Inversión", f"${costo_planta_total:,.2f}")
c2.metric("Potencia DC", f"{pot_sug:.2f} kWp")
c3.metric("Ahorro 25 Años", f"${suma_fin:,.2f}")
c4.metric("Payback", payback_text)

st.dataframe(pd.DataFrame(data_tabla), use_container_width=True)

# --- FUNCIÓN PDF ---
def crear_pdf():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, f'INFORME TÉCNICO FOTOVOLTAICO - {nombre_proyecto}', 0, 1, 'C')
    
    pdf.ln(10)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, '1. SUSTENTO METEOROLÓGICO', 0, 1, 'L')
    pdf.set_font('Arial', '', 10)
    pdf.multi_cell(0, 7, f"La presente proyección utiliza datos de irradiación global horizontal (GHI) obtenidos de {fuente_ciudad}. "
                        f"Se ha calculado una Hora Solar Pico (HSP) de {hsp_promedio_base:.2f} h/día para {ciudad_sel}, "
                        f"ajustada por un Performance Ratio (PR) del {pr_ajustado:.2%} debido a condiciones de temperatura local.")

    pdf.ln(5)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, '2. RESUMEN DE LA PROPUESTA', 0, 1, 'L')
    pdf.set_font('Arial', '', 10)
    pdf.cell(90, 7, f"Cliente: {nombre_cliente}"); pdf.cell(90, 7, f"Potencia Instalada: {pot_sug:.2f} kWp", 0, 1)
    pdf.cell(90, 7, f"Inversión Total: ${costo_planta_total:,.2f}"); pdf.cell(90, 7, f"Retorno (Payback): {payback_text}", 0, 1)

    # Tabla dinámica
    pdf.ln(10)
    pdf.set_fill_color(31, 119, 180); pdf.set_text_color(255, 255, 255)
    widths = [10, 20, 30, 40, 40, 40]
    headers = ['Año', 'Deg.', 'kWh/año', 'Ahorro En.', 'Total Año', 'Acumulado']
    for i, h in enumerate(headers): pdf.cell(widths[i], 8, h, 1, 0, 'C', True)
    pdf.ln(); pdf.set_text_color(0, 0, 0); pdf.set_font('Arial', '', 8)
    
    for d in data_tabla[:25]:
        pdf.cell(widths[0], 7, str(d['Año']), 1)
        pdf.cell(widths[1], 7, d['Índice de Degradación'], 1)
        pdf.cell(widths[2], 7, d['Prod. (kWh/año)'], 1)
        pdf.cell(widths[3], 7, d['Ahorro Energía'], 1)
        pdf.cell(widths[4], 7, d['Ahorro Total Año'], 1)
        pdf.cell(widths[5], 7, d['Acumulado'], 1, 1)

    return pdf.output(dest='S').encode('latin-1')

st.sidebar.download_button("📥 Descargar PDF Técnico", data=crear_pdf(), file_name="Propuesta_Tecnica.pdf")
