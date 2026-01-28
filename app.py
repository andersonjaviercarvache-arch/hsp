import streamlit as st
import pandas as pd
import numpy as np

# Configuración de la página
st.set_page_config(page_title="SolarDesign Ecuador", layout="wide", page_icon="☀️")

# --- BASE DE DATOS CLIMÁTICA ECUADOR ---
CIUDADES = {
    "Quito (Sierra)": {"hsp": 4.8, "temp": 14, "tarifa": 0.09, "alerta": "⚠️ Nubosidad vespertina: Se recomienda sobredimensionar 10%."},
    "Guayaquil (Costa)": {"hsp": 4.5, "temp": 26, "tarifa": 0.10, "alerta": "🌊 Salinidad y calor: Usar estructuras de aluminio anodizado."},
    "Cuenca (Sierra)": {"hsp": 4.9, "temp": 15, "tarifa": 0.09, "alerta": "⛰️ Excelente radiación UV. Rendimiento superior al promedio."},
    "Manta (Costa)": {"hsp": 4.6, "temp": 25, "tarifa": 0.10, "alerta": "💨 Vientos fuertes: Asegurar anclajes reforzados."},
    "Loja (Sur)": {"hsp": 5.1, "temp": 16, "tarifa": 0.09, "alerta": "⚡ Zona privilegiada (Villonaco). Alto potencial."}
}

# --- LÓGICA DE CÁLCULO ---
def calcular_fotovoltaico(ciudad_key, consumo_mensual_kwh, potencia_panel_w):
    datos = CIUDADES[ciudad_key]
    
    # Factor de pérdidas (Performance Ratio)
    # Si hace mucho calor (Costa), el rendimiento baja un poco más
    pr = 0.75 if datos['temp'] > 20 else 0.80
    
    # Cálculo inverso: De kWh mes a Potencia requerida
    consumo_diario = consumo_mensual_kwh / 30
    potencia_requerida_kw = consumo_diario / (datos['hsp'] * pr)
    
    # Número de paneles
    num_paneles = np.ceil((potencia_requerida_kw * 1000) / potencia_panel_w)
    potencia_instalada_kw = (num_paneles * potencia_panel_w) / 1000
    
    # Área (aprox 2.2m2 por panel)
    area = num_paneles * 2.2
    
    # Ahorro estimado
    ahorro_mensual = consumo_mensual_kwh * datos['tarifa']
    generacion_mensual = potencia_instalada_kw * datos['hsp'] * 30 * pr
    
    return {
        "paneles": int(num_paneles),
        "potencia_inst": potencia_instalada_kw,
        "area": area,
        "ahorro": ahorro_mensual,
        "generacion": generacion_mensual,
        "datos_ciudad": datos
    }

# --- INTERFAZ DE USUARIO ---
st.title("☀️ Dimensionamiento Solar Ecuador")
st.markdown("Herramienta técnica para cálculo de sistemas fotovoltaicos residenciales.")

# Sidebar de Entradas
with st.sidebar:
    st.header("📍 Parámetros del Proyecto")
    ciudad = st.selectbox("Selecciona la Ciudad:", list(CIUDADES.keys()))
    
    tipo_calculo = st.radio("¿Qué dato tienes?", ["Consumo (kWh/mes)", "Factura ($)"])
    
    val_entrada = 0
    if tipo_calculo == "Consumo (kWh/mes)":
        val_entrada = st.number_input("Ingresa consumo promedio:", value=350)
        consumo_final = val_entrada
    else:
        val_entrada = st.number_input("Monto de la factura ($):", value=40.0)
        tarifa_ref = CIUDADES[ciudad]["tarifa"]
        consumo_final = val_entrada / tarifa_ref
        st.caption(f"Calculado con tarifa ref: ${tarifa_ref}/kWh")

    panel_w = st.selectbox("Potencia del Panel (Wp):", [450, 500, 550, 600], index=2)
    
    st.divider()
    st.info("Diseñado para normativa ARCONEL 001/21 (Generación Distribuida).")

# Ejecutar Cálculos
res = calcular_fotovoltaico(ciudad, consumo_final, panel_w)

# --- RESULTADOS PRINCIPALES ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Paneles Necesarios", f"{res['paneles']} Unidades", help=f"Módulos de {panel_w}W")
col2.metric("Potencia Sistema", f"{res['potencia_inst']:.2f} kWp")
col3.metric("Generación Estimada", f"{res['generacion']:.0f} kWh/mes")
col4.metric("Área de Techo", f"{res['area']:.1f} m²")

st.markdown("---")

# --- DETALLES Y GRÁFICAS ---
c_left, c_right = st.columns([2, 1])

with c_left:
    st.subheader("📊 Proyección de Ahorro")
    # Alerta específica por ciudad
    st.warning(res['datos_ciudad']['alerta'])
    
    # Tabla simple de BOM
    bom_data = pd.DataFrame([
        {"Item": "Módulos Fotovoltaicos", "Detalle": f"{res['paneles']}x {panel_w}W Monocristalino", "Cant": res['paneles']},
        {"Item": "Inversor Central/Micro", "Detalle": f"Capacidad nominal {res['potencia_inst']*1.1:.1f} kW", "Cant": 1},
        {"Item": "Estructura Aluminio", "Detalle": "Rieles, Clamps y Anclajes", "Cant": "1 Global"},
        {"Item": "Protecciones DC/AC", "Detalle": "DPS, Breakers, Tablero", "Cant": "1 Global"}
    ])
    st.table(bom_data)

with c_right:
    st.subheader("💰 Rentabilidad")
    st.write(f"**Ahorro Mensual:** ${res['ahorro']:.2f}")
    st.write(f"**Ahorro Anual:** ${res['ahorro']*12:.2f}")
    
    # Gráfico simple de retorno
    inversion_estimada = res['potencia_inst'] * 1000 * 1.10 # $1.10 por Watt instalado
    payback = inversion_estimada / (res['ahorro']*12)
    
    st.metric("Inversión Aprox. (Llave en mano)", f"${inversion_estimada:,.0f}")
    st.metric("Retorno de Inversión (Payback)", f"{payback:.1f} Años")
    st.progress(min(1.0, 1/payback), text="Velocidad de Recuperación")