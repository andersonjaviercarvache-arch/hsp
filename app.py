import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
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

st.set_page_config(page_title="HSP Ecuador - Análisis de Inversión", layout="wide")

# Inicialización de estados
if 'costo_kwp' not in st.session_state:
    st.session_state.costo_kwp = 825.0

# --- SIDEBAR: DATOS DEL CLIENTE ---
st.sidebar.header("📋 Datos de la Propuesta")
nombre_cliente = st.sidebar.text_input("Nombre del Cliente", "Cliente Ejemplo")
nombre_proyecto = st.sidebar.text_input("Nombre del Proyecto", "Instalación Solar")
tipo_proyecto = st.sidebar.selectbox("Tipo de Proyecto", ["Comercial", "Residencial"])
vendedor = st.sidebar.text_input("Asesor Técnico", "Ing. Solar")

st.title("☀️ Análisis de Retorno de Inversión Solar (Payback)")
st.markdown(f"### Proyecto: {tipo_proyecto}")
st.markdown("---")

# 2. PARÁMETROS TÉCNICOS Y DE FACTURACIÓN
with st.container():
    col_input1, col_input2, col_input3, col_input4, col_input5 = st.columns(5)
    with col_input1:
        lista_ciudades = [c for c in ciudades_data.keys() if c != "Mes"]
        ciudad_sel = st.selectbox("📍 Ciudad", lista_ciudades)
    with col_input2:
        consumo_mensual = st.number_input("⚡ Consumo (kWh/mes)", value=300.0, step=10.0, min_value=1.0)
    with col_input3:
        pago_planilla = st.number_input("💵 Pago Planilla Mensual (USD)", value=27.60, step=1.00, format="%.2f")
        costo_kwh = pago_planilla / consumo_mensual if consumo_mensual > 0 else 0
        st.info(f"Costo kWh calculado: ${costo_kwh:.4f}")
    with col_input4:
        deg_año1 = st.number_input("📉 Deg. Año 1 (%)", value=2.0, format="%.2f", step=0.1) / 100
    with col_input5:
        atenuacion_anual = st.number_input("📉 Aten. Anual (%)", value=0.55, format="%.2f", step=0.05) / 100

# Lógica técnica con validación (Previene TypeError)
ciudad_info = ciudades_data.get(ciudad_sel, list(ciudades_data.values())[1])
temp_ciudad = ciudad_info["temp"]
pr_ajustado = 0.82 - ((max(0, temp_ciudad - 15)) * 0.0045)
hsp_promedio_base = sum(ciudad_info["hsp"]) / 12
pot_sug = consumo_mensual / (hsp_promedio_base * pr_ajustado * 30.44)

# --- CONFIGURACIÓN DE INVERSIÓN ---
st.subheader("💰 Configuración de Costos e Inversión")
col_c1, col_c2 = st.columns(2)

def update_from_kwp():
    st.session_state.inv_total = st.session_state.costo_kwp * pot_sug
def update_from_inv():
    st.session_state.costo_kwp = st.session_state.inv_total / pot_sug if pot_sug > 0 else 0

with col_c1:
    st.number_input("Costo por kWp instalado (USD)", key="costo_kwp", on_change=update_from_kwp, step=10.0)
with col_c2:
    if 'inv_total' not in st.session_state:
        st.session_state.inv_total = st.session_state.costo_kwp * pot_sug
    st.number_input("Inversión Total del Proyecto (USD)", key="inv_total", on_change=update_from_inv, step=100.0)

# 3. LÓGICA DE PROYECCIÓN (25 AÑOS)
costo_planta_total = st.session_state.inv_total
ahorro_trib_anual = (costo_planta_total / 10) if tipo_proyecto == "Comercial" else 0.0
gen_anual_inicial = pot_sug * hsp_promedio_base * pr_ajustado * 365

data_tabla = []
años_lista = list(range(1, 26))
acumulados_lista = []
suma_fin = 0
año_payback = None

for i in años_lista:
    rend = (1 - deg_año1) * ((1 - atenuacion_anual)**(i-1)) if i > 1 else (1 - deg_año1)
    prod = gen_anual_inicial * rend
    ahorro_en = prod * costo_kwh
    trib = ahorro_trib_anual if i <= 10 else 0
    total_anual = ahorro_en + trib
    suma_fin += total_anual
    acumulados_lista.append(suma_fin)
    
    if suma_fin >= costo_planta_total and año_payback is None:
        año_payback = i

    data_tabla.append({
        "Año": i,
        "Degradación": f"{(rend*100):.1f}%", 
        "Prod. (kWh)": f"{prod:,.0f}",
        "Ahorro (USD)": f"${total_anual:,.2f}",
        "Acumulado": suma_fin
    })

