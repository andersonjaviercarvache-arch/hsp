import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# 1. Base de Datos Técnica Real (HSP y Temperatura)
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

st.title("☀️ Sistema Solar Fotovoltaico: Técnico y Financiero")
st.markdown("---")

# 2. PARÁMETROS DE ENTRADA (Pantalla Principal)
with st.container():
    col_input1, col_input2, col_input3, col_input4 = st.columns(4)
    with col_input1:
        lista_ciudades = [c for c in ciudades_data.keys() if c != "Mes"]
        ciudad_sel = st.selectbox("📍 Ciudad", lista_ciudades)
    with col_input2:
        consumo_mensual = st.number_input("⚡ Consumo (kWh/mes)", value=300.0, step=10.0, min_value=1.0)
    with col_input3:
        costo_kwh = st.number_input("💵 Costo kWh (USD)", value=0.0920, format="%.4f", step=0.0001)
    with col_input4:
        deg_anual = st.number_input("📉 Degradación Anual (%)", value=0.50, format="%.2f", step=0.05) / 100

# 3. LÓGICA TÉCNICA Y METEOROLÓGICA
datos_met = ciudades_data[ciudad_sel]
temp_ciudad = datos_met["temp"]
hsp_mensuales = datos_met["hsp"]
hsp_promedio_base = sum(hsp_mensuales) / 12

# Performance Ratio dinámico por temperatura
pr_ajustado = 0.82 - ((max(0, temp_ciudad - 15)) * 0.0045)

# Dimensionamiento
pot_sug = consumo_mensual / (hsp_promedio_base * pr_ajustado * 30.44)
costo_planta = pot_sug * 825.0
ahorro_trib_anual = costo_planta / 10
gen_anual_ini = pot_sug * hsp_promedio_base * pr_ajustado * 365

# 4. DASHBOARD DE DATOS METEOROLÓGICOS Y KPIs
st.subheader(f"📊 Información Meteorológica y Técnica: {ciudad_sel}")
col_met1, col_met2, col_met3, col_met4 = st.columns(4)

col_met1.metric("HSP Promedio", f"{hsp_promedio_base:.2f} h/día")
col_met2.metric("Temp. Promedio", f"{temp_ciudad} °C")
col_met3.metric("Eficiencia (PR)", f"{pr_ajustado:.1%}")
col_met4.metric("Inversión Est.", f"${costo_planta:,.2f}")

st.markdown("---")

# 5. CÁLCULO FINANCIERO ANUALIZADO (25 AÑOS)
años = list(range(1, 26))
data_tabla = []
suma_fin = 0
año_payback = None

for i in años:
    factor_deg = (1 - deg_anual)**(i-1)
    hsp_deg = hsp_promedio_base * factor_deg
    prod = gen_anual_ini * factor_deg
    ahorro_en = prod * costo_kwh
    beneficio_trib = ahorro_trib_anual if i <= 10 else 0
    total_anual = ahorro_en + beneficio_trib
    suma_fin += total_anual
    
    if suma_fin >= costo_planta and año_payback is None:
        año_payback = i

    data_tabla.append({
        "Año": i,
        "HSP Prom.": f"{hsp_deg:.2f}",
        "Prod. (kWh/año)": f"{prod:,.0f}",
        "Ahorro Energía": f"${ahorro_en:,.2f}",
        "Ahorro Trib.": f"${beneficio_trib:,.2f}",
        "Ahorro Total Año": f"${total_anual:,.2f}",
        "Acumulado": f"${suma_fin:,.2f}",
        "ROI (%)": f"{(suma_fin/costo_planta)*100:.1f}%"
    })

# 6. GRÁFICOS Y TABLA
col_graf, col_tab = st.columns([1, 1.4])

with col_graf:
    st.subheader("Análisis de Radiación y Payback")
    # Gráfico de HSP Mensuales (Datos Meteorológicos)
    fig, ax1 = plt.subplots(figsize=(10, 6))
    ax1.bar(ciudades_data["Mes"], hsp_mensuales, color="orange", alpha=0.6, label="HSP Mensual")
    ax1.set_ylabel("Horas Solar Pico (HSP)")
    ax1.set_ylim(0, 7)
    
    # Línea de Payback en el mismo gráfico o secundario
    ax2 = ax1.twinx()
    acum_vals = [float(d['Acumulado'].replace('$', '').replace(',', '')) for d in data_tabla]
    ax2.plot(range(12), acum_vals[:12], color="blue", marker="o", label="Ahorro Acum. (Año 1)")
    ax2.set_ylabel("Ahorro USD (Primer Año)")
    
    ax1.legend(loc="upper left")
    st.pyplot(fig)
    
    if año_payback:
        st.success(f"⏱️ **Retorno de Inversión:** {año_payback} años.")

with col_tab:
    st.subheader("Proyección a 25 Años")
    df_proy = pd.DataFrame(data_tabla)
    st.dataframe(df_proy, height=450, use_container_width=True)

# 7. TABLA METEOROLÓGICA MENSUAL (HSP PURAS)
with st.expander("☁️ Ver Detalle de Radiación Mensual (HSP)"):
    df_met = pd.DataFrame({
        "Mes": ciudades_data["Mes"],
        "HSP (kWh/m²/día)": hsp_mensuales
    })
    st.table(df_met.T)
