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

st.set_page_config(page_title="HSP Ecuador - Análisis Financiero Pro", layout="wide")

st.title("☀️ Análisis Financiero Solar y Beneficios Tributarios")
st.markdown("---")

# 2. PARÁMETROS EN PANTALLA PRINCIPAL
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
        degradacion_anual = st.number_input("📉 Degradación Anual (%)", value=0.50, format="%.2f", step=0.05) / 100

# 3. LÓGICA TÉCNICA Y FINANCIERA
temp_ciudad = ciudades_data[ciudad_sel]["temp"]
pr_ajustado = 0.82 - ((max(0, temp_ciudad - 15)) * 0.0045)
hsp_promedio = sum(ciudades_data[ciudad_sel]["hsp"]) / 12

# Potencia necesaria y Costo de Planta
pot_sug = consumo_mensual / (hsp_promedio * pr_ajustado * 30.44)
costo_planta_total = pot_sug * 825.0  # Referencia $825 por kWp instalado
ahorro_tributario_anual = costo_planta_total / 10  # Distribuido en 10 años
gen_anual_inicial = pot_sug * hsp_promedio * pr_ajustado * 365

# 4. DASHBOARD DE RESULTADOS
st.subheader("📊 Resumen Ejecutivo del Proyecto")
col_res1, col_res2, col_res3, col_res4 = st.columns(4)

col_res1.metric("Inversión Est. (Planta)", f"${costo_planta_total:,.2f}")
col_res2.metric("Potencia Sugerida", f"{pot_sug:.2f} kWp")
col_res3.metric("Beneficio Tributario/Año", f"${ahorro_tributario_anual:,.2f}")

# Cálculo acumulado para el KPI
años_lista = list(range(1, 26))
acumulado_lista = []
suma_acumulada = 0

for i in años_lista:
    prod = gen_anual_inicial * ((1 - degradacion_anual)**(i-1))
    ahorro_energia = prod * costo_kwh
    beneficio_trib = ahorro_tributario_anual if i <= 10 else 0
    total_anual = ahorro_energia + beneficio_trib
    suma_acumulada += total_anual
    acumulado_lista.append(suma_acumulada)

col_res4.metric("Retorno Total (25 años)", f"${suma_acumulada:,.2f}")

st.markdown("---")

# 5. GRÁFICO Y TABLA FINANCIERA
col_grafico, col_tabla = st.columns([1, 1.2])

# Datos para la tabla anualizada
data_tabla = []
suma_fin = 0
for i in años_lista:
    rendimiento_pct = (1 - degradacion_anual)**(i-1)
    prod = gen_anual_inicial * rendimiento_pct
    ahorro_en = prod * costo_kwh
    beneficio_trib = ahorro_tributario_anual if i <= 10 else 0
    total_anual = ahorro_en + beneficio_trib
    suma_fin += total_anual
    
    data_tabla.append({
        "Año": i,
        "Degradación (%)": f"{(1-rendimiento_pct)*100:.2f}%",
        "Costo kWh (USD)": f"${costo_kwh:.4f}",
        "Prod. (kWh/año)": f"{prod:,.0f}",
        "Ahorro Energía": f"${ahorro_en:,.2f}",
        "Ahorro Tributario": f"${beneficio_trib:,.2f}",
        "Ahorro Total Año": f"${total_anual:,.2f}",
        "Acumulado": f"${suma_fin:,.2f}"
    })

df_proyeccion = pd.DataFrame(data_tabla)

with col_grafico:
    st.subheader("Curva de Retorno de Inversión")
    fig, ax = plt.subplots(figsize=(10, 6.5))
    ax.fill_between(años_lista, acumulado_lista, color="#2ecc71", alpha=0.3)
    ax.plot(años_lista, acumulado_lista, color="#27ae60", marker="o", linewidth=2)
    ax.axhline(costo_planta_total, color='red', linestyle='--', label='Punto de Equilibrio (CAPEX)')
    ax.set_xlabel("Años")
    ax.set_ylabel("Beneficio Económico Acumulado ($)")
    ax.legend()
    st.pyplot(fig)

with col_tabla:
    st.subheader("Proyección Financiera Detallada")
    st.dataframe(df_proyeccion, height=480, use_container_width=True)

st.success(f"✅ **Análisis:** En 10 años, usted habrá recuperado **${ahorro_tributario_anual*10:,.2f}** solo por beneficios tributarios, adicionales al ahorro en su planilla eléctrica.")
