import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
import tempfile
import os

# 1. Base de Datos Técnica Real
ciudades_data = {
    "Guayaquil": {"hsp": [4.12, 4.05, 4.38, 4.51, 4.32, 4.10, 4.45, 4.92, 5.15, 5.02, 4.85, 4.58], "temp": 27.5},
    "Durán": {"hsp": [4.08, 3.98, 4.35, 4.48, 4.28, 4.05, 4.40, 4.88, 5.10, 5.05, 4.90, 4.62], "temp": 27.8},
    "Quito": {"hsp": [4.85, 4.62, 4.28, 4.02, 4.15, 4.65, 5.18, 5.42, 5.35, 4.88, 4.55, 4.68], "temp": 14.5},
    "Cuenca": {"hsp": [4.45, 4.38, 4.25, 4.15, 3.85, 3.72, 3.95, 4.35, 4.62, 4.75, 4.82, 4.55], "temp": 15.0},
    "Esmeraldas": {"hsp": [3.65, 3.82, 4.12, 4.25, 4.18, 3.85, 3.75, 4.05, 4.15, 4.08, 3.95, 3.72], "temp": 26.5},
    "Manta": {"hsp": [4.82, 4.95, 5.15, 5.35, 5.12, 4.85, 4.98, 5.45, 5.75, 5.62, 5.48, 5.15], "temp": 26.2}
}

st.set_page_config(page_title="HSP Ecuador - Análisis 25 Años", layout="wide")

if 'costo_kwp' not in st.session_state:
    st.session_state.costo_kwp = 825.0

# --- SIDEBAR: DATOS DEL CLIENTE ---
st.sidebar.header("📋 Datos de la Propuesta")
nombre_cliente = st.sidebar.text_input("Nombre del Cliente", "Cliente Ejemplo")
tipo_proyecto = st.sidebar.selectbox("Tipo de Proyecto", ["Comercial", "Residencial"])
vendedor = st.sidebar.text_input("Asesor Técnico", "Ing. Solar")

# --- PARÁMETROS PRINCIPALES ---
col_in1, col_in2, col_in3 = st.columns(3)
with col_in1:
    ciudad_sel = st.selectbox("📍 Ciudad", list(ciudades_data.keys()))
with col_in2:
    consumo_mensual = st.number_input("⚡ Consumo (kWh/mes)", value=300.0)
with col_in3:
    pago_planilla = st.number_input("💵 Pago Planilla (USD)", value=30.0)

costo_kwh = pago_planilla / consumo_mensual if consumo_mensual > 0 else 0
info_c = ciudades_data[ciudad_sel]
pr = 0.82 - ((max(0, info_c["temp"] - 15)) * 0.0045)
hsp_avg = sum(info_c["hsp"]) / 12
pot_sug = consumo_mensual / (hsp_avg * pr * 30.44)

# Lógica de sincronización de costos
def up_kwp(): st.session_state.inv_total = st.session_state.costo_kwp * pot_sug
def up_inv(): st.session_state.costo_kwp = st.session_state.inv_total / pot_sug

st.sidebar.number_input("Costo kWp", key="costo_kwp", on_change=up_kwp)
if 'inv_total' not in st.session_state: st.session_state.inv_total = st.session_state.costo_kwp * pot_sug
st.sidebar.number_input("Inversión Total", key="inv_total", on_change=up_inv)

# --- CÁLCULOS ---
costo_total = st.session_state.inv_total
ahorro_trib = (costo_total / 10) if tipo_proyecto == "Comercial" else 0
gen_ini = pot_sug * hsp_avg * pr * 365

data_tabla = []
años_eje = []
acumulados_eje = []
suma_fin = 0
año_payback = None

for i in range(1, 26):
    rend = 0.98 * (0.9945**(i-1))
    ahorro_anual = (gen_ini * rend * costo_kwh) + (ahorro_trib if i <= 10 else 0)
    suma_fin += ahorro_anual
    
    años_eje.append(i)
    acumulados_eje.append(suma_fin)
    
    if suma_fin >= costo_total and año_payback is None:
        año_payback = i

    data_tabla.append({
        "Año": i,
        "Prod. kWh": f"{gen_ini * rend:,.0f}",
        "Ahorro Año": f"${ahorro_anual:,.2f}",
        "Acumulado": f"${suma_fin:,.2f}"
    })