# --- FUNCIÓN PDF ---
def crear_pdf():
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Header
    pdf.set_fill_color(31, 119, 180); pdf.rect(0, 0, 210, 35, 'F')
    pdf.set_text_color(255, 255, 255); pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 15, f'PROPUESTA TÉCNICA ECONÓMICA - {tipo_proyecto.upper()}', 0, 1, 'C')
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 5, f'Asesor: {vendedor} | Ciudad: {ciudad_sel}', 0, 1, 'C')
    
    # Resumen
    pdf.set_text_color(0, 0, 0); pdf.ln(20); pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'RESUMEN FINANCIERO', 0, 1)
    pdf.set_font('Arial', '', 10)
    payback_txt = f"{año_payback} años" if año_payback else "> 25 años"
    pdf.cell(95, 7, f'Cliente: {nombre_cliente}'); pdf.cell(95, 7, f'Retorno (Payback): {payback_txt}', 0, 1)
    pdf.cell(95, 7, f'Inversión: ${costo_planta_total:,.2f}'); pdf.cell(95, 7, f'Potencia: {pot_sug:.2f} kWp', 0, 1)

    # Generar Gráfico para PDF
    plt.figure(figsize=(8, 4))
    plt.plot(años_lista, acumulados_lista, color='#1f77b4', marker='o', linewidth=2, label='Flujo Acumulado')
    plt.axhline(y=costo_planta_total, color='r', linestyle='--', label='Inversión')
    plt.title("Proyección de Recuperación de Inversión")
    plt.xlabel("Años"); plt.ylabel("Dólares (USD)"); plt.legend(); plt.grid(True, alpha=0.3)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        plt.savefig(tmp.name, format='png', dpi=150, bbox_inches='tight')
        pdf.image(tmp.name, x=15, y=pdf.get_y() + 10, w=180)
        tmp_path = tmp.name

    # Tabla (en página nueva si es necesario)
    pdf.ln(95)
    pdf.set_font('Arial', 'B', 9); pdf.set_fill_color(31, 119, 180); pdf.set_text_color(255, 255, 255)
    pdf.cell(20, 8, 'Año', 1, 0, 'C', True); pdf.cell(30, 8, 'Eficiencia', 1, 0, 'C', True)
    pdf.cell(45, 8, 'Gen. kWh', 1, 0, 'C', True); pdf.cell(45, 8, 'Ahorro USD', 1, 0, 'C', True); pdf.cell(45, 8, 'Acumulado', 1, 1, 'C', True)
    
    pdf.set_text_color(0, 0, 0); pdf.set_font('Arial', '', 8)
    for d in data_tabla:
        pdf.cell(20, 6, str(d['Año']), 1, 0, 'C')
        pdf.cell(30, 6, d['Degradación'], 1, 0, 'C')
        pdf.cell(45, 6, d['Prod. (kWh)'], 1, 0, 'C')
        pdf.cell(45, 6, d['Ahorro (USD)'], 1, 0, 'C')
        pdf.cell(45, 6, f"${d['Acumulado']:,.2f}", 1, 1, 'C')

    res_pdf = pdf.output(dest='S').encode('latin-1')
    os.remove(tmp_path)
    return res_pdf

# 5. DASHBOARD STREAMLIT
st.markdown("---")
col_res1, col_res2, col_res3, col_res4 = st.columns(4)
col_res1.metric("Inversión Final", f"${costo_planta_total:,.2f}")
col_res2.metric("Potencia Sugerida", f"{pot_sug:.2f} kWp")
col_res3.metric("Ahorro 25 Años", f"${suma_fin:,.2f}")
col_res4.metric("Payback", f"{año_payback} años" if año_payback else "> 25 años")

st.sidebar.markdown("---")
st.sidebar.download_button("📥 Descargar Propuesta PDF", data=crear_pdf(), file_name=f"Propuesta_{nombre_cliente}.pdf")

st.subheader("Gráfico de Recuperación de Inversión")
st.line_chart(pd.DataFrame({"USD Acumulado": acumulados_lista}, index=años_lista))
st.dataframe(pd.DataFrame(data_tabla), use_container_width=True)
