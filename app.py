import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
from fpdf import FPDF
import tempfile
import os

# --- BASE DE DATOS TÉCNICA ---
ciudades_data = {
    "Guayaquil": {"hsp": [4.12, 4.05, 4.38, 4.51, 4.32, 4.10, 4.45, 4.92, 5.15, 5.02, 4.85, 4.58], "temp": 27.5},
    "Durán": {"hsp": [4.08, 3.98, 4.35, 4.48, 4.28, 4.05, 4.40, 4.88, 5.10, 5.05, 4.90, 4.62], "temp": 27.8},
    "Quito": {"hsp": [4.85, 4.62, 4.28, 4.02, 4.15, 4.65, 5.18, 5.42, 5.35, 4.88, 4.55, 4.68], "temp": 14.5},
    "Cuenca": {"hsp": [4.45, 4.38, 4.25, 4.15, 3.85, 3.72, 3.95, 4.35, 4.62, 4.75, 4.82, 4.55], "temp": 15.0},
    "Manta": {"hsp": [4.82, 4.95, 5.15, 5.35, 5.12, 4.85, 4.98, 5.45, 5.75, 5.62, 5.48, 5.15], "temp": 26.2}
}

st.set_page_config(page_title="Latitud Solar - Propuestas", layout="wide")

if 'costo_kwp' not in st.session_state:
    st.session_state.costo_kwp = 825.0

# --- SIDEBAR ---
st.sidebar.header("📋 Configuración de Propuesta")
nombre_cliente = st.sidebar.text_input("Cliente", "Martillo Jara Angel Cristobal")
n_proyecto = st.sidebar.text_input("N° Proyecto", "P0000000010")
tipo_proyecto = st.sidebar.selectbox("Tipo de Proyecto", ["Residencial", "Comercial"])
vendedor = st.sidebar.text_input("Asesor", "Ing. Solar")

# --- INTERFAZ APP ---
st.title("☀️ Generador de Propuestas Latitud Solar")

col_a, col_b, col_c = st.columns(3)
with col_a:
    ciudad_sel = st.selectbox("📍 Ciudad", list(ciudades_data.keys()))
with col_b:
    consumo_mensual = st.number_input("⚡ Consumo (kWh/mes)", value=1228.0)
with col_c:
    pago_planilla = st.number_input("💵 Planilla Mensual (USD)", value=149.94)

# Cálculos Técnicos
datos = ciudades_data[ciudad_sel]
hsp_avg = sum(datos["hsp"]) / 12
pr = 0.82 - (max(0, datos["temp"] - 15) * 0.0045)
pot_sug = consumo_mensual / (hsp_avg * pr * 30.44)
gen_y1 = pot_sug * hsp_avg * pr * 365
costo_kwh = pago_planilla / consumo_mensual if consumo_mensual > 0 else 0

# Configuración Inversión
def update_inv(): st.session_state.inv_total = st.session_state.costo_kwp * pot_sug
def update_kwp(): st.session_state.costo_kwp = st.session_state.inv_total / pot_sug if pot_sug > 0 else 0

st.subheader("💰 Inversión")
ci1, ci2 = st.columns(2)
with ci1: st.number_input("Costo/kWp", key="costo_kwp", on_change=update_inv)
with ci2: 
    if 'inv_total' not in st.session_state: update_inv()
    st.number_input("Inversión Total", key="inv_total", on_change=update_kwp)

# Generación de Tabla
data_tabla = []
años_list, acumulados_list = [], []
suma_fin, año_payback = 0, None

for i in range(1, 26):
    deg = (1 - 0.02) * ((1 - 0.0055)**(i-1)) if i > 1 else 0.98
    prod = gen_y1 * deg
    ahorro = prod * costo_kwh
    suma_fin += ahorro
    if suma_fin >= st.session_state.inv_total and año_payback is None: año_payback = i
    
    años_list.append(i); acumulados_list.append(suma_fin)
    data_tabla.append({
        "Año": i, "Ind. Deg.": f"-{deg:.3f}", "Prod. kWh": f"{prod:,.0f}",
        "Ahorro Año": f"${ahorro:,.2f}", "Acumulado": f"${suma_fin:,.2f}"
    })

