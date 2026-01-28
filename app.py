import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# 1. Base de Datos Técnica Real
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

st.set_page_config(page_title="HSP Ecuador Pro", layout="wide")

st.title("☀️ Sistema de Dimensionamiento Solar Fotovoltaico")
st.markdown("### 🛠️ Parámetros del Proyecto")

# 2. SECCIÓN DE ENTRADA DE DATOS (En pantalla principal)
with st.container():
    col_input1, col_input2, col_input3 = st.columns(3)
    
    with col_input1:
        lista_ciudades = [c for c in ciudades_data.keys() if c != "Mes"]
        ciudad_sel = st.selectbox("📍 Seleccione la Ciudad", lista_ciudades)
        
    with col_input2:
        consumo_mensual = st.number_input("⚡ Consumo Mensual (kWh/mes)", value=300.0, step=10.0, min_value=1.0)
        
    with col_input3:
        costo_kwh = st.number_input("💵 Valor por kWh (USD)", value=0.0920, format="%.4f", step=0.0001)

st.markdown("---")

# 3. Lógica Técnica (PR Dinámico y Potencia)
temp_ciudad = ciudades_data[ciudad_sel]["temp"]
pr_ajustado = 0.82 - ((max(0, temp_ciudad - 15)) * 0.0045)
hsp_lista = ciudades_data[ciudad_sel]["hsp"]
hsp_promedio = sum(hsp_lista) / len(hsp_lista)

# Cálculo de Potencia Recomendada
potencia_sugerida = consumo_mensual / (hsp_promedio * pr_ajustado * 30.44)
gen_diaria = potencia_sugerida * hsp_promedio * pr_ajustado
gen_mensual = gen_diaria * 30.44
ahorro_mensual = gen_mensual * costo_kwh

# 4. RESULTADOS (KPIs)
st.subheader("📊 Indicadores de Rendimiento")
col_res1, col_res2, col_res3, col_res4 = st.columns(4)

col_res1.metric("Recurso Solar (HSP)", f"{hsp_promedio:.2f} h")
col_res2.metric("Potencia Sugerida", f"{potencia_sugerida:.2f} kWp")
col_res3.metric("Generación Diaria", f"{gen_diaria:.2f} kWh")
col_res4.metric("Ahorro Mensual", f"${ahorro_mensual:.2f}")

st.markdown("---")

# 5. GRÁFICO Y DETALLE TÉCNICO
col_grafico, col_tecnico = st.columns([2, 1])

with col_grafico:
    st.subheader("Proyección Mensual de Generación")
    gen_mes_a_mes = [potencia_sugerida * h * pr_ajustado * 30.44 for h in hsp_lista]
    
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.bar(ciudades_data["Mes"], gen_mes_a_mes, color="#3498db", alpha=0.8, edgecolor="black")
    ax.axhline(consumo_mensual, color='red', linestyle='--', label=f'Consumo Objetivo ({consumo_mensual} kWh)')
    ax.set_ylabel("Energía (kWh/mes)")
    ax.legend()
    st.pyplot(fig)

with col_tecnico:
    st.subheader("Datos Técnicos Localizados")
    num_paneles = int((potencia_sugerida * 1000) / 550) + 1
    
    st.info(f"""
    - **Ubicación:** {ciudad_sel}
    - **Temperatura Media:** {temp_ciudad}°C
    - **Eficiencia Real (PR):** {pr_ajustado:.1%}
    - **Paneles Sugeridos (550W):** {num_paneles} unidades
    - **Ahorro Anual Proyectado:** ${ahorro_mensual * 12:.2f}
    """)

# 6. TABLA DE DATOS
with st.expander("📂 Ver Tabla Detallada"):
    df_detalle = pd.DataFrame({
        "Mes": ciudades_data["Mes"],
        "HSP": hsp_lista,
        "Gen. Diaria (kWh)": [round(potencia_sugerida * h * pr_ajustado, 2) for h in hsp_lista],
        "Gen. Mensual (kWh)": [round(g, 2) for g in gen_mes_a_mes],
        "Ahorro (USD)": [round(g * costo_kwh, 2) for g in gen_mes_a_mes]
    })
    st.dataframe(df_detalle, use_container_width=True)
    
