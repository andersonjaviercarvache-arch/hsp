import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from fpdf import FPDF
import tempfile
import os

# ... (Base de datos y configuración inicial igual al código anterior)

# --- DENTRO DE LA LÓGICA DE CÁLCULO ---
# Asegúrate de tener estas listas para graficar
años_lista = list(range(1, 26))
flujo_anual = []
acumulados_lista = []
suma_fin = 0

for i in años_lista:
    rend = (1 - deg_año1) * ((1 - atenuacion_anual)**(i-1)) if i > 1 else (1 - deg_año1)
    total_año = (gen_anual_inicial * rend * costo_kwh) + (ahorro_trib_anual if i <= 10 else 0)
    suma_fin += total_año
    flujo_anual.append(total_año)
    acumulados_lista.append(suma_fin)

# --- FUNCIÓN PDF ACTUALIZADA ---
def crear_pdf_con_flujo():
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # PÁGINA 1: RESUMEN Y GRÁFICOS
    pdf.add_page()
    pdf.set_fill_color(31, 119, 180); pdf.rect(0, 0, 210, 35, 'F')
    pdf.set_text_color(255, 255, 255); pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 15, 'ESTUDIO FINANCIERO Y FLUJO DE CAJA', 0, 1, 'C')
    
    pdf.set_text_color(0, 0, 0); pdf.ln(25)
    pdf.set_font('Arial', 'B', 12); pdf.cell(0, 10, '1. PROYECTO DE FLUJO DE CAJA ANUAL', 0, 1)
    
    # GRÁFICO 1: Barras de Flujo Anual
    fig1, ax1 = plt.subplots(figsize=(8, 3.5))
    ax1.bar(años_lista, flujo_anual, color='#2ecc71', label='Ahorro + Beneficio')
    ax1.set_title("Ingresos Anuales Proyectados (USD)")
    ax1.grid(axis='y', alpha=0.3)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp1:
        fig1.savefig(tmp1.name, format='png', dpi=150, bbox_inches='tight')
        pdf.image(tmp1.name, x=15, w=180)
        path1 = tmp1.name

    pdf.ln(5)
    pdf.set_font('Arial', 'B', 12); pdf.cell(0, 10, '2. RETORNO DE INVERSIÓN ACUMULADO', 0, 1)

    # GRÁFICO 2: Línea de Acumulado con Sombreado de Ganancia
    fig2, ax2 = plt.subplots(figsize=(8, 3.5))
    ax2.plot(años_lista, acumulados_lista, color='#1f77b4', linewidth=2, label='Flujo Acumulado')
    ax2.axhline(y=costo_planta_total, color='red', linestyle='--', label='Inversión Inicial')
    ax2.fill_between(años_lista, acumulados_lista, costo_planta_total, 
                     where=(np.array(acumulados_lista) >= costo_planta_total), 
                     color='green', alpha=0.2, label='Ganancia Neta')
    ax2.set_title("Punto de Equilibrio y Utilidad Neta")
    ax2.legend(loc='upper left')
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp2:
        fig2.savefig(tmp2.name, format='png', dpi=150, bbox_inches='tight')
        pdf.image(tmp2.name, x=15, w=180)
        path2 = tmp2.name

    # PÁGINA 2: TABLA DE DATOS
    pdf.add_page()
    pdf.set_font('Arial', 'B', 11); pdf.cell(0, 10, 'DETALLE CRONOLÓGICO DE FLUJO', 0, 1)
    # ... (Aquí va el código de la tabla que ya tienes)

    res = pdf.output(dest='S').encode('latin-1')
    os.remove(path1); os.remove(path2)
    return res

# Botón de descarga
st.sidebar.download_button("📥 Descargar Reporte Financiero", 
                          data=crear_pdf_con_flujo(), 
                          file_name=f"Flujo_Caja_{nombre_cliente}.pdf")
