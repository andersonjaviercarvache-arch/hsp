import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
from fpdf import FPDF
import tempfile
import os

# 1. Base de Datos Técnica Real
ciudades_data = {
    "Mes": ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"],
    "Guayaquil": {"hsp": [4.12, 4.05, 4.38, 4.51, 4.32, 4.10, 4.45, 4.92, 5.15, 5.02, 4.85, 4.58], "temp": 27.5},
    "Durán": {"hsp": [4.08, 3.98, 4.35, 4.48, 4.28, 4.05, 4.40, 4.88, 5.10, 5.05, 4.90, 4.62], "temp": 27.8},
    "Quito": {"hsp": [4.85, 4.62, 4.28, 4.02, 4.15, 4.65, 5.18, 5.42, 5.35, 4.88, 4.55, 4.68], "temp": 14.5},
    "Cuenca": {"hsp": [4.45, 4.38, 4.25, 4.15, 3.85, 3.72, 3.95, 4.35, 4.62, 4.75, 4.82, 4.55], "temp": 15.0},
    "Esmeraldas": {"hsp": [3.65, 3.82, 4.12, 4.25, 4.18, 3.85, 3.75, 4.05, 4.15, 4.08, 3.95, 3.72], "temp": 26.5},
    "Quinindé": {"hsp": [3.55, 3.68, 3.92, 4.10, 4.05, 3.78, 3.65, 3.95, 4.08, 4.02, 3.92, 3.62], "temp": 26.0},
    "Santo Domingo": {"hsp": [3.45, 3.55, 3.85, 4.02, 3.95, 3.62, 3.58, 3.82, 3.95, 3.92, 3.88, 3.55], "temp": 24.0},
    "Loja": {"hsp": [4.65, 4.52, 4.48, 4.35, 4.12, 3.95, 4.08, 4.55, 4.95, 5.12, 5.25, 4.92], "temp": 16.5},
    "Manta": {"hsp": [4.82, 4.95, 5.15, 5.35, 5.12, 4.85, 4.98, 5.45, 5.75, 5.62, 5.48, 5.15], "temp": 26.2}
}

st.set_page_config(page_title="Latitud Solar - Simulador Pro", layout="wide")

if 'costo_kwp' not in st.session_state:
    st.session_state.costo_kwp = 825.0

# --- SIDEBAR ---
st.sidebar.header("📋 Datos de la Propuesta")
nombre_cliente = st.sidebar.text_input("Nombre del Cliente", "Martillo Jara Angel Cristobal")
n_proyecto = st.sidebar.text_input("N° Proyecto", "P0000000010")
tipo_proyecto = st.sidebar.selectbox("Tipo de Proyecto", ["Residencial", "Comercial"])
vendedor = st.sidebar.text_input("Asesor Técnico", "Ing. Solar")

st.title("☀️ Latitud Solar: Análisis de Inversión")

# --- PARÁMETROS TÉCNICOS (TODOS LOS CAMPOS RESTAURADOS) ---
with st.container():
    col_input1, col_input2, col_input3, col_input4, col_input5 = st.columns(5)
    with col_input1:
        lista_ciudades = [c for c in ciudades_data.keys() if c != "Mes"]
        ciudad_sel = st.selectbox("📍 Ciudad", lista_ciudades)
    with col_input2:
        consumo_mensual = st.number_input("⚡ Consumo (kWh/mes)", value=1228.0)
    with col_input3:
        pago_planilla = st.number_input("💵 Planilla Mensual (USD)", value=149.94)
        costo_kwh = pago_planilla / consumo_mensual if consumo_mensual > 0 else 0
        st.info(f"Costo kWh: ${costo_kwh:.4f}")
    with col_input4:
        deg_año1 = st.number_input("📉 Deg. Año 1 (%)", value=2.0) / 100
    with col_input5:
        atenuacion_anual = st.number_input("📉 Aten. Anual (%)", value=0.55) / 100

# Lógica Meteorológica Dinámica
temp_ciudad = ciudades_data[ciudad_sel]["temp"]
hsp_promedio_base = sum(ciudades_data[ciudad_sel]["hsp"]) / 12
pr_ajustado = 0.82 - ((max(0, temp_ciudad - 15)) * 0.0045)
pot_sug = consumo_mensual / (hsp_promedio_base * pr_ajustado * 30.44)
gen_anual_inicial = pot_sug * hsp_promedio_base * pr_ajustado * 365

with st.expander("🌍 Panel Meteorológico y Eficiencia", expanded=True):
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    m_col1.metric("HSP Promedio", f"{hsp_promedio_base:.2f} h/día")
    m_col2.metric("Temp. Ambiente", f"{temp_ciudad}°C")
    m_col3.metric("PR Ajustado", f"{pr_ajustado:.2%}")
    m_col4.metric("Gen. Año 1", f"{gen_anual_inicial:,.0f} kWh")

# --- COSTOS E INVERSIÓN ---
st.subheader("💰 Configuración de Inversión")
def update_from_kwp(): st.session_state.inv_total = st.session_state.costo_kwp * pot_sug
def update_from_inv(): st.session_state.costo_kwp = st.session_state.inv_total / pot_sug if pot_sug > 0 else 0

col_c1, col_c2 = st.columns(2)
with col_c1:
    st.number_input("Costo por kWp (USD)", key="costo_kwp", on_change=update_from_kwp)
with col_c2:
    if 'inv_total' not in st.session_state: update_from_kwp()
    st.number_input("Inversión Total (USD)", key="inv_total", on_change=update_from_inv)

# --- CÁLCULO FINANCIERO 25 AÑOS ---
costo_planta_total = st.session_state.inv_total
ahorro_tributario_anual = (costo_planta_total / 10) if tipo_proyecto == "Comercial" else 0.0
data_tabla, años_list, acumulados_list = [], [], []
suma_fin, año_payback = 0, None