st.dataframe(pd.DataFrame(data_tabla), use_container_width=True)

# --- FUNCIÓN PDF (CLON DE LA IMAGEN) ---
def crear_pdf_clon():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_margins(15, 15, 15)
    
    # Encabezado Empresa
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(50, 10, 'Latitud Solar', 0, 0, 'L')
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(0, 5, 'LATITUD SOLAR C.LTDA.', 0, 1, 'L')
    pdf.set_font('Arial', '', 8)
    pdf.set_x(65)
    pdf.cell(50, 5, 'RUC   0993403111001', 0, 0, 'L')
    pdf.cell(0, 5, 'TELEFONOS:  0969952794-0959032257', 0, 1, 'L')
    
    # Título Propuesta
    pdf.ln(10)
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, f'PROPUESTA SOLAR - {tipo_proyecto.upper()}', 0, 1, 'C')
    pdf.set_draw_color(31, 119, 180); pdf.set_line_width(0.8)
    pdf.line(40, pdf.get_y(), 170, pdf.get_y())
    
    # Datos del Proyecto
    pdf.ln(12)
    pdf.set_font('Arial', 'B', 10); pdf.cell(0, 10, 'DATOS DEL PROYECTO', 0, 1, 'L')
    pdf.set_font('Arial', '', 9)
    pdf.cell(95, 6, f'Cliente: {nombre_cliente}'); pdf.cell(0, 6, f'Ciudad: {ciudad_sel}', 0, 1)
    pdf.cell(95, 6, f'Proyecto: {n_proyecto}'); pdf.cell(0, 6, f'Costo kWh: ${costo_kwh:.4f}', 0, 1)
    
    # Resumen Financiero
    pdf.ln(8)
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font('Arial', 'B', 10); pdf.cell(0, 8, 'RESUMEN FINANCIERO', 0, 1, 'L', fill=True)
    pdf.set_font('Arial', '', 9)
    pdf.ln(2)
    pdf.cell(95, 6, f'Inversión Total: ${st.session_state.inv_total:,.2f}'); pdf.cell(0, 6, f'Retorno: {año_payback} años', 0, 1)
    pdf.cell(95, 6, f'Potencia: {pot_sug:.2f} kWp'); pdf.cell(0, 6, f'Planilla Mensual: ${pago_planilla:,.2f}', 0, 1)
    
    # Tabla (Estilo exacto)
    pdf.ln(10)
    pdf.set_fill_color(31, 119, 180); pdf.set_text_color(255, 255, 255); pdf.set_font('Arial', 'B', 9)
    pdf.set_draw_color(50, 50, 50); pdf.set_line_width(0.2)
    
    w = [20, 30, 45, 45, 45]
    h = ['Año', 'Ind. Deg.', 'Prod. kWh', 'Ahorro Año', 'Acumulado']
    for i in range(len(h)):
        pdf.cell(w[i], 8, h[i], 1, 0, 'C', fill=True)
    pdf.ln()
    
    pdf.set_text_color(0, 0, 0); pdf.set_font('Arial', '', 8)
    for d in data_tabla:
        pdf.cell(w[0], 7, str(d['Año']), 1, 0, 'C')
        pdf.cell(w[1], 7, d['Ind. Deg.'], 1, 0, 'C')
        pdf.cell(w[2], 7, d['Prod. kWh'], 1, 0, 'C')
        pdf.cell(w[3], 7, d['Ahorro Año'], 1, 0, 'C')
        pdf.cell(w[4], 7, d['Acumulado'], 1, 1, 'C')

    # Gráfico al final
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(años_list, acumulados_list, color='#1f77b4', marker='o')
    ax.axhline(y=st.session_state.inv_total, color='red', linestyle='--')
    ax.set_title("Flujo de Caja Acumulado")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        plt.savefig(tmp.name, dpi=150); plot_path = tmp.name
    
    if pdf.get_y() > 180: pdf.add_page()
    pdf.image(plot_path, x=15, w=180)
    plt.close()
    return pdf.output(dest='S').encode('latin-1')

st.sidebar.download_button("📥 Descargar Propuesta PDF", data=crear_pdf_clon(), file_name=f"Propuesta_{nombre_cliente}.pdf")
