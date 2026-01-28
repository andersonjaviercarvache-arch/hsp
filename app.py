import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# 1. Base de Datos Técnica Real Actualizada
# Valores en kWh/m²/día (HSP)
data_real = {
    "Mes": ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"],
    "Guayaquil": [4.12, 4.05, 4.38, 4.51, 4.32, 4.10, 4.45, 4.92, 5.15, 5.02, 4.85, 4.58],
    "Durán": [4.08, 3.98, 4.35, 4.48, 4.28, 4.05, 4.40, 4.88, 5.10, 5.05, 4.90, 4.62],
    "Quito": [4.85, 4.62, 4.28, 4.02, 4.15, 4.65, 5.18, 5.42, 5.35, 4.88, 4.55, 4.68],
    "Cuenca": [4.45, 4.38, 4.25, 4.15, 3.85, 3.72, 3.95, 4.35, 4.62, 4.75, 4.82, 4.55],
    "Esmeraldas": [3.65, 3.82, 4.12, 4.25, 4.18, 3.85, 3.75, 4.05, 4.15, 4.08, 3.95, 3.72],
    "Santo Domingo": [3.45, 3.55, 3.85, 4.02, 3.95, 3.62, 3.58, 3.82, 3.95, 3.92, 3.88, 3.55],
    "Loja": [4.65, 4.52, 4.48, 4.35, 4.12, 3.95, 4.08, 4.55, 4.95, 5.12, 5.25, 4.92],
    "Manta": [4.82, 4.95, 5.15, 5.35, 5.12, 4.85, 4.98, 5.45, 5.75, 5.62, 5.48, 5.15]
}

df_hsp = pd.DataFrame(data_real)

# 2. Configuración de Interfaz
st.set_page_config(page_title="HSP Ecuador Avanzado", layout="wide")
st.title("☀️ Calculadora de Potencial Solar: Ecuador")
st.markdown("---")

# 3. Sidebar
st.sidebar.header("Configuración")
ciudad = st.sidebar.selectbox("Seleccione la Ciudad", df_hsp.columns[1:])
potencia_panel = st.sidebar.number_input("Capacidad del Sistema (kWp)", value=1.0, min_value=0.1)
pr = st.sidebar.slider("Performance Ratio (Eficiencia Real)", 0.60, 0.95, 0.77)

# 4. Cálculos Técnicos
hsp_anual = df_hsp[ciudad].mean()
energia_diaria = potencia_panel * hsp_anual * pr
energia_anual = energia_diaria * 365

# 5. Visualización de Kpis
c1, c2, c3 = st.columns(3)
c1.metric(f"HSP Promedio {ciudad}", f"{hsp_anual:.2f} h")
c2.metric("Gen. Diaria Estimada", f"{energia_diaria:.2f} kWh")
c3.metric("Gen. Anual Estimada", f"{energia_anual:.0f} kWh")

# 6. Gráfico de Barras Mensual
st.subheader(f"Análisis Mensual del Recurso Solar en {ciudad}")
fig, ax = plt.subplots(figsize=(10, 4))
ax.bar(df_hsp["Mes"], df_hsp[ciudad], color='#f39c12', alpha=0.8, edgecolor='black')
ax.axhline(hsp_anual, color='red', linestyle='--', label='Promedio Anual')
ax.set_ylabel("HSP (kWh/m²/día)")
ax.legend()
st.pyplot(fig)

# 7. Comparativa de todas las ciudades
if st.checkbox("Comparar todas las ciudades"):
    st.subheader("HSP Promedio Anual por Ciudad")
    comparativa = df_hsp.mean(numeric_only=True).sort_values(ascending=False)
    st.bar_chart(comparativa)