# --- FUNCIÓN PDF ---
def generar_pdf_final():
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Header
    pdf.set_fill_color(31, 119, 180); pdf.rect(0, 0, 210, 35, 'F')
    pdf.set_text_color(255, 255, 255); pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 15, f'PROPUESTA TÉCNICA - {nombre_cliente}', 0, 1, 'C')
    
    # Resumen
    pdf.set_text_color(0, 0, 0); pdf.ln(25)
    pdf.set_font('Arial', 'B', 12); pdf.cell(0, 8, 'RESUMEN FINANCIERO', 0, 1)
    pdf.set_font('Arial', '', 10)
    pdf.cell(95, 7, f'Inversión Inicial: ${costo_total:,.2f}'); pdf.cell(95, 7, f'Payback: {año_payback} años', 0, 1)
    pdf.cell(95, 7, f'Potencia Sugerida: {pot_sug:.2f} kWp'); pdf.cell(95, 7, f'Ciudad: {ciudad_sel}', 0, 1)
    pdf.ln(5)

    # Tabla de Proyección (Los 25 años)
    pdf.set_font('Arial', 'B', 10); pdf.set_fill_color(230, 230, 230)
    pdf.cell(20, 8, 'Año', 1, 0, 'C', True)
    pdf.cell(50, 8, 'Gen. (kWh/año)', 1, 0, 'C', True)
    pdf.cell(60, 8, 'Ahorro Anual (USD)', 1, 0, 'C', True)
    pdf.cell(60, 8, 'Acumulado (USD)', 1, 1, 'C', True)
    
    pdf.set_font('Arial', '', 9)
    for row in data_tabla:
        pdf.cell(20, 7, str(row['Año']), 1, 0, 'C')
        pdf.cell(50, 7, row['Prod. kWh'], 1, 0, 'C')
        pdf.cell(60, 7, row['Ahorro Año'], 1, 0, 'C')
        pdf.cell(60, 7, row['Acumulado'], 1, 1, 'C')

    # --- GRÁFICO AL FINAL (Después de la tabla) ---
    pdf.ln(10)
    plt.figure(figsize=(10, 5))
    plt.plot(años_eje, acumulados_eje, color='#1f77b4', linewidth=2, marker='o', label='Flujo Acumulado')
    plt.axhline(y=costo_total, color='red', linestyle='--', label='Inversión')
    plt.fill_between(años_eje, acumulados_eje, costo_total, where=(pd.Series(acumulados_eje) >= costo_total), color='green', alpha=0.1)
    plt.title("Proyección de Recuperación de Inversión (25 Años)")
    plt.xlabel("Año"); plt.ylabel("USD Acumulado"); plt.legend(); plt.grid(True, alpha=0.3)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        plt.savefig(tmp.name, format='png', dpi=150, bbox_inches='tight')
        # Verificar si hay espacio en la página actual para el gráfico, si no, agregar página
        if pdf.get_y() > 180: 
            pdf.add_page()
        pdf.image(tmp.name, x=15, w=180)
        tmp_path = tmp.name

    res = pdf.output(dest='S').encode('latin-1')
    os.remove(tmp_path)
    return res

# --- INTERFAZ STREAMLIT ---
st.markdown("---")
st.subheader("📊 Proyección de Flujo de Caja (25 Años)")
st.table(pd.DataFrame(data_tabla))

# Botón de descarga en el sidebar
st.sidebar.markdown("---")
st.sidebar.download_button(
    label="📥 Descargar Propuesta PDF",
    data=generar_pdf_final(),
    file_name=f"Propuesta_Solar_{nombre_cliente}.pdf"
)

# Métricas rápidas
m1, m2, m3 = st.columns(3)
m1.metric("Payback Estimado", f"{año_payback} años")
m2.metric("Ahorro Total (25 años)", f"${suma_fin:,.2f}")
m3.metric("ROI (Veces la inversión)", f"{(suma_fin/costo_total):.2f}x")
