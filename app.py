import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# 1. Base de Datos con Radiación (HSP) y Temperatura Promedio (°C)
# La temperatura influye directamente en el Performance Ratio (PR)
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

st.set_page_config(page_title="HSP Ecuador Inteligente", layout="wide")
st.title("☀️ Calculadora Solar con Ajuste Climático (PR Dinámico)")

# 2. Selección de Ciudad
lista_ciudades = list(ciudades_data.keys())
lista_ciudades.remove("Mes")
ciudad_sel = st.sidebar.selectbox("Seleccione la Ciudad", lista_ciudades)
potencia_kwp = st.sidebar.number_input("Potencia Instalada (kWp)", value=1.0)

# 3. Lógica de Ajuste de Rendimiento (PR)
# El PR base es 0.80 a 25°C. Se resta 0.004 (0.4%) por cada grado arriba de 25°C.
temp_base = 25.0
temp_ciudad = ciudades_data[ciudad_sel]["temp"]
coef_temp = 0.004  # Pérdida típica por grado Celsius

# Cálculo del PR ajustado
pr_ajustado = 0.82 - ((max(0, temp_ciudad - 15)) * coef_temp) 
# Nota: En ciudades frías (15°C) el PR sube, en calurosas baja.

# 4. Cálculos finales
hsp_lista = ciudades_data[ciudad_sel]["hsp"]
hsp_promedio = sum(hsp_lista) / len(hsp_lista)
gen_diaria = potencia_kwp * hsp_promedio * pr_ajustado

# 5. Interfaz
col1, col2, col3 = st.columns(3)
col1.metric("HSP Promedio", f"{hsp_promedio:.2f} h")
col2.metric("PR Ajustado (Clima)", f"{pr_ajustado:.2%}", 
           delta=f"{pr_ajustado - 0.75:.2%}", delta_color="normal")
col3.metric("Generación Diaria", f"{gen_diaria:.2f} kWh")

st.info(f"💡 **Análisis Térmico:** En {ciudad_sel}, la temperatura promedio es de {temp_ciudad}°C. "
        f"El sistema ha calculado un Performance Ratio de {pr_ajustado:.2%} considerando las pérdidas por calor.")

# 6. Gráfico
fig, ax = plt.subplots(figsize=(10, 4))
ax.bar(ciudades_data["Mes"], hsp_lista, color="#f1c40f", edgecolor="black")
ax.set_ylabel("HSP (kWh/m²/día)")
ax.set_title(f"Recurso Solar Mensual en {ciudad_sel}")
st.pyplot(fig)
