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
    años_beneficio = st.number_input("Años a Aplicar el Beneficio Tributario", min_value=1, max_value=10, value=2, step=1)
    
    if tipo_proyecto == "Comercial":
        porcentaje_distribucion = 100.0 / años_beneficio
        st.info(f"Beneficio: **{porcentaje_distribucion:.2f}%** anual de la Inversión Total por {años_beneficio} año(s).")
    else:
        porcentaje_distribucion = 0.0
        st.info("El beneficio tributario aplica únicamente para proyectos Comerciales.")

# --- BLOQUE 3: FLUJO DE CAJA Y CÁLCULO DE RETORNO ---
inv_final = st.session_state.inv_total
ahorro_trib_anual_usd = inv_final * (porcentaje_distribucion / 100.0)

data_rows, años, acumulados = [], [], []
balance_acumulado = 0
payback_exacto = None

for año in range(1, 31):
    factor_deg = (1 - deg_y1) * ((1 - atenuacion)**(año-1)) if año > 1 else (1 - deg_y1)
    prod_anual = generacion_y1 * factor_deg
    ahorro_energetico = prod_anual * costo_kwh
    
    # Aplicar el beneficio en USD de acuerdo a la cantidad de años seleccionada
    beneficio_extra = ahorro_trib_anual_usd if (año <= años_beneficio and tipo_proyecto == "Comercial") else 0
    
    # SUMA DE AMBOS AHORROS
    total_año = ahorro_energetico + beneficio_extra
    
    # Cálculo exacto fraccional del Retorno de Inversión
    if payback_exacto is None and (balance_acumulado + total_año) >= inv_final:
        remand_por_recuperar = inv_final - balance_acumulado
        payback_exacto = (año - 1) + (remand_por_recuperar / total_año)
    
    balance_acumulado += total_año
    años.append(año)
    acumulados.append(balance_acumulado)
    
    data_rows.append({
        "Año": año, "Ind. Deg.": f"-{factor_deg:.3f}", "Prod. kWh": f"{prod_anual:,.0f}",
        "Ahorro Energía": f"${ahorro_energetico:,.2f}", "Ahorro Trib.": f"${beneficio_extra:,.2f}",
        "Ahorro Año": f"${total_año:,.2f}", "Acumulado": f"${balance_acumulado:,.2f}"
    })

# --- BLOQUE DE MÉTRICAS INDICADORAS ---
with st.container():
    st.markdown("### 📊 Análisis de Retorno de Inversión")
    r1, r2, r3 = st.columns(3)
    
    ahorro_en_y1 = generacion_y1 * (1 - deg_y1) * costo_kwh
    benef_trib_y1 = ahorro_trib_anual_usd if tipo_proyecto == "Comercial" else 0
    
    r1.metric("Ahorro Año 1 (Suma de Ambos)", f"${(ahorro_en_y1 + benef_trib_y1):,.2f}")
    r2.metric("Inversión a Recuperar", f"${inv_final:,.2f}")
    
    # Muestra el resultado dinámico exacto de cuándo se recuperará la inversión
    if payback_exacto:
        if payback_exacto < 1:
            meses = round(payback_exacto * 12)
            texto_retorno = f"{payback_exacto:.2f} años (~ {meses} meses)"
        else:
            texto_retorno = f"{payback_exacto:.2f} años"
    else:
        texto_retorno = "> 30 años"
        
    r3.metric("⏱️ Tiempo de Recuperación Real", texto_retorno)

# Tabla en la App
st.subheader("📊 Tabla de Proyección")
st.dataframe(pd.DataFrame(data_rows), use_container_width=True)

# --- GRÁFICO MEJORADO ---
st.subheader("📈 Gráfico de Recuperación de Capital")
plt.style.use('ggplot')
fig_app, ax_app = plt.subplots(figsize=(10, 5))

plot_años = [0] + años
plot_acumulados = [0] + acumulados

años_ser = pd.Series(plot_años)
acumulados_ser = pd.Series(plot_acumulados)

ax_app.plot(años_ser, acumulados_ser, color='#1f77b4', marker='o', linewidth=2, label='Ahorro Acumulado (Energía + Tributario)')
ax_app.axhline(y=inv_final, color='#e74c3c', linestyle='--', linewidth=2, label='Línea de Inversión')

