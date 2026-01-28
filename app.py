import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# 1. Base de Datos Técnica
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

st.set_page_config(page_title="HSP Ecuador - Sugerencia de Potencia", layout="wide")

st.title("☀️ Dimensionamiento Fotovoltaico por Consumo - Ecuador")
st.markdown("---")

# 2. Sidebar con Consumo y Costo
st.sidebar.header("⚙️ Datos del Usuario")
lista_ciudades = [c for c in ciudades_data.keys() if c != "Mes"]
ciudad_sel = st.sidebar.selectbox("Seleccione la Ciudad", lista_ciudades)

# CAMBIO: Ahora el usuario ingresa su consumo mensual
consumo_mensual_objetivo = st.sidebar.number_input("Consumo Mensual (kWh/mes)", value=300.0, step=10.0, min_value=0.0)

st.sidebar.header("💰 Costos Eléctricos")
costo_kwh = st.sidebar.number_input("Valor por kWh (USD)", value=0.0920, format="%.4f", step=0.0001)

# 3. Lógica Técnica y Sugerencia de Potencia
temp_ciudad = ciudades_data[ciudad_sel]["temp"]
pr_ajustado = 0.82 - ((max(0, temp_ciudad - 15)) * 0.0045)
hsp_lista = ciudades_data[ciudad_sel]["hsp"]
hsp_promedio = sum(hsp_lista) / len(hsp_lista)

# Cálculo de Potencia Sugerida (kWp)
# Fórmula: Potencia = Consumo_Mensual / (HSP * PR * 30.44)
if consumo_mensual_objetivo > 0:
    potencia_sugerida = consumo_mensual_objetivo / (hsp_promedio * pr_ajustado * 30.44)
else:
    potencia_sugerida = 0.0

# Re-calculamos la generación diaria y mensual basada en la potencia sugerida
gen_diaria = potencia_sugerida * hsp_promedio * pr_ajustado
gen_mensual = gen_diaria * 30.44
ahorro_mensual = gen_mensual * costo_kwh

# 4. Dashboard de Indicadores Principales
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Horas Solar Pico (HSP)", f"{hsp_promedio:.2f} h")
with col2:
    st.metric("Potencia Sugerida", f"{potencia_sugerida:.2f} kWp", delta="Recomendado")
with col3:
    st.metric("Gen. Diaria Est.", f"{gen_diaria:.2f} kWh")
with col4:
    st.metric("Ahorro Mensual Est.", f"${ahorro_mensual:.2f}")

st.markdown("---")

# 5. Sección de Análisis Gráfico
col_graf, col_info = st.columns([2, 1])

with col_graf:
    st.subheader(f"Producción Mensual Sugerida para cubrir {consumo_mensual_objetivo} kWh")
    gen_mes_a_mes = [potencia_sugerida * h * pr_ajustado * 30.44 for h in hsp_lista]
    
    fig, ax = plt.subplots(figsize=(10, 4))
    bars = ax.bar(ciudades_data["Mes"], gen_mes_a_mes, color="#1abc9c", edgecolor="black", alpha=0.8)
    ax.axhline(consumo_mensual_objetivo, color='red', linestyle='--', label='Consumo Objetivo')
    ax.set_ylabel("Energía Generada (kWh)")
    ax.legend()
    st.pyplot(fig)

with col_info:
    st.subheader("Ficha de Dimensionamiento")
    # Ejemplo de cálculo de paneles (asumiendo paneles de 550W)
    num_paneles = int((potencia_sugerida * 1000) / 550) + 1 if potencia_sugerida > 0 else 0
    
    st.info(f"""
    **Para {ciudad_sel}:**
    - **Potencia necesaria:** {potencia_sugerida:.2f} kWp.
    - **Est. de paneles:** {num_paneles} paneles de 550W.
    - **Ahorro Anual:** ${ahorro_mensual * 12:.2f}
    - **Eficiencia Local (PR):** {pr_ajustado:.1%}
    """)
    st.write("La potencia sugerida cubre el 100% de su consumo mensual promedio.")

# 6. Tabla Detallada
with st.expander("📂 Ver Desglose Técnico Mensual"):
    df_detalle = pd.DataFrame({
        "Mes": ciudades_data["Mes"],
        "Radiación (HSP)": hsp_lista,
        "Generación Diaria (kWh)": [round(potencia_sugerida * h * pr_ajustado, 2) for h in hsp_lista],
        "Generación Mensual (kWh)": [round(g, 2) for g in gen_mes_a_mes],
        "Ahorro Estimado (USD)": [round(g * costo_kwh, 2) for g in gen_mes_a_mes]
    })
    st.dataframe(df_detalle, use_container_width=True)
    
