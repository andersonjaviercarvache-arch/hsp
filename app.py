import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# 1. Base de Datos Técnica (HSP y Temperatura promedio para PR dinámico)
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

st.set_page_config(page_title="HSP Ecuador - Análisis Económico", layout="wide")

# Estilo personalizado para el título
st.title("☀️ Calculadora Solar de Ecuador: Técnica y Económica")
st.markdown("---")

# 2. Sidebar de Configuración
st.sidebar.header("⚙️ Configuración del Sistema")
lista_ciudades = [c for c in ciudades_data.keys() if c != "Mes"]
ciudad_sel = st.sidebar.selectbox("Seleccione la Ciudad", lista_ciudades)

potencia_kwp = st.sidebar.number_input("Potencia Instalada (kWp)", value=5.0, step=0.5, min_value=0.1)

st.sidebar.header("💰 Parámetros Económicos")
costo_kwh = st.sidebar.slider("Costo del kWh (USD)", 0.04, 0.20, 0.09, step=0.01, 
                             help="Promedio en Ecuador: $0.09 - $0.10 para residencial.")

# 3. Lógica de Rendimiento (PR Dinámico por Temperatura)
temp_ciudad = ciudades_data[ciudad_sel]["temp"]
# El PR base 0.82 disminuye si la temperatura supera los 15°C (ajuste por clima de Ecuador)
pr_ajustado = 0.82 - ((max(0, temp_ciudad - 15)) * 0.0045)

# 4. Cálculos de Generación
hsp_lista = ciudades_data[ciudad_sel]["hsp"]
hsp_promedio = sum(hsp_lista) / len(hsp_lista)

gen_diaria = potencia_kwp * hsp_promedio * pr_ajustado
gen_mensual = gen_diaria * 30.44  # Promedio de días al mes
ahorro_mensual = gen_mensual * costo_kwh
ahorro_anual = ahorro_mensual * 12

# 5. Visualización de Resultados (KPIs)
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("HSP Diarias", f"{hsp_promedio:.2f} h")
with col2:
    st.metric("Gen. Mensual Est.", f"{gen_mensual:.2f} kWh")
with col3:
    st.metric("PR (Rendimiento)", f"{pr_ajustado:.1%}")
with col4:
    st.subheader(f"💵 Ahorro: ${ahorro_mensual:.2f}/mes")

st.markdown("---")

# 6. Gráficos y Tablas
col_izq, col_der = st.columns([2, 1])

with col_izq:
    st.subheader(f"Producción Energética Mensual en {ciudad_sel}")
    fig, ax = plt.subplots(figsize=(10, 4))
    
    # Cálculo de generación mes a mes para el gráfico
    gen_mes_a_mes = [potencia_kwp * h * pr_ajustado * 30.44 for h in hsp_lista]
    
    ax.bar(ciudades_data["Mes"], gen_mes_a_mes, color="#2ecc71", edgecolor="black")
    ax.set_ylabel("Generación Estimada (kWh/mes)")
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    st.pyplot(fig)

with col_der:
    st.subheader("Resumen Económico")
    st.success(f"""
    **Estimación Anual:**
    - Generación: {gen_mensual * 12:.0f} kWh/año
    - Ahorro Total: ${ahorro_anual:.2f}/año
    """)
    
    st.info(f"""
    **Datos Climáticos ({ciudad_sel}):**
    - Temp. Promedio: {temp_ciudad}°C
    - El calor reduce la eficiencia en un {(0.82-pr_ajustado):.1%}.
    """)

# 7. Tabla Detallada
if st.checkbox("Mostrar tabla de datos técnicos mensuales"):
    df_detalle = pd.DataFrame({
        "Mes": ciudades_data["Mes"],
        "HSP (kWh/m²/día)": hsp_lista,
        "Gen. Estimada (kWh)": [round(g, 2) for g in gen_mes_a_mes]
    })
    st.table(df_detalle)