for i in range(1, 26):
    rendimiento_pct = (1 - deg_año1) * ((1 - atenuacion_anual)**(i-1)) if i > 1 else (1 - deg_año1)
    prod = gen_anual_inicial * rendimiento_pct
    ahorro_en = prod * costo_kwh
    beneficio_trib = ahorro_tributario_anual if i <= 10 else 0
    total_anual = ahorro_en + beneficio_trib
    suma_fin += total_anual
    
    años_list.append(i); acumulados_list.append(suma_fin)
    if suma_fin >= costo_planta_total and año_payback is None: año_payback = i

    data_tabla.append({
        "Año": i, "Ind. Deg.": f"-{rendimiento_pct:.3f}", "Prod. kWh": f"{prod:,.0f}",
        "Ahorro Año": f"${total_anual:,.2f}", "Acumulado": f"${suma_fin:,.2f}"
    })

st.dataframe(pd.DataFrame(data_tabla), use_container_width=True)

# --- FUNCIÓN PDF BASADA EN "Captura de pantalla 2026-05-01 231848.png" ---
def crear_pdf_latitud():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_margins(15, 15, 15)
    
    # Encabezado Superior (Logo y Datos Empresa)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(50, 10, 'Latitud Solar', 0, 0, 'L')
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(0, 5, 'LATITUD SOLAR C.LTDA.', 0, 1, 'L')
    pdf.set_font('Arial', '', 8)
    pdf.set_x(65)
    pdf.cell(50, 5, 'RUC   0993403111001', 0, 0, 'L')
    pdf.cell(0, 5, f'TELEFONOS:  0969952794-0959032257', 0, 1, 'L')
    
    # Título Propuesta
    pdf.ln(10)
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, f'PROPUESTA SOLAR - {tipo_proyecto.upper()}', 0, 1, 'C')
    pdf.set_draw_color(31, 119, 180); pdf.set_line_width(0.8)
    pdf.line(40, pdf.get_y(), 170, pdf.get_y())
    
    # Sección: Datos del Proyecto
    pdf.ln(12)
    pdf.set_font('Arial', 'B', 11); pdf.cell(0, 10, 'DATOS DEL PROYECTO', 0, 1, 'L')
    pdf.set_font('Arial', '', 9)
    pdf.cell(95, 6, f'Cliente: {nombre_cliente}'); pdf.cell(0, 6, f'Ciudad: {ciudad_sel}', 0, 1)
    pdf.cell(95, 6, f'Proyecto: {n_proyecto}'); pdf.cell(0, 6, f'Costo kWh: ${costo_kwh:.4f}', 0, 1)
    
    # Sección: Resumen Financiero
    pdf.ln(8)
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font('Arial', 'B', 11); pdf.cell(0, 8, 'RESUMEN FINANCIERO', 0, 1, 'L', fill=True)
    pdf.set_font('Arial', '', 9)
    pdf.ln(2)
    pdf.cell(95, 6, f'Inversión Total: ${costo_planta_total:,.2f}'); pdf.cell(0, 6, f'Retorno: {año_payback} años', 0, 1)
    pdf.cell(95, 6, f'Potencia: {pot_sug:.2f} kWp'); pdf.cell(0, 6, f'Planilla Mensual: ${pago_planilla:,.2f}', 0, 1)
    
    # Tabla de Datos (Estilo Captura)
    pdf.ln(10)
    pdf.set_fill_color(31, 119, 180); pdf.set_text_color(255, 255, 255); pdf.set_font('Arial', 'B', 9)
    pdf.set_draw_color(50, 50, 50); pdf.set_line_width(0.2)
    
    # Cabeceras
    w = [15, 25, 45, 45, 50]
    headers = ['Año', 'Ind. Deg.', 'Prod. kWh', 'Ahorro Año', 'Acumulado']
    for i in range(len(headers)):
        pdf.cell(w[i], 8, headers[i], 1, 0, 'C', fill=True)
    pdf.ln()
    
    # Filas
    pdf.set_text_color(0, 0, 0); pdf.set_font('Arial', '', 8)
    for d in data_tabla:
        pdf.cell(w[0], 7, str(d['Año']), 1, 0, 'C')
        pdf.cell(w[1], 7, d['Ind. Deg.'], 1, 0, 'C')
        pdf.cell(w[2], 7, d['Prod. kWh'], 1, 0, 'C')
        pdf.cell(w[3], 7, d['Ahorro Año'], 1, 0, 'C')
        pdf.cell(w[4], 7, d['Acumulado'], 1, 1, 'C')

    # Gráfico de flujo (Acomodado al final)
    plt.style.use('seaborn-v0_8-muted')
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(años_list, acumulados_list, color='#1f77b4', marker='o', linewidth=2)
    ax.axhline(y=costo_planta_total, color='r', linestyle='--', label='Inversión')
    ax.set_title("Flujo de Caja Acumulado (25 años)")
    ax.yaxis.set_major_formatter(mtick.StrMethodFormatter('${x:,.0f}'))
    ax.grid(True, alpha=0.3)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        plt.savefig(tmp.name, dpi=150, bbox_inches='tight'); plot_path = tmp.name
    
    if pdf.get_y() > 180: pdf.add_page()
    pdf.image(plot_path, x=15, w=180)
    plt.close()
    os.remove(plot_path)
    
    return pdf.output(dest='S').encode('latin-1')

st.sidebar.markdown("---")
st.sidebar.download_button("📥 Descargar Propuesta PDF", data=crear_pdf_latitud(), file_name=f"Propuesta_{nombre_cliente}.pdf")
