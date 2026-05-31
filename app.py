import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
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

st.set_page_config(page_title="Latitud Solar - Generador de Propuestas", layout="wide")

if 'costo_kwp' not in st.session_state:
    st.session_state.costo_kwp = 850.0

# --- SIDEBAR ---
st.sidebar.header("📋 Información del Cliente")
nombre_cliente = st.sidebar.text_input("Nombre del Cliente", "Martillo Jara Angel Cristobal")
n_proyecto = st.sidebar.text_input("Número de Proyecto", "P0000000010")
tipo_proyecto = st.sidebar.selectbox("Tipo de Proyecto", ["Residencial", "Comercial"])
vendedor = st.sidebar.text_input("Asesor Comercial", "Ing. Solar")

st.title("☀️ Sistema de Simulación Fotovoltaica - Latitud Solar")

# --- BLOQUE 1: PARÁMETROS TÉCNICOS ---
with st.container():
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        ciudad_sel = st.selectbox("📍 Ubicación", list(ciudades_data.keys()))
    with col2:
        consumo_mensual = st.number_input("⚡ Consumo (kWh/mes)", value=1228.0)
    with col3:
        pago_planilla = st.number_input("💵 Planilla USD/mes", value=149.94)
        costo_kwh = pago_planilla / consumo_mensual if consumo_mensual > 0 else 0
    with col4:
        deg_y1 = st.number_input("📉 Deg. Año 1 (%)", value=2.0) / 100
    with col5:
        atenuacion = st.number_input("📉 Aten. Anual (%)", value=0.55) / 100

hsp_avg = sum(ciudades_data[ciudad_sel]["hsp"]) / 12
temp_prom = ciudades_data[ciudad_sel]["temp"]
pr_calculado = 0.82 - (max(0, temp_prom - 15) * 0.0045)
potencia_sug = consumo_mensual / (hsp_avg * pr_calculado * 30.44)
generacion_y1 = potencia_sug * hsp_avg * pr_calculado * 365

with st.expander("🔍 Análisis Meteorológico y Técnico", expanded=True):
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Potencia Sugerida", f"{potencia_sug:.2f} kWp")
    m2.metric("HSP Promedio", f"{hsp_avg:.2f} h/día")
    m3.metric("Eficiencia (PR)", f"{pr_calculado:.2%}")
    m4.metric("Costo kWh", f"${costo_kwh:.4f}")

# --- BLOQUE 2: INVERSIÓN Y AHORRO TRIBUTARIO ---
st.subheader("💰 Inversión y Beneficios")
def sync_kwp(): st.session_state.inv_total = st.session_state.costo_kwp * potencia_sug
def sync_inv(): st.session_state.costo_kwp = st.session_state.inv_total / potencia_sug if potencia_sug > 0 else 0

c_inv1, c_inv2, c_inv3 = st.columns(3)
with c_inv1:
    st.number_input("Inversión Total (USD)", key="inv_total", on_change=sync_inv)
with c_inv2:
    st.number_input("Costo por kWp (USD)", key="costo_kwp", on_change=sync_kwp)
with c_inv3:
    tasa_incentivo = 0.10 if tipo_proyecto == "Comercial" else 0.0
    st.info(f"Beneficio Tributario: {tasa_incentivo:.0%} anual")

# --- BLOQUE 3: FLUJO DE CAJA ---
inv_final = st.session_state.inv_total
ahorro_trib_anual = inv_final * tasa_incentivo
data_rows, años, acumulados = [], [], []
balance_acumulado, payback_year = 0, None

# CAMBIO AQUÍ: range(1, 31) en lugar de range(1, 26) para 30 años
for año in range(1, 31):
    factor_deg = (1 - deg_y1) * ((1 - atenuacion)**(año-1)) if año > 1 else (1 - deg_y1)
    prod_anual = generacion_y1 * factor_deg
    ahorro_energetico = prod_anual * costo_kwh
    beneficio_extra = ahorro_trib_anual if año <= 10 else 0
    total_año = ahorro_energetico + beneficio_extra
    balance_acumulado += total_año
    if balance_acumulado >= inv_final and payback_year is None: payback_year = año
    
    años.append(año); acumulados.append(balance_acumulado)
    data_rows.append({
        "Año": año, "Ind. Deg.": f"-{factor_deg:.3f}", "Prod. kWh": f"{prod_anual:,.0f}",
        "Ahorro Energía": f"${ahorro_energetico:,.2f}", "Ahorro Trib.": f"${beneficio_extra:,.2f}",
        "Ahorro Año": f"${total_año:,.2f}", "Acumulado": f"${balance_acumulado:,.2f}"
    })

# Tabla en la App
st.subheader("📊 Tabla de Proyección")
st.dataframe(pd.DataFrame(data_rows), use_container_width=True)

# --- NUEVO: GRÁFICO EN LA APP ---
st.subheader("📈 Análisis de Retorno de Inversión")
plt.style.use('ggplot')
fig_app, ax_app = plt.subplots(figsize=(10, 5))
ax_app.plot(años, acumulados, color='#1f77b4', marker='o', linewidth=2, label='Ahorro Acumulado')
ax_app.axhline(y=inv_final, color='#e74c3c', linestyle='--', linewidth=2, label='Inversión Inicial')
ax_app.fill_between(años, acumulados, inv_final, where=(pd.Series(acumulados) >= inv_final), 
                interpolate=True, color='green', alpha=0.2, label='Ganancia Neta')
