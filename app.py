import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# 1. Base de Datos Técnica Real Actualizada (HSP = kWh/m²/día)
# Se incluye Quinindé basado en datos del Atlas Solar y registros regionales.
data_real = {
    "Mes": ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"],
    "Guayaquil": [4.12, 4.05, 4.38, 4.51, 4.32, 4.10, 4.45, 4.92, 5.15, 5.02, 4.85, 4.58],
    "Durán": [4.08, 3.98, 4.35, 4.48, 4.28, 4.05, 4.40, 4.88, 5.10, 5.05, 4.90, 4.62],
    "Quito": [4.85, 4.62, 4.28, 4.02, 4.15, 4.65, 5.18, 5.42, 5.35, 4.88, 4.55, 4.68],
    "Cuenca": [4.45, 4.38, 4.25, 4.15, 3.85, 3.72, 3.95, 4.35, 4.62, 4.75, 4.82, 4.55],
    "Esmeraldas": [3.65, 3.82, 4.12, 4.25, 4.18, 3.85, 3.75, 4.05, 4.15, 4.08, 3.95, 3.72],
    "Quinindé": [3.55, 3.68, 3.92, 4.10, 4.05, 3.78, 3.65, 3.95, 4.08, 4.02, 3.92, 3.62],
    "Santo Domingo": [3.45, 3.55, 3.85, 4.02, 3.95, 3.62, 3.58, 3.82, 3.95, 3.92, 3.88, 3.55],
    "Loja": [4.65, 4.52, 4.48, 4.35, 4.12, 3.95, 4.08, 4.55, 4.95, 5.12, 5.25, 4.92],
    "Manta": [4.82, 4.95, 5.15, 5.35, 5.12, 4.85, 4.98, 5.45, 5.75, 5.62, 5.48, 5.15]
}

df_hsp = pd.DataFrame(data_real)

# 2. Configuración de la App
st.set_page_config(page_title="Calculadora Solar Ecuador Pro", layout="wide")
st.title("☀️ Sistema de Cálculo Fotovoltaico: Ecuador")
st.markdown("---")

# 3. Panel de Control (Sidebar)
st.sidebar.header("Parámetros de Diseño")
ciudad = st.sidebar.selectbox("Seleccione la Ubicación", df_hsp.columns[1:])
potencia_sistema = st.sidebar.number_input("Potencia de los Paneles (kWp)", value=5.0, step=0.5)
factor_perdidas = st.sidebar.slider("Factor de Rendimiento (PR)", 0.65, 0.90, 0.78, 
                                   help="Considera pérdidas por calor, cables e inversor. 0.78 es un estándar conservador.")

# 4. Cálculos Energéticos
hsp_promedio = df_hsp[ciudad].mean()
gen_diaria = potencia_sistema * hsp_promedio * factor_perdidas
gen_mensual = gen_diaria * 30.44

# 5. Despliegue de Resultados
col1, col2, col3 = st.columns(3)
col1.metric(f"HSP Promedio en {ciudad}", f"{hsp_promedio:.2f} h/día")
col2.metric("Generación Diaria Media", f"{gen_diaria:.2f} kWh")
col3.metric("Generación Mensual Est.", f"{gen_mensual:.2f} kWh")

# 6. Visualización Gráfica
st.subheader(f"Disponibilidad de Recurso Solar Mensual: {ciudad}")
fig, ax = plt.subplots(figsize=(12, 5))
ax.plot(df_hsp["Mes"], df_hsp[ciudad], marker='o', linestyle='-', color='#e67e22', linewidth=3, label="HSP Mensual")
ax.fill_between(df_hsp["Mes"], df_hsp[ciudad], color='#f39c12', alpha=0.3)
ax.axhline(hsp_promedio, color='red', linestyle='--', label=f'Promedio: {hsp_promedio:.2f}')

ax.set_ylim(0, 6.5)
ax.set_ylabel("HSP (kWh/m²/día)")
ax.set_title(f"Curva de Radiación en {ciudad}")
ax.grid(True, axis='y', alpha=0.3)
ax.legend()

st.pyplot(fig)

# 7. Información Técnica Relevante
with st.expander("ℹ️ Nota sobre Quinindé"):
    st.write("""
    **Quinindé** presenta un reto técnico interesante: aunque está cerca de la línea ecuatorial, la **nubosidad orográfica** (nubes que se forman por la humedad del Chocó) reduce las HSP promedio a aproximadamente **3.86 h/día**. 
    En proyectos para esta zona, se recomienda sobredimensionar el arreglo fotovoltaico en un 15% comparado con ciudades como Manta.
    """)
