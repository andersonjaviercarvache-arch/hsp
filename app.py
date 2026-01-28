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

st.set_page_config(page_title="Solar Pro - Ecuador", layout="wide")

st.title("☀️ Sistema Solar Fotovoltaico: Análisis Técnico y Financiero")

# 2. PARÁMETROS DE ENTRADA
with st.container():
    col_in1, col_in2, col_in3, col_in4 = st.columns(4)
    with col_in1:
        ciudad_sel = st.selectbox("📍 Ciudad", [c for c in ciudades_data.keys() if c != "Mes"])
    with col_in2:
        consumo_mensual = st.number_input("⚡ Consumo (kWh/mes)", value=300.0, step=10.0, min_value=1.0)
    with col_in3:
        costo_kwh = st.number_input("💵 Costo kWh (USD)", value=0.0920, format="%.4f", step=0.0001)
    with col_in4:
        deg_anual = st.number_input("📉 Degradación Anual (%)", value=0.50, format="%.2f", step=0.05) / 100

# 3. PROCESAMIENTO TÉCNICO
datos_met = ciudades_data[ciudad_sel]
hsp_mes = datos_met["hsp"]
hsp_prom_base = sum(hsp_mes) / 12
temp_c = datos_met["temp"]
pr_ajustado = 0.82 - ((max(0, temp_c - 15)) * 0.0045)

# Financiero
pot_sug = consumo_mensual / (hsp_prom_base * pr_ajustado * 30.44)
costo_planta = pot_sug * 825.0
ahorro_trib_anual = costo_planta / 10
gen_anual_ini = pot_sug * hsp_prom_base * pr_ajustado * 365

# 4. VISIBILIDAD DE DATOS METEOROLÓGICOS (KPIs)
st.markdown("---")
st.subheader(f"📊 Datos Meteorológicos y Técnicos: {ciudad_sel}")
c1, c2, c3, c4 = st.columns(4)
c1.metric("HSP Promedio", f"{hsp_prom_base:.2f} h/día")
c2.metric("Temperatura", f"{temp_c} °C")
c3.metric("Potencia Planta", f"{pot_sug:.2f} kWp")
c4.metric("Costo Planta", f"${costo_planta:,.2f}")

# 5. CÁLCULOS ANUALES (25 AÑOS)
data_tabla = []
suma_acum = 0
año_payback = None

for i in range(1, 26):
    f_deg = (1 - deg_anual)**(i-1)
    prod = gen_anual_ini * f_deg
    ah_en = prod * costo_kwh
    ah_tr = ahorro_trib_anual if i <= 10 else 0
    total_año = ah_en + ah_tr
    suma_acum += total_año
    
    if suma_acum >= costo_planta and año_payback is None:
        año_payback = i

    data_tabla.append({
        "Año": i,
        "HSP Prom.": f"{(hsp_prom_base * f_deg):.2f}",
        "Prod. (kWh/año)": f"{prod:,.0f}",
        "Ahorro Energía": f"${ah_en:,.2f}",
        "Ahorro Trib.": f"${ah_tr:,.2f}",
        "Ahorro Total Año": f"${total_año:,.2f}",
        "Acumulado": f"${suma_acum:,.2f}"
    })

# 6. GRÁFICOS Y TABLA
col_graf, col_tab = st.columns([1, 1.4])

with col_graf:
    st.subheader("Radiación Mensual (HSP)")
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(ciudades_data["Mes"], hsp_mes, color="gold", edgecolor="orange")
    ax.set_ylabel("HSP (kWh/m²/día)")
    ax.set_title(f"Distribución de Radiación en {ciudad_sel}")
    st.pyplot(fig)
    
    if año_payback:
        st.success(f"⏱️ **Retorno de Inversión (Payback):** {año_payback} años")

with col_tab:
    st.subheader("Proyección Financiera Detallada")
    df_proy = pd.DataFrame(data_tabla)
    st.dataframe(df_proy, height=450, use_container_width=True)

# 7. TABLA METEOROLÓGICA MANUAL
st.markdown("---")
with st.expander("📂 Ver Tabla de Radiación Mensual"):
    st.table(pd.DataFrame({"Mes": ciudades_data["Mes"], "HSP": hsp_mes}).T)