ax_app.fill_between(años, acumulados, inv_final, where=(pd.Series(acumulados) < inv_final), 
                interpolate=True, color='red', alpha=0.1, label='Periodo de Recuperación')

if payback_year:
    ax_app.plot(payback_year, inv_final, marker='*', markersize=15, color='#f1c40f', label='Punto de Equilibrio')
    ax_app.annotate(f'Año {payback_year}', xy=(payback_year, inv_final), xytext=(payback_year, inv_final*1.1),
                    fontweight='bold', color='#2c3e50')

ax_app.set_ylabel("Dólares (USD)")
ax_app.set_xlabel("Años")
ax_app.yaxis.set_major_formatter(mtick.StrMethodFormatter('${x:,.0f}'))
ax_app.legend(loc='upper left')
st.pyplot(fig_app)


# --- FUNCIÓN PDF ---
def generar_pdf():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_margins(15, 15, 15)
    
    if os.path.exists("Negro sobre blanco (1).png"):
        pdf.image("Negro sobre blanco (1).png", x=15, y=10, w=45)
    else:
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(50, 10, 'Latitud Solar', 0, 0, 'L')
    
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(0, 5, 'LATITUD SOLAR C.LTDA.', 0, 1, 'R')
    pdf.set_font('Arial', '', 8)
    pdf.set_x(110)
    pdf.cell(0, 5, 'RUC   0993403111001', 0, 1, 'R')
    pdf.set_x(110)
    pdf.cell(0, 5, 'TELEFONOS:  0969952794-0959032257', 0, 1, 'R')
    
    pdf.ln(10); pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, f'PROPUESTA SOLAR - {tipo_proyecto.upper()}', 0, 1, 'C')
    pdf.set_draw_color(31, 119, 180); pdf.set_line_width(0.8)
    pdf.line(40, pdf.get_y(), 170, pdf.get_y())
    
    pdf.ln(12); pdf.set_font('Arial', 'B', 10); pdf.cell(0, 10, 'DATOS DEL PROYECTO', 0, 1, 'L')
    pdf.set_font('Arial', '', 9)
    pdf.cell(95, 6, f'Cliente: {nombre_cliente}'); pdf.cell(0, 6, f'Ciudad: {ciudad_sel}', 0, 1)
    pdf.cell(95, 6, f'Proyecto: {n_proyecto}'); pdf.cell(0, 6, f'Costo kWh: ${costo_kwh:.4f}', 0, 1)
    
    pdf.ln(8); pdf.set_fill_color(240, 240, 240)
    pdf.set_font('Arial', 'B', 10); pdf.cell(0, 8, 'RESUMEN FINANCIERO', 0, 1, 'L', fill=True)
    pdf.set_font('Arial', '', 9); pdf.ln(2)
    # CAMBIO AQUÍ: de "> 25 años" a "> 30 años"
    retorno_texto = f"{payback_year} años" if payback_year else "> 30 años"
    pdf.cell(95, 6, f'Inversión Total: ${inv_final:,.2f}'); pdf.cell(0, 6, f'Retorno: {retorno_texto}', 0, 1)
    pdf.cell(95, 6, f'Potencia Sugerida: {potencia_sug:.2f} kWp'); pdf.cell(0, 6, f'Planilla Mensual: ${pago_planilla:,.2f}', 0, 1)
    
    pdf.ln(10); pdf.set_fill_color(31, 119, 180); pdf.set_text_color(255, 255, 255); pdf.set_font('Arial', 'B', 9)
    pdf.set_draw_color(50, 50, 50); pdf.set_line_width(0.2)
    cols_w = [15, 25, 35, 35, 35, 40]
    headers = ['Año', 'Ind. Deg.', 'Prod. kWh', 'Ahorro En.', 'Ahorro Trib.', 'Acumulado']
    for i in range(len(headers)): pdf.cell(cols_w[i], 8, headers[i], 1, 0, 'C', fill=True)
    pdf.ln()
    
    pdf.set_text_color(0, 0, 0); pdf.set_font('Arial', '', 8)
    for row in data_rows:
        # Se añade control de salto de página manual para evitar que la tabla de 30 años se corte feo
        if pdf.get_y() > 260:
            pdf.add_page()
            # Reimprimir encabezado si lo deseas, o simplemente continuar
        pdf.cell(cols_w[0], 7, str(row['Año']), 1, 0, 'C')
        pdf.cell(cols_w[1], 7, row['Ind. Deg.'], 1, 0, 'C')
        pdf.cell(cols_w[2], 7, row['Prod. kWh'], 1, 0, 'C')
        pdf.cell(cols_w[3], 7, row['Ahorro Energía'], 1, 0, 'C')
        pdf.cell(cols_w[4], 7, row['Ahorro Trib.'], 1, 0, 'C')
        pdf.cell(cols_w[5], 7, row['Acumulado'], 1, 1, 'C')

    pdf.ln(15)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        plt.savefig(tmp.name, dpi=200, bbox_inches='tight'); plot_p = tmp.name
    
    if pdf.get_y() > 170: pdf.add_page()
    pdf.image(plot_p, x=15, w=180); plt.close(); os.remove(plot_p)
    return pdf.output(dest='S').encode('latin-1')

st.sidebar.download_button("📥 Descargar Propuesta PDF", data=generar_pdf(), file_name=f"Propuesta_{nombre_cliente}.pdf")
