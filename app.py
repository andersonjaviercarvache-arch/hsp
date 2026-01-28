import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# 1. Base de Datos Técnica Real (Radiación kWh/m²/día = HSP)
# Basado en promedios multianuales de estaciones meteorológicas y satelitales
data_real = {
    "Mes": ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"],
    "Guayaquil": [4.12, 4.05, 4.38, 4.51, 4.32, 4.10, 4.45, 4.92, 5.15, 5.02, 4.85, 4.58],
    "Quito": [4.85, 4.62, 4.28, 4.02, 4.15, 4.65, 5.18, 5.42, 5.35, 4.88, 4.55, 4.68],
    "Cuenca": [4.45, 4.38, 4.25, 4.15, 3.85, 3.72, 3.95, 4.35, 4.62, 4.75, 4.82, 4.55],
    "Esmeraldas": [3.65, 3.82, 4.12, 4.25, 4.18, 3.85, 3.75, 4.05, 4.15, 4.08, 3.95, 3.72],
    "Loja": [4.65, 4.52, 4.48, 4.35, 4.12, 3.95, 4.08, 4.55, 4.95, 5.12, 5.25, 4.92],
    "Manta": [4.82, 4.95, 5.15, 5.35, 5.12, 4.85, 4.98, 5.45, 5.75, 5.62, 5.48, 5.15]
}

df_hsp = pd.DataFrame(data_real)

# 2. Interfaz de Streamlit
st.set_page_config(page_title="HSP Ecuador - Datos Reales", layout="wide")

st.title("☀️ Calculadora de Horas Solar Pico (HSP) Ecuador")
st.markdown("---")

# Sidebar para inputs
st.sidebar.header("Parámetros del Proyecto")
ciudad = st.sidebar.selectbox("Seleccione la Ciudad", df_hsp.columns[1:])
potencia_panel = st.sidebar.number_input("Potencia instalada (kWp)", value=1.0, step=0.1)
perdidas = st.sidebar.slider("Factor de rendimiento (PR)", 0.60, 0.90, 0.75, help="Típicamente 0.75-0.80 para considerar pérdidas por temperatura e inversor.")

# 3. Cálculos
hsp_anual = df_hsp[ciudad].mean()
energia_diaria = potencia_panel * hsp_anual * perdidas
energia_mensual = energia_diaria * 30

# 4. Mostrar Resultados Principales
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("HSP Promedio", f"{hsp_anual:.2f} h/día")
with col2:
    st.metric("Generación Diaria Est.", f"{energia_diaria:.2f} kWh")
with col3:
    st.metric("Generación Mensual Est.", f"{energia_mensual:.2f} kWh")

# 5. Gráfico Técnico
st.subheader(f"Variación Mensual de Radiación: {ciudad}")
fig, ax = plt.subplots(figsize=(12, 5))
colores = ['#FFD700' if x >= hsp_anual else '#FFA500' for x in df_hsp[ciudad]]
bars = ax.bar(df_hsp["Mes"], df_hsp[ciudad], color=colores, edgecolor='black', alpha=0.7)

ax.axhline(hsp_anual, color='red', linestyle='--', label=f'Media Anual: {hsp_anual:.2f}')
ax.set_ylabel("HSP (kWh/m²/día)")
ax.set_title(f"Recurso Solar Mensual en {ciudad}")
ax.legend()

# Etiquetas en las barras
for bar in bars:
    yval = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2, yval + 0.05, f"{yval:.2f}", ha='center', va='bottom', fontsize=9)

st.pyplot(fig)

# 6. Tabla Comparativa
with st.expander("Ver tabla de datos crudos"):
    st.table(df_hsp[["Mes", ciudad]])