ax_app.fill_between(años_ser, acumulados_ser, inv_final, where=(acumulados_ser >= inv_final), 
                interpolate=True, color='green', alpha=0.2, label='Ganancia Neta')
ax_app.fill_between(años_ser, acumulados_ser, inv_final, where=(acumulados_ser < inv_final), 
                interpolate=True, color='red', alpha=0.1, label='Periodo de Recuperación')

if tipo_proyecto == "Comercial" and años_beneficio > 0:
    ax_app.axvspan(0, años_beneficio, color='#f1c40f', alpha=0.12, 
                   label=f'Incentivo Tributario Activo ({años_beneficio} añ.)')

if payback_exacto:
    ax_app.plot(payback_exacto, inv_final, marker='*', markersize=15, color='#f1c40f', label=f'Punto de Equilibrio: {payback_exacto:.2f} años')
    ax_app.annotate(f'Retorno: {payback_exacto:.2f} años', xy=(payback_exacto, inv_final), xytext=(payback_exacto, inv_final * 1.15),
                    fontweight='bold', color='#2c3e50', arrowprops=dict(facecolor='#2c3e50', shrink=0.08, width=1, headwidth=6))

ax_app.set_ylabel("Dólares (USD)")
ax_app.set_xlabel("Años")
ax_app.set_xlim(0, 30.5)
ax_app.yaxis.set_major_formatter(mtick.StrMethodFormatter('${x:,.0f}'))
ax_app.legend(loc='upper left')
st.pyplot(fig_app)


