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

st.set_page_config(page_title="HSP Ecuador - Análisis de Inversión", layout="wide")

st.title("☀️ Análisis de Retorno de Inversión Solar (Payback)")
st.markdown("---")

# 2. PARÁMETROS EN PANTALLA PRINCIPAL
with st.container():
    col_input1, col_input2, col_input3, col_input4, col_input5 = st.columns(5)
    with col_input1:
        lista_ciudades = [c for c in ciudades_data.keys() if c != "Mes"]
        ciudad_sel = st.selectbox("📍 Ciudad", lista_ciudades)
    with col_input2:
        consumo_mensual = st.number_input("⚡ Consumo (kWh/mes)", value=300.0, step=10.0, min_value=1.0)
    with col_input3:
        costo_kwh = st.number_input("💵 Costo kWh (USD)", value=0.0920, format="%.4f", step=0.0001)
    with col_input4:
        deg_año1 = st.number_input("📉 Deg. Año 1 (%)", value=2.0, format="%.2f", step=0.1) / 100
    with col_input5:
        atenuacion_anual = st.number_input("📉 Atenuación Anual (%)", value=0.55, format="%.2f", step=0.05) / 100

# 3. LÓGICA TÉCNICA Y FINANCIERA
temp_ciudad = ciudades_data[ciudad_sel]["temp"]
pr_ajustado = 0.82 - ((max(0, temp_ciudad - 15)) * 0.0045)
hsp_promedio_base = sum(ciudades_data[ciudad_sel]["hsp"]) / 12

pot_sug = consumo_mensual / (hsp_promedio_base * pr_ajustado * 30.44)
costo_planta_total = pot_sug * 825.0
ahorro_tributario_anual = costo_planta_total / 10
gen_anual_inicial = pot_sug * hsp_promedio_base * pr_ajustado * 365

# 4. CÁLCULO DEL PAYBACK (AÑOS)
años_lista = list(range(1, 26))
data_tabla = []
suma_fin = 0
año_payback = None

for i in años_lista:
    if i == 1:
        rendimiento_pct = (1 - deg_año1)
    else:
        rendimiento_pct = (1 - deg_año1) * ((1 - atenuacion_anual)**(i-1))
    
    # Cambio solicitado: Índice de degradación negativo
    indice_degradacion = (rendimiento_pct - 1) * 100 
    
    prod = gen_anual_inicial * rendimiento_pct
    ahorro_en = prod * costo_kwh
    beneficio_trib = ahorro_tributario_anual if i <= 10 else 0
    total_anual = ahorro_en + beneficio_trib
    suma_fin += total_anual
    
    if suma_fin >= costo_planta_total and año_payback is None:
        año_payback = i

    data_tabla.append({
        "Año": i,
        "Índice de Degradación": f"{indice_degradacion:.2f}%", # Nombre y signo ajustado
        "Prod. (kWh/año)": f"{prod:,.0f}",
        "Ahorro Energía": f"${ahorro_en:,.2f}",
        "Ahorro Trib.": f"${beneficio_trib:,.2f}",
        "Ahorro Total Año": f"${total_anual:,.2f}",
        "Acumulado": f"${suma_fin:,.2f}"
    })

# 5. DASHBOARD DE RESULTADOS (Se mantiene igual)
st.subheader("📊 Resumen Económico del Proyecto")
col_res1, col_res2, col_res3, col_res4 = st.columns(4)

col_res1.metric("Inversión Total", f"${costo_planta_total:,.2f}")
col_res2.metric("Potencia Sugerida", f"{pot_sug:.2f} kWp")
col_res3.metric("Ahorro Total (25 años)", f"${suma_fin:,.2f}")

if año_payback:
    col_res4.metric("Payback (Retorno)", f"{año_payback} años")
else:
    col_res4.metric("Payback (Retorno)", "> 25 años")

st.markdown("---")

# 6. GRÁFICO Y TABLA
col_grafico, col_tabla = st.columns([1, 1.4])

with col_grafico:
    st.subheader("Tiempo de Recuperación de Capital")
    acumulado_vals = [float(d['Acumulado'].replace('$', '').replace(',', '')) for d in data_tabla]
    fig, ax = plt.subplots(figsize=(10, 7))
    ax.plot(años_lista, acumulado_vals, color="#1f77b4", marker="o", label="Flujo Acumulado")
    ax.axhline(costo_planta_total, color='red', linestyle='--', label=f'Inversión (${costo_planta_total:,.0f})')
    
    if año_payback:
        ax.axvline(año_payback, color='green', linestyle=':', label=f'Retorno: Año {año_payback}')
        ax.scatter(año_payback, costo_planta_total, color='green', s=100, zorder=5)

    ax.set_xlabel("Años")
    ax.set_ylabel("Dólares ($)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    st.pyplot(fig)

with col_tabla:
    st.subheader("Proyección de Flujo de Caja")
    df_proyeccion = pd.DataFrame(data_tabla)
    st.dataframe(df_proyeccion, height=480, use_container_width=True)

st.success(f"✅ Tabla actualizada: Se muestra el **Índice de Degradación** como valor negativo para representar la pérdida de eficiencia.")

