import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
import tempfile

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

st.set_page_config(page_title="Análisis Solar 25 Años", layout="wide")

if 'costo_kwp' not in st.session_state:
    st.session_state.costo_kwp = 825.0

# Sidebar
st.sidebar.header("📋 Configuración")
nombre_cliente = st.sidebar.text_input("Cliente", "Cliente Ejemplo")
nombre_proyecto = st.sidebar.text_input("Proyecto", "Residencial Solar")
tipo_proyecto = st.sidebar.selectbox("Tipo", ["Comercial", "Residencial"])
vendedor = st.sidebar.text_input("Asesor", "Ing. Solar")

# Parámetros
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    ciudad_sel = st.selectbox("📍 Ciudad", list(ciudades_data.keys()))
with col2:
    consumo_mensual = st.number_input("⚡ kWh/mes", value=300.0)
with col3:
    pago_planilla = st.number_input("💵 Planilla USD", value=30.0)
    costo_kwh = pago_planilla / consumo_mensual if consumo_mensual > 0 else 0
with col4:
    deg_año1 = st.number_input("% Deg. Año 1", value=2.0) / 100
with col5:
    atenuacion = st.number_input("% Aten. Anual", value=0.55) / 100

# Lógica Técnica
temp_ciudad = ciudades_data[ciudad_sel]["temp"]
pr = 0.82 - ((max(0, temp_ciudad - 15)) * 0.0045)
hsp = sum(ciudades_data[ciudad_sel]["hsp"]) / 12
pot_sug = consumo_mensual / (hsp * pr * 30.44)

# Sincronización de costos
def update_kwp(): st.session_state.inv_total = st.session_state.costo_kwp * pot_sug
def update_inv(): st.session_state.costo_kwp = st.session_state.inv_total / pot_sug
col_c1, col_c2 = st.columns(2)
with col_c1:
    st.number_input("Costo/kWp", key="costo_kwp", on_change=update_kwp)
with col_c2:
    if 'inv_total' not in st.session_state: st.session_state.inv_total = st.session_state.costo_kwp * pot_sug
    st.number_input("Inversión Total", key="inv_total", on_change=update_inv)

# Cálculos Proyección
costo_total = st.session_state.inv_total
ahorro_trib = (costo_total / 10) if tipo_proyecto == "Comercial" else 0
gen_ini = pot_sug * hsp * pr * 365
data_tabla = []
acumulado = 0
años = list(range(1, 26))
ahorros_anuales = []
acumulados = []

for i in años:
    rend = (1 - deg_año1) * ((1 - atenuacion)**(i-1)) if i > 1 else (1 - deg_año1)
    prod = gen_ini * rend
    ahorro_e = prod * costo_kwh
    trib = ahorro_trib if i <= 10 else 0
    total_año = ahorro_e + trib
    acumulado += total_año
    ahorros_anuales.append(total_año)
    acumulados.append(acumulado)
    data_tabla.append({"Año": i, "Prod.": f"{prod:,.0f}", "Ahorro": total_año, "Acum.": acumulado})

# PDF Function
def generar_pdf():
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Encabezado
    pdf.set_fill_color(31, 119, 180); pdf.rect(0, 0, 210, 30, 'F')
    pdf.set_font("Arial", 'B', 16); pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 10, f"PROPUESTA ECONÓMICA: {nombre_cliente.upper()}", 0, 1, 'C')
    
    # Info
    pdf.set_text_color(0, 0, 0); pdf.ln(25); pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "RESUMEN DEL PROYECTO", 0, 1)
    pdf.set_font("Arial", '', 10)
    pdf.cell(90, 7, f"Potencia: {pot_sug:.2f} kWp"); pdf.cell(90, 7, f"Ciudad: {ciudad_sel}", 0, 1)
    pdf.cell(90, 7, f"Inversión: ${costo_total:,.2f}"); pdf.cell(90, 7, f"Costo kWh: ${costo_kwh:.4f}", 0, 1)
    
    # Crear Gráfico para el PDF
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(años, ahorros_anuales, color='#add8e6', label='Ahorro Anual')
    ax.plot(años, acumulados, color='#1f77b4', marker='.', label='Flujo Acumulado')
    ax.axhline(costo_total, color='red', linestyle='--', label='Inversión')
    ax.set_title("Proyección Financiera a 25 Años")
    ax.legend()
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmpfile:
        fig.savefig(tmpfile.name, format='png', bbox_inches='tight')
        pdf.image(tmpfile.name, x=15, y=pdf.get_y() + 5, w=180)
    
    # Tabla
    pdf.ln(85); pdf.set_font("Arial", 'B', 10)
    pdf.cell(20, 8, "Año", 1); pdf.cell(50, 8, "Gen. kWh", 1); pdf.cell(50, 8, "Ahorro USD", 1); pdf.cell(50, 8, "Acumulado", 1, 1)
    pdf.set_font("Arial", '', 9)
    for d in data_tabla:
        pdf.cell(20, 7, str(d['Año']), 1)
        pdf.cell(50, 7, d['Prod.'], 1)
        pdf.cell(50, 7, f"${d['Ahorro']:,.2f}", 1)
        pdf.cell(50, 7, f"${d['Acum.']:,.2f}", 1, 1)
        
    return pdf.output(dest='S').encode('latin-1')

st.sidebar.download_button("📥 Descargar PDF con Gráfico", data=generar_pdf(), file_name="Propuesta_Solar.pdf")
st.dataframe(pd.DataFrame(data_tabla), use_container_width=True)