# --- FUNCIÓN PDF ---
def generar_pdf():
    def to_latin1(texto):
        return str(texto).encode('latin-1', 'replace').decode('latin-1')

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
    pdf.cell(0, 10, to_latin1(f'PROPUESTA SOLAR - {tipo_proyecto.upper()}'), 0, 1, 'C')
    pdf.set_draw_color(31, 119, 180); pdf.set_line_width(0.8)
    pdf.line(40, pdf.get_y(), 170, pdf.get_y())
    
    pdf.ln(12); pdf.set_font('Arial', 'B', 10); pdf.cell(0, 10, 'DATOS DEL PROYECTO', 0, 1, 'L')
    pdf.set_font('Arial', '', 9)
    pdf.cell(95, 6, to_latin1(f'Cliente: {nombre_cliente}')); pdf.cell(0, 6, to_latin1(f'Ciudad: {ciudad_sel}'), 0, 1)
    pdf.cell(95, 6, to_latin1(f'Proyecto: {n_proyecto}')); pdf.cell(0, 6, to_latin1(f'Costo kWh: ${costo_kwh:.4f}'), 0, 1)
    
    pdf.ln(8); pdf.set_fill_color(240, 240, 240)
    pdf.set_font('Arial', 'B', 10); pdf.cell(0, 8, to_latin1('RESUMEN FINANCIERO DE RECUPERACIÓN'), 0, 1, 'L', fill=True)
    pdf.set_font('Arial', '', 9); pdf.ln(2)
    pdf.cell(95, 6, to_latin1(f'Inversión Total: ${inv_final:,.2f}')); pdf.cell(0, 6, to_latin1(f'Retorno Estimado Real: {texto_retorno}'), 0, 1)
    pdf.cell(95, 6, to_latin1(f'Potencia Sugerida: {potencia_sug:.2f} kWp')); pdf.cell(0, 6, to_latin1(f'Esquema Beneficio: {porcentaje_distribucion:.2f}% por {años_beneficio} año(s)'), 0, 1)
    
    # --- CUADRO DE TEXTO DESTACADO DENTRO DEL PDF ---
    pdf.ln(6)
    
    # Configuramos los colores del cuadro (Fondo azul claro, texto azul oscuro)
    pdf.set_fill_color(235, 245, 255)
    pdf.set_text_color(0, 50, 100)
    pdf.set_font('Arial', 'I', 9)
    
    if payback_exacto:
        texto_explicativo = (
            f"El retorno de inversión será de {texto_retorno} como resultado de la sumatoria "
            f"del ahorro anual energético y el ahorro anual tributario aplicado a {años_beneficio} año(s). "
            f"A partir de este punto, el sistema pasa a generar un saldo a favor totalmente neto para el cliente "
            f"durante el resto de su vida útil."
        )
    else:
        texto_explicativo = (
            "Con los parámetros de consumo e inversión actuales, el proyecto no alcanza su punto de "
            "equilibrio dentro de los primeros 30 años proyectados."
        )
    
    # Esta línea imprime visualmente el texto como un bloque/cuadro de color en el PDF
    pdf.multi_cell(0, 6, to_latin1(texto_explicativo), border=0, align='C', fill=True)
    
    # Restauramos los colores a negro y blanco para el resto del documento
    pdf.set_text_color(0, 0, 0)
    # ------------------------------------------

    pdf.ln(8); pdf.set_fill_color(31, 119, 180); pdf.set_text_color(255, 255, 255); pdf.set_font('Arial', 'B', 9)
    pdf.set_draw_color(50, 50, 50); pdf.set_line_width(0.2)
    cols_w = [15, 25, 35, 35, 35, 40]
    headers = ['Año', 'Ind. Deg.', 'Prod. kWh', 'Ahorro En.', 'Ahorro Trib.', 'Acumulado']
    
    for i in range(len(headers)): 
        pdf.cell(cols_w[i], 8, to_latin1(headers[i]), 1, 0, 'C', fill=True)
    pdf.ln()
    
    pdf.set_text_color(0, 0, 0); pdf.set_font('Arial', '', 8)
    for row in data_rows:
        if pdf.get_y() > 260:
            pdf.add_page()
        pdf.cell(cols_w[0], 7, to_latin1(str(row['Año'])), 1, 0, 'C')
        pdf.cell(cols_w[1], 7, to_latin1(row['Ind. Deg.']), 1, 0, 'C')
        pdf.cell(cols_w[2], 7, to_latin1(row['Prod. kWh']), 1, 0, 'C')
        pdf.cell(cols_w[3], 7, to_latin1(row['Ahorro Energía']), 1, 0, 'C')
        pdf.cell(cols_w[4], 7, to_latin1(row['Ahorro Trib.']), 1, 0, 'C')
        pdf.cell(cols_w[5], 7, to_latin1(row['Acumulado']), 1, 1, 'C')

    pdf.ln(15)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        plt.savefig(tmp.name, dpi=200, bbox_inches='tight'); plot_p = tmp.name
    
    if pdf.get_y() > 170: pdf.add_page()
    pdf.image(plot_p, x=15, w=180); plt.close(); os.remove(plot_p)
    
    pdf_out = pdf.output(dest='S')
    if isinstance(pdf_out, str):
        return pdf_out.encode('latin-1', errors='replace')
    return bytes(pdf_out)

st.sidebar.download_button("📥 Descargar Propuesta PDF", data=generar_pdf(), file_name=f"Propuesta_{nombre_cliente}.pdf")
# --- CUADRO DE TEXTO DESTACADO CON TU NUEVA EXPLICACIÓN ---
    pdf.ln(6)
    pdf.set_fill_color(235, 245, 255)
    pdf.set_text_color(0, 50, 100)
    pdf.set_font('Arial', 'I', 9)
    
    # Texto dinámico basado en tus nuevos datos
    texto_explicativo = (
        f"El retorno de inversión será de {texto_retorno}, derivado de la sumatoria del ahorro energético anual "
        f"y el ahorro tributario. Al aplicar una depreciación acelerada del 50% anual durante 2 años sobre una "
        f"inversión de ${inv_final:,.2f}, logramos recuperar el capital inicial en 1.4 años. "
        f"A partir de este punto, el sistema entra en una fase de saldo a favor neto durante el resto de su "
        f"vida útil de 30 años, transformando el ahorro en un flujo de caja positivo constante para su empresa."
    )
    
    pdf.multi_cell(0, 5, to_latin1(texto_explicativo), border=0, align='C', fill=True)
    pdf.set_text_color(0, 0, 0) # Reset color
    # ----------------------------------------------------------
