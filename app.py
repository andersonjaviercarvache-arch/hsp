import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# 1. Configuración de la página
st.set_page_config(page_title="Calculadora HSP Ecuador", page_icon="☀️")

# 2. Base de Datos de Radiación (HSP mensuales aproximadas basadas en Atlas Solar)
# Los valores representan kWh/m2/día (que equivalen a HSP)
data = {
    "Mes": ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"],
    "Guayaquil": [4.2, 4.1, 4.4, 4.6, 4.5, 4.3, 4.6, 5.1, 5.2, 5.0, 4.9, 4.6],
    "Quito": [4.8, 4.6, 4.5, 4.3, 4.4, 4.7, 5.2, 5.5, 5.4, 4.9, 4.6, 4.7],
    "Cuenca": [4.3, 4.2, 4.1, 4.0, 3.9, 3.8, 4.0, 4.4, 4.6, 4.5, 4.5, 4.4],
    "Esmeraldas": [3.7, 3.8, 3.9, 4.0, 4.1, 3.9, 4.0, 4.2, 4.3, 4.1, 4.0, 3.8],
    "Loja": [4.5, 4.4, 4.4, 4.5, 4.3, 4.2, 4.3, 4.8, 5.1, 5.2, 5.1, 4.8],
    "Manta": [4.9, 5.0, 5.2, 5.4, 5.3, 5.1, 5.2, 5.6, 5.8, 5.7, 5.5, 5.2]
}

df_hsp = pd.DataFrame(data)

# 3. Interfaz de Usuario
st.title("☀️ Calculadora de Horas Solar Pico (HSP) - Ecuador")
st.markdown("""
Esta herramienta utiliza datos climáticos promediados para estimar el potencial fotovoltaico 
en ciudades clave de Ecuador. Las **HSP** representan la energía solar recibida si el sol 
brillara a 1000W/m² constantes.
""")

st.sidebar.header("Configuración de la Instalación")
ciudad = st.sidebar.selectbox("Selecciona la Ciudad", df_hsp.columns[1:])
eficiencia = st.sidebar.slider("Eficiencia del Sistema (Factor de Pérdidas)", 0.50, 0.95, 0.80)
potencia_instalada = st.sidebar.number_input("Potencia del Panel/Arreglo (kWp)", min_value=0.1, value=1.0)

# 4. Cálculos
hsp_mensual = df_hsp[ciudad]
hsp_promedio_anual = hsp_mensual.mean()
energia_diaria_estimada = potencia_instalada * hsp_promedio_anual * eficiencia

# 5. Visualización de Resultados
col1, col2 = st.columns(2)

with col1:
    st.metric(label=f"HSP Promedio Anual ({ciudad})", value=f"{hsp_promedio_anual:.2f} h")
with col2:
    st.metric(label="Energía Estimada Diaria", value=f"{energia_diaria_estimada:.2f} kWh/día")

st.subheader(f"Desglose Mensual de Radiación en {ciudad}")

# Gráfico de barras
fig, ax = plt.subplots(figsize=(10, 4))
bars = ax.bar(df_hsp["Mes"], hsp_mensual, color='orange', alpha=0.8)
ax.set_ylabel("HSP (kWh/m²/día)")
ax.set_ylim(0, 7)
ax.axhline(hsp_promedio_anual, color='red', linestyle='--', label='Promedio Anual')
ax.legend()

# Añadir etiquetas de valor sobre las barras
for bar in bars:
    yval = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2, yval + 0.1, yval, ha='center', va='bottom')

st.pyplot(fig)

# Tabla de datos
if st.checkbox("Ver tabla de datos detallada"):
    st.dataframe(df_hsp[["Mes", ciudad]])

st.info("Nota: Los datos son referenciales basados en promedios históricos. Para proyectos reales, se recomienda el uso de archivos .MET o bases de datos PVSYST.")
