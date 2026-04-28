import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
import tempfile

# --- 1. CONFIGURACIÓN Y DATOS (Igual al anterior) ---
ciudades_data = {
    "Mes": ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"],
    "Guayaquil": {"hsp": [4.12, 4.05, 4.38, 4.51, 4.32, 4.10, 4.45, 4.92, 5.15, 5.02, 4.85, 4.58], "temp": 27.5},
    "Quito": {"hsp": [4.85, 4.62, 4.28, 4.02, 4.15, 4.65, 5.18, 5.42, 5.35, 4.88, 4.55, 4.68], "temp": 14.5},
    "Manta": {"hsp": [4.82, 4.95, 5.15, 5.35, 5.12, 4.85, 4.98, 5.45, 5.75, 5.62, 5.48, 5.15], "temp": 26.2}
    # (Puedes re-agregar el resto de ciudades aquí)
}

st.set_page_config(page_title="Generador de Propuestas Solares", layout="wide")

# --- 2. DATOS DEL CLIENTE (NUEVA SECCIÓN) ---
st.sidebar.header("👤 Datos del Cliente")
with st.sidebar:
    nombre_cliente = st.text_input("Nombre del Cliente", "Juan Pérez")
    empresa_cliente = st.text_input("Empresa/Proyecto", "Residencia Pérez")
    ubicacion = st.text_input("Dirección", "Vía a la Costa, Guayaquil")
    num_propuesta = st.text_input("N° de Propuesta", "PROP-2024-001")

st.title("☀️ Propuesta Técnica y Económica Solar")
st.markdown("---")

# --- 3. PARÁMETROS TÉCNICOS ---
with st.container():
    col_input1, col_input2, col_input3, col_input4, col_input5 = st.columns(5)
    with col_input1:
        lista_ciudades = [c for c in ciudades_data.keys() if c != "Mes"]
        ciudad_sel = st.selectbox("📍 Ciudad", lista_ciudades)
    with col_input2:
        consumo_mensual = st.number_input("⚡ Consumo (kWh/mes)", value=300.0)
    with col_input3:
        costo_kwh = st.number_input("💵 Costo kWh (USD)", value=0.0920, format="%.4f")
    with col_input4:
        deg_año1 = st.number_input("📉 Deg. Año 1 (%)", value=2.0) / 100
    with col_input5:
        atenuacion_anual = st.number_input("📉 Aten. Anual (%)", value=0.55) / 100

# --- 4. LÓGICA DE CÁLCULO ---
temp_ciudad = ciudades_data[ciudad_sel]["temp"]
pr_ajustado = 0.82 - ((max(0, temp_ciudad - 15)) * 0.0045)
hsp_promedio_base = sum(ciudades_data[ciudad_sel]["hsp"]) / 12

pot_sug = consumo_mensual / (hsp_promedio_base * pr_ajustado * 30.44)
costo_planta_total = pot_sug * 825.0
ahorro_tributario_anual = costo_planta_total / 10
gen_anual_inicial = pot_sug * hsp_promedio_base * pr_ajustado * 365

años_lista = list(range(1, 26))
data_tabla = []
suma_fin = 0
año_payback = None

for i in años_lista:
    rendimiento_pct = (1 - deg_año1) * ((1 - atenuacion_anual)**(i-1)) if i > 1 else (1 - deg_año1)
    indice_degradacion = -rendimiento_pct 
    prod = gen_anual_inicial * rendimiento_pct
    ahorro_en = prod * costo_kwh
    beneficio_trib = ahorro_tributario_anual if i <= 10 else 0
    total_anual = ahorro_en + beneficio_trib
    suma_fin += total_anual
    
    if suma_fin >= costo_planta_total and año_payback is None:
        año_payback = i

    data_tabla.append({
        "Año": i,
        "Índice de Degradación": f"{indice_degradacion:.3f}",
        "Prod. (kWh/año)": round(prod, 0),
        "Ahorro Total Año": round(total_anual, 2),
        "Acumulado": round(suma_fin, 2)
    })

df_proyeccion = pd.DataFrame(data_tabla)

# --- 5. VISUALIZACIÓN EN APP ---
st.subheader(f"Propuesta para: {nombre_cliente} - {empresa_cliente}")
st.dataframe(df_proyeccion, use_container_width=True)

# --- 6. GENERACIÓN DE PDF (NUEVO) ---
def generar_pdf(df, cliente, empresa, ciudad, inversion, retorno):
    pdf = FPDF()
    pdf.add_page()
    
    # Encabezado
    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, "PROPUESTA DE SISTEMA SOLAR FOTOVOLTAICO", 0, 1, "C")
    pdf.ln(10)
    
    # Datos del Cliente
    pdf.set_font("Arial", "B", 12)
    pdf.cell(100, 10, f"Cliente: {cliente}")
    pdf.cell(100, 10, f"Propuesta: {num_propuesta}", 0, 1, "R")
    pdf.set_font("Arial", "", 11)
    pdf.cell(100, 10, f"Empresa: {empresa}")
    pdf.cell(100, 10, f"Ubicación: {ciudad}", 0, 1, "R")
    pdf.ln(10)
    
    # Resumen Ejecutivo
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "RESUMEN DEL PROYECTO", 0, 1)
    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 8, f"- Inversion Estimada: ${inversion:,.2f}")
    pdf.cell(0, 8, f"- Tiempo de Retorno (Payback): {retorno} años")
    pdf.cell(0, 8, f"- Potencia del Sistema: {pot_sug:.2f} kWp")
    pdf.ln(10)

    # Tabla de Proyeccion (Simplificada para PDF)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(20, 10, "Año", 1)
    pdf.cell(40, 10, "Ind. Degrad.", 1)
    pdf.cell(40, 10, "Prod. kWh", 1)
    pdf.cell(45, 10, "Ahorro Anual $", 1)
    pdf.cell(45, 10, "Acumulado $", 1, 1)
    
    pdf.set_font("Arial", "", 10)
    for index, row in df.head(15).iterrows(): # Primeros 15 años por espacio
        pdf.cell(20, 8, str(row["Año"]), 1)
        pdf.cell(40, 8, str(row["Índice de Degradación"]), 1)
        pdf.cell(40, 8, f"{row['Prod. (kWh/año)']:,.0f}", 1)
        pdf.cell(45, 8, f"{row['Ahorro Total Año']:,.2f}", 1)
        pdf.cell(45, 8, f"{row['Acumulado']:,.2f}", 1, 1)
        
    return pdf.output(dest='S').encode('latin-1')

# Botón de Descarga
pdf_output = generar_pdf(df_proyeccion, nombre_cliente, empresa_cliente, ciudad_sel, costo_planta_total, año_payback)
st.sidebar.download_button(
    label="📩 Descargar Propuesta PDF",
    data=pdf_output,
    file_name=f"Propuesta_{nombre_cliente}.pdf",
    mime="application/pdf"
)
