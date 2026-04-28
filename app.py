import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
import base64

# ... (todo tu código previo) ...

# 7. GENERAR PDF DESCARGABLE
def generar_pdf(ciudad, costo_total, potencia, ahorro_total, año_payback, tabla):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(200, 10, txt="Análisis de Retorno de Inversión Solar", ln=True, align="C")
    pdf.ln(10)

    pdf.cell(200, 10, txt=f"Ciudad: {ciudad}", ln=True)
    pdf.cell(200, 10, txt=f"Inversión Total: ${costo_total:,.2f}", ln=True)
    pdf.cell(200, 10, txt=f"Potencia Sugerida: {potencia:.2f} kWp", ln=True)
    pdf.cell(200, 10, txt=f"Ahorro Total (25 años): ${ahorro_total:,.2f}", ln=True)
    if año_payback:
        pdf.cell(200, 10, txt=f"Payback: {año_payback} años", ln=True)
    else:
        pdf.cell(200, 10, txt="Payback: > 25 años", ln=True)

    pdf.ln(10)
    pdf.cell(200, 10, txt="Proyección de Flujo de Caja:", ln=True)
    pdf.ln(5)

    # Tabla resumida
    for fila in tabla[:10]:  # solo primeras 10 filas para ejemplo
        pdf.cell(200, 10, txt=f"Año {fila['Año']} - Prod: {fila['Prod. (kWh/año)']} - Ahorro: {fila['Ahorro Total Año']}", ln=True)

    return pdf

pdf_obj = generar_pdf(ciudad_sel, costo_planta_total, pot_sug, suma_fin, año_payback, data_tabla)

# Convertir a base64 para descarga
pdf_bytes = pdf_obj.output(dest="S").encode("latin-1")
b64 = base64.b64encode(pdf_bytes).decode("latin-1")
href = f'<a href="data:application/octet-stream;base64,{b64}" download="ROI_Solar_{ciudad_sel}.pdf">📥 Descargar Reporte en PDF</a>'

st.markdown(href, unsafe_allow_html=True)


