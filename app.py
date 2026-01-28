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

st.set_page_config(page_title="HSP Ecuador - Proyección 25 Años", layout="wide")

st.title("☀️ Análisis Solar y Financiero a Largo Plazo (25 Años)")
st.markdown("---")

# 2. PARÁMETROS EN PANTALLA PRINCIPAL
with st.container():
    col_input1, col_input2, col_input3 = st.columns(3)
    with col_input1:
        lista_ciudades = [c for c in ciudades_data.keys() if c != "Mes"]
        ciudad_sel = st.selectbox("📍 Ciudad del Proyecto", lista_ciudades)
    with col_input2:
        consumo_mensual = st.number_input("⚡ Consumo Mensual (kWh/mes)", value=300.0, step=10.0, min_value=1.0)
    with col_input3:
        costo_kwh = st.number_input("💵 Costo kWh (USD)", value=0.0920, format="%.4f", step=0.0001)

# 3. LÓGICA TÉCNICA
temp_ciudad = ciudades_data[ciudad_sel]["temp"]
pr_ajustado = 0.82 - ((max(0, temp_ciudad - 15)) * 0.0045)
hsp_promedio = sum(ciudades_data[ciudad_sel]["hsp"]) / 12

# Potencia necesaria para cubrir el 100% del consumo
potencia_sugerida = consumo_mensual / (hsp_promedio * pr_ajustado * 30.44)
gen_anual_inicial = potencia_sugerida * hsp_promedio * pr_ajustado * 365

# 4. DASHBOARD DE RESULTADOS
st.subheader("📊 Resumen de Inversión y Generación")
col_res1, col_res2, col_res3, col_res4 = st.columns(4)

col_res1.metric("Potencia a Instalar", f"{potencia_sugerida:.2f} kWp")
col_res2.metric("Paneles (550W)", f"{int((potencia_sugerida*1000)/550)+1} ud")
col_res3.metric("Ahorro Año 1", f"${gen_anual_inicial * costo_kwh:.2f}")

# Cálculo del ahorro acumulado a 25 años con degradación del 0.5% anual
ahorro_acumulado_25 = 0
for i in range(25):
    ahorro_acumulado_25 += (gen_anual_inicial * (0.995**i)) * costo_kwh

col_res4.metric("Ahorro Total (25 años)", f"${ahorro_acumulado_25:,.2f}")

st.markdown("---")

# 5. TABLA ANUALIZADA Y GRÁFICO DE AHORRO
col_grafico, col_tabla = st.columns([1, 1])

# Crear DataFrame para la tabla de 25 años
años = list(range(1, 26))
produccion_anual = [gen_anual_inicial * (0.995**(i-1)) for i in años]
ahorro_anual = [p * costo_kwh for p in produccion_anual]
ahorro_total_acumulado = [sum(ahorro_anual[:i]) for i in años]

df_25_años = pd.DataFrame({
    "Año": años,
    "Producción (kWh/año)": [f"{p:,.2f}" for p in produccion_anual],
    "Ahorro Anual (USD)": [f"$ {a:,.2f}" for a in ahorro_anual],
    "Ahorro Acumulado
