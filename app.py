import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
from fpdf import FPDF
import tempfile
import os
import re
import io
import math
import requests
import pdfplumber

try:
    import pytesseract
    from pdf2image import convert_from_bytes
    from PIL import Image
    OCR_DISPONIBLE = True
except Exception:
    OCR_DISPONIBLE = False

# --- 1. BASE DE DATOS DE RESPALDO (usada si NASA POWER no responde) ---
# HSP: Atlas Solar del Ecuador (CONELEC/CIE, 2008) y estimaciones satelitales NREL/Global Solar Atlas.
# Coordenadas: ubicación geográfica estándar de cada ciudad.
ciudades_data = {
    "Guayaquil":  {"lat": -2.1894, "lon": -79.8891, "hsp": [4.12, 4.05, 4.38, 4.51, 4.32, 4.10, 4.45, 4.92, 5.15, 5.02, 4.85, 4.58], "temp": 27.5},
    "Durán":      {"lat": -2.1710, "lon": -79.8285, "hsp": [4.08, 3.98, 4.35, 4.48, 4.28, 4.05, 4.40, 4.88, 5.10, 5.05, 4.90, 4.62], "temp": 27.8},
    "Quito":      {"lat": -0.1807, "lon": -78.4678, "hsp": [4.85, 4.62, 4.28, 4.02, 4.15, 4.65, 5.18, 5.42, 5.35, 4.88, 4.55, 4.68], "temp": 14.5},
    "Cuenca":     {"lat": -2.9006, "lon": -79.0045, "hsp": [4.45, 4.38, 4.25, 4.15, 3.85, 3.72, 3.95, 4.35, 4.62, 4.75, 4.82, 4.55], "temp": 15.0},
    "Esmeraldas": {"lat":  0.9682, "lon": -79.6517, "hsp": [3.65, 3.82, 4.12, 4.25, 4.18, 3.85, 3.75, 4.05, 4.15, 4.08, 3.95, 3.72], "temp": 26.5},
    "Manta":      {"lat": -0.9677, "lon": -80.7089, "hsp": [4.82, 4.95, 5.15, 5.35, 5.12, 4.85, 4.98, 5.45, 5.75, 5.62, 5.48, 5.15], "temp": 26.2}
}

MESES_ORDEN_NASA = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]


@st.cache_data(ttl=86400, show_spinner=False)
def obtener_datos_nasa_power(lat, lon):
    """Consulta la climatología mensual multi-anual de NASA POWER (irradiancia y temperatura).
    Retorna (hsp_mensual, temp_mensual, exito)."""
    try:
        url = "https://power.larc.nasa.gov/api/temporal/climatology/point"
        params = {
            "parameters": "ALLSKY_SFC_SW_DWN,T2M",
            "community": "RE",
            "longitude": lon,
            "latitude": lat,
            "format": "JSON"
        }
        resp = requests.get(url, params=params, timeout=8)
        resp.raise_for_status()
        data = resp.json()
        hsp_mensual = [data["properties"]["parameter"]["ALLSKY_SFC_SW_DWN"][m] for m in MESES_ORDEN_NASA]
        temp_mensual = [data["properties"]["parameter"]["T2M"][m] for m in MESES_ORDEN_NASA]
        return hsp_mensual, temp_mensual, True
    except Exception:
        return None, None, False


def calcular_pr(temp_ambiente_prom, noct, coef_temp_pct, perdidas_sistema_pct, eficiencia_inversor_pct):
    """Modelo NOCT (Nominal Operating Cell Temperature), estándar en PVWatts/NREL y Sandia:
    T_celda = T_ambiente + (NOCT - 20), evaluado a irradiancia de referencia de 800 W/m2 (condición NOCT).
    Luego se aplican pérdidas por temperatura, inversor y sistema (cableado, suciedad, mismatch, disponibilidad)."""
    t_celda = temp_ambiente_prom + (noct - 20)
    factor_temp = 1 + (coef_temp_pct / 100.0) * (t_celda - 25)
    factor_temp = max(factor_temp, 0.5)  # salvaguarda ante valores extremos
    pr = factor_temp * (eficiencia_inversor_pct / 100.0) * (1 - perdidas_sistema_pct / 100.0)
    return pr, t_celda


# --- EXTRACCIÓN DE TEXTO DE ARCHIVOS SUBIDOS (PDF digital u OCR de imagen/escaneo) ---
def extraer_texto_archivo(archivo_subido):
    """Devuelve (texto_extraido, metodo). metodo: 'texto_pdf', 'ocr', o 'fallo'."""
    nombre = archivo_subido.name.lower()
    datos = archivo_subido.read()
    archivo_subido.seek(0)

    if nombre.endswith(".pdf"):
        texto = ""
        try:
            with pdfplumber.open(io.BytesIO(datos)) as pdf:
                for pagina in pdf.pages:
                    texto += (pagina.extract_text() or "") + "\n"
        except Exception:
            texto = ""

        if len(texto.strip()) >= 25:
            return texto, "texto_pdf"

        # El PDF no tiene texto seleccionable (probablemente escaneado) -> intentar OCR
        if OCR_DISPONIBLE:
            try:
                paginas_img = convert_from_bytes(datos, dpi=200)
                texto_ocr = ""
                for img in paginas_img:
                    texto_ocr += pytesseract.image_to_string(img, lang="spa+eng") + "\n"
                if len(texto_ocr.strip()) >= 10:
                    return texto_ocr, "ocr"
            except Exception:
                pass
        return "", "fallo"

    else:
        # Imagen (jpg/png)
        if OCR_DISPONIBLE:
            try:
                img = Image.open(io.BytesIO(datos))
                texto_ocr = pytesseract.image_to_string(img, lang="spa+eng")
                if len(texto_ocr.strip()) >= 10:
                    return texto_ocr, "ocr"
            except Exception:
                pass
        return "", "fallo"


def _buscar_numero(patron, texto, flags=re.IGNORECASE):
    m = re.search(patron, texto, flags)
    if not m:
        return None
    valor = m.group(1).replace(",", ".").replace(" ", "")
    try:
        return float(valor)
    except ValueError:
        return None


def _buscar_texto(patron, texto, flags=re.IGNORECASE):
    m = re.search(patron, texto, flags)
    if not m:
        return None
    return m.group(1).strip()


def extraer_datos_panel(texto):
    """Extrae parámetros técnicos de una ficha técnica de panel solar (best-effort, revisar siempre)."""
    return {
        "potencia_wp": _buscar_numero(r"(?:Maximum Power|Potencia\s*M[aá]xima|Nominal\s*Power|Pmax)[^\d\-]{0,15}(\d{2,4}(?:[.,]\d+)?)\s*W", texto),
        "noct": _buscar_numero(r"NOCT[^\d\-]{0,40}(\d{2,3}(?:[.,]\d+)?)\s*°?\s*C", texto),
        "eficiencia_pct": _buscar_numero(r"(?:Module\s*Efficiency|Eficiencia\s*del?\s*[MmPp]ódulo|Eficiencia)[^\d\-]{0,15}(\d{1,2}(?:[.,]\d+)?)\s*%", texto),
        "coef_temp_pct": _buscar_numero(r"(?:Temperature\s*Coefficient\s*of\s*P(?:max|MAX)|Coeficiente\s*de\s*Temperatura)[^\d\-]{0,20}(-?\d{1,2}[.,]\d+)\s*%", texto),
    }


def extraer_datos_planilla(texto):
    """Extrae datos de una planilla eléctrica ecuatoriana (CNEL u otra), best-effort."""
    consumos = [float(x.replace(",", ".")) for x in re.findall(r"(\d{2,5}(?:[.,]\d+)?)\s*kWh", texto, flags=re.IGNORECASE)]
    return {
        "cliente": _buscar_texto(r"(?:Nombre\s*del?\s*Cliente|Cliente)[:\s]+([A-ZÁÉÍÓÚÑ][^\n]{3,60})", texto),
        "contrato": _buscar_texto(r"(?:N[uú]mero\s*de\s*Cuenta\s*Contrato|Cuenta\s*Contrato|N[°º]?\s*de?\s*Contrato|N[uú]mero\s*de\s*Suministro)[:\s#Nn°º]*([\w\-]{4,20})", texto),
        "direccion": _buscar_texto(r"(?:Direcci[oó]n)[:\s]+([^\n]{5,90})", texto),
        "valor_pagar": _buscar_numero(r"(?:Valor\s*a\s*Pagar|Total\s*a\s*Pagar|TOTAL\s*USD)[:\s\$]{0,5}([\d.,]+)", texto),
        "consumos_kwh": consumos,
    }


st.set_page_config(page_title="Latitud Solar - Generador de Propuestas", layout="wide")

valores_default = {
    "nombre_cliente": "Martillo Jara Angel Cristobal",
    "costo_kwp": 850.0,
    "consumo_mensual": 1228.0,
    "pago_planilla": 149.94,
    "noct": 45.0,
    "coef_temp_pct": -0.40,
    "potencia_panel_wp": 550.0,
    "eficiencia_panel_pct": 21.0,
    "ubicacion_cliente": "",
    "numero_contrato": "",
}
for _clave, _valor in valores_default.items():
    if _clave not in st.session_state:
        st.session_state[_clave] = _valor

# --- SIDEBAR: INFORMACIÓN DEL CLIENTE ---
st.sidebar.header("📋 Información del Cliente")
nombre_cliente = st.sidebar.text_input("Nombre del Cliente", key="nombre_cliente")
n_proyecto = st.sidebar.text_input("Número de Proyecto", "P0000000010")
numero_contrato = st.sidebar.text_input("N° de Contrato / Cuenta", key="numero_contrato")
ubicacion_cliente = st.sidebar.text_input("📍 Ubicación / Dirección del Proyecto", key="ubicacion_cliente")
tipo_proyecto = st.sidebar.selectbox("Tipo de Proyecto", ["Residencial", "Comercial"])
vendedor = st.sidebar.text_input("Asesor Comercial", "Ing. Solar")

# --- SIDEBAR: PARÁMETROS TÉCNICOS AVANZADOS (MODELO PR / NOCT) ---
st.sidebar.header("⚙️ Parámetros Técnicos del Sistema (PR)")
usar_tiempo_real = st.sidebar.checkbox("🌐 Usar meteorología en tiempo real (NASA POWER)", value=True,
                                        help="Consulta climatología satelital multi-anual real por coordenadas. Si falla la conexión, se usan valores de referencia locales.")
noct = st.sidebar.number_input("NOCT del panel (°C)", min_value=40.0, max_value=50.0, step=0.5, key="noct",
                                help="Temperatura Nominal de Operación de Celda. Típico 44-47°C según ficha técnica del fabricante.")
coef_temp_pct = st.sidebar.number_input("Coef. Temperatura Potencia (%/°C)", min_value=-0.60, max_value=-0.20, step=0.01, key="coef_temp_pct",
                                         help="Pérdida de potencia por cada °C sobre 25°C (condición STC). Típico -0.35% a -0.45%/°C en silicio cristalino.")
potencia_panel_wp = st.sidebar.number_input("Potencia por Panel (Wp)", min_value=100.0, max_value=1000.0, step=5.0, key="potencia_panel_wp",
                                             help="Potencia nominal de un solo panel, usada para estimar el número de paneles necesarios.")
eficiencia_panel_pct = st.sidebar.number_input("Eficiencia del Panel (%)", min_value=10.0, max_value=25.0, step=0.1, key="eficiencia_panel_pct",
                                                help="Eficiencia de conversión del módulo, usada para estimar el área aproximada de instalación.")
eficiencia_inversor_pct = st.sidebar.number_input("Eficiencia del Inversor (%)", min_value=90.0, max_value=99.5, value=97.0, step=0.1)
perdidas_sistema_pct = st.sidebar.number_input("Otras Pérdidas del Sistema (%)", min_value=0.0, max_value=25.0, value=9.0, step=0.5,
                                                help="Suciedad/soiling, cableado DC-AC, mismatch entre paneles y disponibilidad. Rango típico 7-12%.")

# --- SIDEBAR: PARÁMETROS - HOJA PERFIL DE CONSUMO ---
st.sidebar.header("⚙️ Parámetros - Hoja Perfil de Consumo")
pct_autosuficiencia = st.sidebar.slider(
    "% Autosuficiencia Solar (Cobertura)", min_value=0.0, max_value=100.0, value=95.0, step=0.5,
    help="Porcentaje del consumo que cubrirá la planta solar. El resto se muestra como aporte de la red."
)
pct_aporte_red = 100.0 - pct_autosuficiencia

potencia_manual = st.sidebar.number_input(
    "Potencia a Instalar Manual (kWp)", min_value=0.0, value=0.0, step=0.1,
    help="Déjalo en 0 para usar la potencia sugerida automáticamente calculada. Si ingresas un valor, este sobreescribe la sugerida en todos los cálculos."
)

st.title("☀️ Sistema de Simulación Fotovoltaica - Latitud Solar")

# --- BLOQUE: CARGA DE DOCUMENTOS PARA AUTO-COMPLETADO ---
st.subheader("📎 Carga de Documentos (Auto-completado)")
if not OCR_DISPONIBLE:
    st.caption("⚠️ OCR no disponible en este entorno (falta tesseract/poppler). Solo se procesarán PDFs con texto seleccionable; fotos o escaneos deberán ingresarse a mano.")

doc1, doc2 = st.columns(2)

with doc1:
    st.markdown("**Ficha Técnica del Panel**")
    archivo_ficha = st.file_uploader("Sube la ficha técnica (PDF, JPG o PNG)", type=["pdf", "jpg", "jpeg", "png"], key="uploader_ficha")
    if archivo_ficha is not None:
        texto_ficha, metodo_ficha = extraer_texto_archivo(archivo_ficha)
        if metodo_ficha == "fallo":
            st.error("No se pudo extraer texto de este archivo. Ingresa los valores manualmente en el sidebar.")
        else:
            datos_panel = extraer_datos_panel(texto_ficha)
            st.caption(f"Método de lectura: {'texto PDF' if metodo_ficha == 'texto_pdf' else 'OCR (imagen/escaneo)'}. Revisa antes de aplicar.")
            st.json({k: v for k, v in datos_panel.items() if v is not None} or {"detectado": "ningún parámetro reconocido"})
            if st.button("📌 Aplicar valores detectados de la ficha técnica", key="btn_aplicar_ficha"):
                if datos_panel["noct"] is not None:
                    st.session_state.noct = datos_panel["noct"]
                if datos_panel["coef_temp_pct"] is not None:
                    st.session_state.coef_temp_pct = datos_panel["coef_temp_pct"]
                if datos_panel["potencia_wp"] is not None:
                    st.session_state.potencia_panel_wp = datos_panel["potencia_wp"]
                if datos_panel["eficiencia_pct"] is not None:
                    st.session_state.eficiencia_panel_pct = datos_panel["eficiencia_pct"]
                st.rerun()

with doc2:
    st.markdown("**Planilla Eléctrica**")
    archivo_planilla = st.file_uploader("Sube la planilla (PDF, JPG o PNG)", type=["pdf", "jpg", "jpeg", "png"], key="uploader_planilla")
    if archivo_planilla is not None:
        texto_planilla, metodo_planilla = extraer_texto_archivo(archivo_planilla)
        if metodo_planilla == "fallo":
            st.error("No se pudo extraer texto de este archivo. Ingresa los valores manualmente.")
        else:
            datos_planilla = extraer_datos_planilla(texto_planilla)
            st.caption(f"Método de lectura: {'texto PDF' if metodo_planilla == 'texto_pdf' else 'OCR (imagen/escaneo)'}. Revisa antes de aplicar.")
            resumen_planilla = {k: v for k, v in datos_planilla.items() if v not in (None, [])}
            st.json(resumen_planilla or {"detectado": "ningún parámetro reconocido"})
            if st.button("📌 Aplicar datos detectados de la planilla", key="btn_aplicar_planilla"):
                if datos_planilla["cliente"]:
                    st.session_state.nombre_cliente = datos_planilla["cliente"]
                if datos_planilla["contrato"]:
                    st.session_state.numero_contrato = datos_planilla["contrato"]
                if datos_planilla["direccion"]:
                    st.session_state.ubicacion_cliente = datos_planilla["direccion"]
                if datos_planilla["consumos_kwh"]:
                    consumos_detectados = datos_planilla["consumos_kwh"]
                    st.session_state.tabla_historico = pd.DataFrame({
                        "Mes": [f"Mes {i+1}" for i in range(len(consumos_detectados))],
                        "Consumo (kWh)": consumos_detectados
                    })
                    st.session_state.consumo_mensual = round(sum(consumos_detectados) / len(consumos_detectados), 2)
                if datos_planilla["valor_pagar"] and datos_planilla["consumos_kwh"]:
                    st.session_state.pago_planilla = datos_planilla["valor_pagar"]
                st.rerun()

# --- BLOQUE: DATOS HISTÓRICOS DE CONSUMO (determina el consumo mensual sugerido) ---
st.subheader("📊 Consumo Histórico del Cliente")
st.caption("Ingresa los meses y consumos reales (ej. de planillas). El promedio se puede usar como Consumo Mensual, que es lo que determina la potencia sugerida de la planta.")

if "tabla_historico" not in st.session_state:
    st.session_state.tabla_historico = pd.DataFrame({
        "Mes": ["Mes 1", "Mes 2", "Mes 3"],
        "Consumo (kWh)": [737.0, 1044.0, 1228.0]
    })

historico_editado = st.data_editor(
    st.session_state.tabla_historico, num_rows="dynamic", use_container_width=True, key="historico_consumo_editor"
)
meses_hist = historico_editado["Mes"].astype(str).tolist()
valores_hist = pd.to_numeric(historico_editado["Consumo (kWh)"], errors="coerce").fillna(0).tolist()
suma_hist = sum(valores_hist)
promedio_hist = suma_hist / len(valores_hist) if valores_hist else 0

h1, h2, h3 = st.columns([1, 1, 1.4])
h1.metric("Σ Suma Total Ingresada", f"{suma_hist:,.0f} kWh")
h2.metric("Promedio Mensual", f"{promedio_hist:,.0f} kWh")
with h3:
    st.write("")
    if st.button("📌 Usar este promedio como Consumo Mensual (kWh/mes)", use_container_width=True):
        st.session_state.consumo_mensual = round(promedio_hist, 2)
        st.rerun()

# --- BLOQUE 1: PARÁMETROS TÉCNICOS ---
with st.container():
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        ciudad_sel = st.selectbox("📍 Ubicación", list(ciudades_data.keys()))
    with col2:
        consumo_mensual = st.number_input("⚡ Consumo (kWh/mes)", key="consumo_mensual")
    with col3:
        pago_planilla = st.number_input("💵 Planilla USD/mes", key="pago_planilla")
        costo_kwh = pago_planilla / consumo_mensual if consumo_mensual > 0 else 0
    with col4:
        deg_y1 = st.number_input("📉 Deg. Año 1 (%)", value=2.0) / 100
    with col5:
        atenuacion = st.number_input("📉 Aten. Anual (%)", value=0.55) / 100

# --- OBTENCIÓN DE DATOS METEOROLÓGICOS (NASA POWER en vivo, o respaldo local) ---
if usar_tiempo_real:
    lat_sel = ciudades_data[ciudad_sel]["lat"]
    lon_sel = ciudades_data[ciudad_sel]["lon"]
    hsp_mensual_nasa, temp_mensual_nasa, exito_nasa = obtener_datos_nasa_power(lat_sel, lon_sel)
    if exito_nasa:
        hsp_avg = sum(hsp_mensual_nasa) / 12
        temp_prom = sum(temp_mensual_nasa) / 12
        fuente_meteo = "NASA POWER — climatología satelital multi-anual (en vivo)"
    else:
        hsp_avg = sum(ciudades_data[ciudad_sel]["hsp"]) / 12
        temp_prom = ciudades_data[ciudad_sel]["temp"]
        fuente_meteo = "Valores de referencia locales (sin conexión a NASA POWER)"
        st.sidebar.warning("⚠️ No se pudo conectar con NASA POWER. Usando valores de referencia locales.")
else:
    hsp_avg = sum(ciudades_data[ciudad_sel]["hsp"]) / 12
    temp_prom = ciudades_data[ciudad_sel]["temp"]
    fuente_meteo = "Valores de referencia locales (Atlas Solar Ecuador / estimación)"

pr_calculado, temp_celda = calcular_pr(temp_prom, noct, coef_temp_pct, perdidas_sistema_pct, eficiencia_inversor_pct)
potencia_sug = consumo_mensual / (hsp_avg * pr_calculado * 30.44)

# Potencia final: usa la manual si fue ingresada (> 0), si no, la sugerida
potencia_final = potencia_manual if potencia_manual > 0 else potencia_sug
generacion_y1 = potencia_final * hsp_avg * pr_calculado * 365

numero_paneles = math.ceil((potencia_final * 1000) / potencia_panel_wp) if potencia_panel_wp > 0 else 0
area_aproximada_m2 = (potencia_final * 1000) / (eficiencia_panel_pct / 100.0 * 1000) if eficiencia_panel_pct > 0 else 0

with st.expander("🔍 Análisis Meteorológico y Técnico", expanded=True):
    st.caption(f"Fuente de datos meteorológicos: **{fuente_meteo}**")
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Potencia Sugerida", f"{potencia_sug:.2f} kWp")
    m2.metric("Potencia Instalada (final)", f"{potencia_final:.2f} kWp",
               delta="Override manual" if potencia_manual > 0 else None)
    m3.metric("HSP Promedio", f"{hsp_avg:.2f} h/día")
    m4.metric("Temp. Celda Estimada", f"{temp_celda:.1f} °C")
    m5.metric("PR (Performance Ratio)", f"{pr_calculado:.2%}")
    n1, n2, n3 = st.columns(3)
    n1.metric("Costo kWh", f"${costo_kwh:.4f}")
    n2.metric("N° de Paneles Estimado", f"{numero_paneles} paneles")
    n3.metric("Área Aproximada", f"{area_aproximada_m2:.1f} m²")

# --- BLOQUE 2: INVERSIÓN Y AHORRO TRIBUTARIO ---
st.subheader("💰 Inversión y Beneficios")
def sync_kwp(): st.session_state.inv_total = st.session_state.costo_kwp * potencia_final
def sync_inv(): st.session_state.costo_kwp = st.session_state.inv_total / potencia_final if potencia_final > 0 else 0

c_inv1, c_inv2, c_inv3 = st.columns(3)
with c_inv1:
    st.number_input("Inversión Total (USD)", key="inv_total", on_change=sync_inv)
with c_inv2:
    st.number_input("Costo por kWp (USD)", key="costo_kwp", on_change=sync_kwp)
with c_inv3:
    años_beneficio = st.number_input("Años a Aplicar el Beneficio Tributario", min_value=1, max_value=10, value=2, step=1)

    if tipo_proyecto == "Comercial":
        porcentaje_distribucion = 100.0 / años_beneficio
        st.info(f"Beneficio: **{porcentaje_distribucion:.2f}%** anual de la Inversión Total por {años_beneficio} año(s).")
    else:
        porcentaje_distribucion = 0.0
        st.info("El beneficio tributario aplica únicamente para proyectos Comerciales.")

# --- BLOQUE 3: FLUJO DE CAJA Y CÁLCULO DE RETORNO ---
inv_final = st.session_state.inv_total
ahorro_trib_anual_usd = inv_final * (porcentaje_distribucion / 100.0)

data_rows, años, acumulados, producciones_anuales = [], [], [], []
balance_acumulado = 0
payback_exacto = None

for año in range(1, 31):
    factor_deg = (1 - deg_y1) * ((1 - atenuacion)**(año-1)) if año > 1 else (1 - deg_y1)
    prod_anual = generacion_y1 * factor_deg
    producciones_anuales.append(prod_anual)
    ahorro_energetico = prod_anual * costo_kwh

    beneficio_extra = ahorro_trib_anual_usd if (año <= años_beneficio and tipo_proyecto == "Comercial") else 0
    total_año = ahorro_energetico + beneficio_extra

    if payback_exacto is None and (balance_acumulado + total_año) >= inv_final:
        remand_por_recuperar = inv_final - balance_acumulado
        payback_exacto = (año - 1) + (remand_por_recuperar / total_año)

    balance_acumulado += total_año
    años.append(año)
    acumulados.append(balance_acumulado)

    data_rows.append({
        "Año": año, "Ind. Deg.": f"-{factor_deg:.3f}", "Prod. kWh": f"{prod_anual:,.0f}",
        "Ahorro Energía": f"${ahorro_energetico:,.2f}", "Ahorro Trib.": f"${beneficio_extra:,.2f}",
        "Ahorro Año": f"${total_año:,.2f}", "Acumulado": f"${balance_acumulado:,.2f}"
    })

energia_total_30_años = sum(producciones_anuales)
tarifa_nivelada = (inv_final / energia_total_30_años) if energia_total_30_años > 0 else 0

# --- BLOQUE DE MÉTRICAS INDICADORAS ---
with st.container():
    st.markdown("### 📊 Análisis de Retorno de Inversión")
    r1, r2, r3 = st.columns(3)

    ahorro_en_y1 = generacion_y1 * (1 - deg_y1) * costo_kwh
    benef_trib_y1 = ahorro_trib_anual_usd if tipo_proyecto == "Comercial" else 0

    r1.metric("Ahorro Año 1 (Suma de Ambos)", f"${(ahorro_en_y1 + benef_trib_y1):,.2f}")
    r2.metric("Inversión a Recuperar", f"${inv_final:,.2f}")

    if payback_exacto:
        if payback_exacto < 1:
            meses = round(payback_exacto * 12)
            texto_retorno = f"{payback_exacto:.2f} años (~ {meses} meses)"
        else:
            texto_retorno = f"{payback_exacto:.2f} años"
    else:
        texto_retorno = "> 30 años"

    r3.metric("⏱️ Tiempo de Recuperación Real", texto_retorno)

# Tabla en la App
st.subheader("📊 Tabla de Proyección")
st.dataframe(pd.DataFrame(data_rows), use_container_width=True)

# --- GRÁFICO MEJORADO ---
st.subheader("📈 Gráfico de Recuperación de Capital")
plt.style.use('ggplot')
fig_app, ax_app = plt.subplots(figsize=(10, 5))

plot_años = [0] + años
plot_acumulados = [0] + acumulados

años_ser = pd.Series(plot_años)
acumulados_ser = pd.Series(plot_acumulados)

ax_app.plot(años_ser, acumulados_ser, color='#1f77b4', marker='o', linewidth=2, label='Ahorro Acumulado (Energía + Tributario)')
ax_app.axhline(y=inv_final, color='#e74c3c', linestyle='--', linewidth=2, label='Línea de Inversión')

ax_app.fill_between(años_ser, acumulados_ser, inv_final, where=(acumulados_ser >= inv_final),
                interpolate=True, color='green', alpha=0.2, label='Ganancia Neta')
ax_app.fill_between(años_ser, acumulados_ser, inv_final, where=(acumulados_ser < inv_final),
                interpolate=True, color='red', alpha=0.1, label='Periodo de Recuperación')

if tipo_proyecto == "Comercial" and años_beneficio > 0:
    ax_app.axvspan(0, años_beneficio, color='#f1c40f', alpha=0.12,
                   label=f'Incentivo Tributario Activo ({años_beneficio} añ.)')

if payback_exacto:
    ax_app.plot(payback_exacto, inv_final, marker='*', markersize=15, color='#f1c40f', label=f'Punto de Equilibrio: {payback_exacto:.2f} años')
    ax_app.annotate(f'Retorno: {payback_exacto:.2f} años', xy=(payback_exacto, inv_final), xytext=(payback_exacto, inv_final * 1.15),
                    fontweight='bold', color='#2c3e50', arrowprops=dict(facecolor='#2c3e50', shrink=0.08, width=1, headwidth=6))

ax_app.set_ylabel("Dólares (USD)")
ax_app.set_xlabel("Años")
ax_app.set_xlim(0, 30.5)
ax_app.yaxis.set_major_formatter(mtick.StrMethodFormatter('${x:,.0f}'))
ax_app.legend(loc='upper left')
st.pyplot(fig_app)

# --- VISTA PREVIA EN APP: NUEVA HOJA "PERFIL DE CONSUMO ENERGÉTICO" ---
st.subheader("📄 Vista Previa: Nueva Hoja - Perfil de Consumo Energético")
pv1, pv2 = st.columns(2)
with pv1:
    fig_hist, ax_hist = plt.subplots(figsize=(5, 3.2))
    colores_barras = ['#95a5a6'] * (len(valores_hist) - 1) + ['#2c3e50'] if valores_hist else []
    ax_hist.bar(meses_hist, valores_hist, color=colores_barras if colores_barras else '#2c3e50')
    ax_hist.axhline(y=promedio_hist, color='red', linewidth=1.5)
    ax_hist.set_ylabel('kWh')
    ax_hist.set_title('Histórico de Consumo Eléctrico', fontsize=10, fontweight='bold')
    st.pyplot(fig_hist)
    st.caption("Análisis del consumo registrado en los últimos periodos.")
with pv2:
    fig_dona, ax_dona = plt.subplots(figsize=(5, 3.2))
    sizes = [pct_autosuficiencia, pct_aporte_red]
    colors_dona = ['#2ecc71', '#bdc3c7']
    ax_dona.pie(sizes, colors=colors_dona, startangle=90, counterclock=False, wedgeprops=dict(width=0.35))
    ax_dona.text(0, 0.08, f"{pct_autosuficiencia:.0f}%", ha='center', va='center', fontsize=22, fontweight='bold', color='#27ae60')
    ax_dona.text(0, -0.18, "AUTOSUFICIENCIA", ha='center', va='center', fontsize=8, color='#555')
    ax_dona.set_title('Cobertura Energética Proyectada', fontsize=10, fontweight='bold')
    ax_dona.legend(['Energía Solar', 'Red (CNEL)'], loc='lower center', bbox_to_anchor=(0.5, -0.15), ncol=2, fontsize=8, frameon=False)
    st.pyplot(fig_dona)

pv3, pv4 = st.columns(2)
with pv3:
    fig_tarifa, ax_tarifa = plt.subplots(figsize=(5, 3.2))
    barras = ax_tarifa.bar(['Red Eléctrica\n(CNEL)', 'Planta Solar\n(Latitud Solar)'], [costo_kwh, tarifa_nivelada], color=['#5d6d7e', '#2ecc71'])
    for b in barras:
        ax_tarifa.annotate(f"${b.get_height():.3f}", xy=(b.get_x() + b.get_width() / 2, b.get_height()),
                            xytext=(0, 4), textcoords="offset points", ha='center', fontweight='bold')
    ax_tarifa.set_ylabel('Tarifa (USD/kWh)')
    st.pyplot(fig_tarifa)
with pv4:
    st.metric("TARIFA ACTUAL (RED CNEL)", f"${costo_kwh:.3f} / kWh")
    st.metric("TARIFA NIVELADA (PLANTA SOLAR)", f"${tarifa_nivelada:.3f} / kWh")

texto_conclusion_preview = (
    f"Al sustituir el {pct_autosuficiencia:.0f}% de la energía proveniente de la red por generación propia, "
    f"el costo efectivo de la energía se desploma de forma garantizada durante los próximos 30 años de vida útil del proyecto."
)
st.markdown(f"**Conclusión Técnica:** {texto_conclusion_preview}")


# --- FUNCIONES AUXILIARES DE DISEÑO PARA EL PDF ---
def agregar_encabezado(pdf):
    if os.path.exists("Negro sobre blanco (1).png"):
        pdf.image("Negro sobre blanco (1).png", x=15, y=12, w=40)

    pdf.set_font('Arial', 'B', 10)
    pdf.set_y(15)
    pdf.cell(0, 5, 'LATITUDSOLAR C.LTDA.', 0, 1, 'C')
    pdf.ln(2)

    pdf.set_font('Arial', 'B', 9)
    pdf.cell(50, 5, '', 0, 0)
    pdf.cell(30, 5, 'RUC', 0, 0, 'R')
    pdf.set_font('Arial', '', 9)
    pdf.cell(40, 5, '0993403111001', 0, 0, 'L')
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(25, 5, 'TELEFONOS:', 0, 0, 'R')
    pdf.set_font('Arial', '', 9)
    pdf.cell(0, 5, '0969952794-0959032257', 0, 1, 'L')
    pdf.ln(8)


def agregar_titulo_principal(pdf, texto):
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, texto, 0, 1, 'C')
    pdf.set_draw_color(31, 119, 180)
    pdf.set_line_width(1)
    pdf.line(30, pdf.get_y(), 180, pdf.get_y())
    pdf.ln(10)


def dibujar_titulo_seccion(pdf, texto):
    y = pdf.get_y()
    pdf.set_fill_color(230, 240, 250)
    pdf.rect(15, y, 180, 10, 'F')
    pdf.set_fill_color(31, 119, 180)
    pdf.rect(15, y, 2, 10, 'F')
    pdf.set_xy(20, y + 1.5)
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(170, 8, texto, 0, 1, 'L')
    pdf.ln(4)


def dibujar_tarjeta_metrica(pdf, x, y, w, h, titulo, valor, color_fondo, color_borde, color_texto):
    pdf.set_fill_color(*color_fondo)
    pdf.set_draw_color(*color_borde)
    pdf.set_line_width(0.4)
    pdf.rect(x, y, w, h, 'DF')
    pdf.set_xy(x + 4, y + 3)
    pdf.set_font('Arial', 'B', 8)
    pdf.set_text_color(90, 90, 90)
    pdf.cell(w - 8, 5, titulo, 0, 1, 'L')
    pdf.set_xy(x + 4, y + 9)
    pdf.set_font('Arial', 'B', 18)
    pdf.set_text_color(*color_texto)
    pdf.cell(w - 8, 10, valor, 0, 0, 'L')


def agregar_pagina_perfil_consumo(pdf):
    """Nueva hoja: PERFIL DE CONSUMO ENERGÉTICO"""
    pdf.add_page()
    agregar_encabezado(pdf)
    agregar_titulo_principal(pdf, 'PERFIL DE CONSUMO ENERGÉTICO')

    archivos_temp = []

    dibujar_titulo_seccion(pdf, '1. DISTRIBUCIÓN Y CAPACIDAD DE GENERACIÓN')
    y_seccion1 = pdf.get_y()

    fig_hist, ax_hist = plt.subplots(figsize=(5, 3.2))
    colores_barras = ['#95a5a6'] * (len(valores_hist) - 1) + ['#2c3e50'] if valores_hist else []
    ax_hist.bar(meses_hist, valores_hist, color=colores_barras if colores_barras else '#2c3e50')
    ax_hist.axhline(y=promedio_hist, color='red', linewidth=1.5)
    ax_hist.set_ylabel('kWh')
    ax_hist.set_title('Histórico de Consumo Eléctrico', fontsize=10, fontweight='bold')
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp1:
        plt.savefig(tmp1.name, dpi=200, bbox_inches='tight')
        ruta_hist = tmp1.name
    plt.close(fig_hist)
    archivos_temp.append(ruta_hist)

    fig_dona, ax_dona = plt.subplots(figsize=(5, 3.2))
    sizes = [pct_autosuficiencia, pct_aporte_red]
    colors_dona = ['#2ecc71', '#bdc3c7']
    ax_dona.pie(sizes, colors=colors_dona, startangle=90, counterclock=False, wedgeprops=dict(width=0.35))
    ax_dona.text(0, 0.08, f"{pct_autosuficiencia:.0f}%", ha='center', va='center', fontsize=22, fontweight='bold', color='#27ae60')
    ax_dona.text(0, -0.18, "AUTOSUFICIENCIA", ha='center', va='center', fontsize=8, color='#555')
    ax_dona.set_title('Cobertura Energética Proyectada', fontsize=10, fontweight='bold')
    ax_dona.legend(['Energía Solar', 'Red (CNEL)'], loc='lower center', bbox_to_anchor=(0.5, -0.15), ncol=2, fontsize=8, frameon=False)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp2:
        plt.savefig(tmp2.name, dpi=200, bbox_inches='tight')
        ruta_dona = tmp2.name
    plt.close(fig_dona)
    archivos_temp.append(ruta_dona)

    pdf.image(ruta_hist, x=15, y=y_seccion1, w=86)
    pdf.image(ruta_dona, x=109, y=y_seccion1, w=86)

    pdf.set_y(y_seccion1 + 65)
    pdf.set_font('Arial', 'I', 8)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(90, 5, 'Análisis del consumo registrado en los últimos periodos.', 0, 0, 'C')
    pdf.ln(12)
    pdf.set_text_color(0, 0, 0)

    dibujar_titulo_seccion(pdf, '2. IMPACTO ECONÓMICO Y REDUCCIÓN TARIFARIA')
    y_seccion2 = pdf.get_y()

    fig_tarifa, ax_tarifa = plt.subplots(figsize=(5, 3.2))
    barras = ax_tarifa.bar(['Red Eléctrica\n(CNEL)', 'Planta Solar\n(Latitud Solar)'], [costo_kwh, tarifa_nivelada], color=['#5d6d7e', '#2ecc71'])
    for b in barras:
        ax_tarifa.annotate(f"${b.get_height():.3f}", xy=(b.get_x() + b.get_width() / 2, b.get_height()),
                            xytext=(0, 4), textcoords="offset points", ha='center', fontweight='bold')
    ax_tarifa.set_ylabel('Tarifa (USD/kWh)')
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp3:
        plt.savefig(tmp3.name, dpi=200, bbox_inches='tight')
        ruta_tarifa = tmp3.name
    plt.close(fig_tarifa)
    archivos_temp.append(ruta_tarifa)

    pdf.image(ruta_tarifa, x=15, y=y_seccion2, w=90)

    dibujar_tarjeta_metrica(
        pdf, x=112, y=y_seccion2, w=83, h=24,
        titulo='TARIFA ACTUAL (RED CNEL)', valor=f"${costo_kwh:.3f} / kWh",
        color_fondo=(230, 233, 236), color_borde=(150, 160, 170), color_texto=(70, 80, 90)
    )
    dibujar_tarjeta_metrica(
        pdf, x=112, y=y_seccion2 + 30, w=83, h=24,
        titulo='TARIFA NIVELADA (PLANTA SOLAR)', valor=f"${tarifa_nivelada:.3f} / kWh",
        color_fondo=(230, 248, 240), color_borde=(46, 204, 113), color_texto=(39, 174, 96)
    )

    pdf.set_y(y_seccion2 + 70)
    pdf.set_font('Arial', 'B', 9.5)
    pdf.set_text_color(0, 0, 0)
    pdf.write(5, 'Conclusión Técnica: ')
    pdf.set_font('Arial', '', 9.5)
    texto_conclusion = (
        f"Al sustituir el {pct_autosuficiencia:.0f}% de la energía proveniente de la red por generación propia, "
        f"el costo efectivo de la energía se desploma de forma garantizada durante los próximos 30 años de vida útil del proyecto."
    )
    pdf.write(5, texto_conclusion)

    for ruta in archivos_temp:
        try:
            os.remove(ruta)
        except OSError:
            pass


# --- FUNCIÓN PDF PRINCIPAL ---
def generar_pdf():
    pdf = FPDF()

    agregar_pagina_perfil_consumo(pdf)

    pdf.add_page()
    pdf.set_margins(15, 15, 15)
    agregar_encabezado(pdf)
    agregar_titulo_principal(pdf, f'PROPUESTA SOLAR - {tipo_proyecto.upper()}')

    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 8, 'DATOS DEL PROYECTO', 0, 1, 'L')
    pdf.set_font('Arial', '', 10)
    pdf.cell(95, 7, f'Cliente: {nombre_cliente}', 0, 0)
    pdf.cell(0, 7, f'Ciudad: {ciudad_sel}', 0, 1)
    pdf.cell(95, 7, f'Proyecto: {n_proyecto}', 0, 0)
    pdf.cell(0, 7, f'N° Contrato: {numero_contrato if numero_contrato else "N/A"}', 0, 1)
    pdf.cell(95, 7, f'Costo kWh: ${costo_kwh:.4f}', 0, 0)
    pdf.cell(0, 7, f'Potencia Instalada: {potencia_final:.2f} kWp', 0, 1)
    pdf.cell(0, 7, f'Ubicación: {ubicacion_cliente if ubicacion_cliente else "N/A"}', 0, 1)

    pdf.ln(8)
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 8, 'RESUMEN FINANCIERO DE RECUPERACIÓN', 0, 1, 'L', fill=True)
    pdf.ln(2)

    if tipo_proyecto == "Comercial":
        explicacion_retorno = (
            f"El retorno de inversión estimado para su proyecto es de solo {payback_exacto:.1f} años. "
            f"Este extraordinario tiempo de recuperación no ocurre de manera aislada, sino como el resultado directo del "
            f"beneficio tributario aplicado por la depreciación acelerada de la planta solar por {años_beneficio} años sumado al ahorro energético acumulado "
            f"de estos mismos años.\n\n"
            f"Al finalizar este período de amortización, la inyección constante de capital liberado de la planilla de energía eléctrica se consolidará "
            f"como un saldo a favor directo y neto para el presupuesto de su empresa. Esto significa ganancias operativas constantes "
            f"que maximizarán la rentabilidad de su negocio durante el resto de los 30 años de vida útil estimada de la planta."
        )
    else:
        explicacion_retorno = (
            f"El retorno de inversión estimado para su residencia es de {payback_exacto:.1f} años. "
            f"Este resultado es el fruto de la sinergia y acumulación directa del ahorro por la autogeneración de energía. "
            f"Al recuperar su capital, la reducción sustancial de su planilla eléctrica se traducirá en un saldo a favor constante "
            f"dentro de su presupuesto mensual, maximizando la liquidez de su hogar por las próximas décadas."
        )

    pdf.set_font('Arial', '', 9.5)
    pdf.multi_cell(0, 5.5, explicacion_retorno)

    pdf.ln(10)
    pdf.set_fill_color(31, 119, 180)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Arial', 'B', 9)
    pdf.set_draw_color(50, 50, 50); pdf.set_line_width(0.2)

    cols_w = [15, 25, 35, 35, 35, 40]
    headers = ['Año', 'Ind. Deg.', 'Prod. kWh', 'Ahorro En.', 'Ahorro Trib.', 'Acumulado']
    for i in range(len(headers)):
        pdf.cell(cols_w[i], 8, headers[i], 1, 0, 'C', fill=True)
    pdf.ln()

    pdf.set_text_color(0, 0, 0); pdf.set_font('Arial', '', 8)
    for row in data_rows:
        if pdf.get_y() > 260:
            pdf.add_page()
            pdf.set_fill_color(31, 119, 180); pdf.set_text_color(255, 255, 255); pdf.set_font('Arial', 'B', 9)
            for i in range(len(headers)):
                pdf.cell(cols_w[i], 8, headers[i], 1, 0, 'C', fill=True)
            pdf.ln()
            pdf.set_text_color(0, 0, 0); pdf.set_font('Arial', '', 8)

        pdf.cell(cols_w[0], 7, str(row['Año']), 1, 0, 'C')
        pdf.cell(cols_w[1], 7, row['Ind. Deg.'], 1, 0, 'C')
        pdf.cell(cols_w[2], 7, row['Prod. kWh'], 1, 0, 'C')
        pdf.cell(cols_w[3], 7, row['Ahorro Energía'], 1, 0, 'C')
        pdf.cell(cols_w[4], 7, row['Ahorro Trib.'], 1, 0, 'C')
        pdf.cell(cols_w[5], 7, row['Acumulado'], 1, 1, 'C')

    pdf.ln(8)

    fig_pdf, ax_pdf = plt.subplots(figsize=(10, 5))
    ax_pdf.plot(años_ser, acumulados_ser, color='#1f77b4', marker='o', linewidth=2, label='Ahorro Acumulado Combinado')
    ax_pdf.axhline(y=inv_final, color='#e74c3c', linestyle='--', linewidth=2, label='Inversión Inicial')

    ax_pdf.fill_between(años_ser, acumulados_ser, inv_final, where=(acumulados_ser >= inv_final),
                        interpolate=True, color='green', alpha=0.2)
    ax_pdf.fill_between(años_ser, acumulados_ser, inv_final, where=(acumulados_ser < inv_final),
                        interpolate=True, color='red', alpha=0.1)

    if tipo_proyecto == "Comercial" and años_beneficio > 0:
        ax_pdf.axvspan(0, años_beneficio, color='#f1c40f', alpha=0.12,
                       label=f'Incentivo Tributario Activo ({años_beneficio} añ.)')

    if payback_exacto:
        ax_pdf.plot(payback_exacto, inv_final, marker='*', markersize=15, color='#f1c40f')
        ax_pdf.annotate(f'Retorno: {payback_exacto:.2f} años', xy=(payback_exacto, inv_final), xytext=(payback_exacto, inv_final * 1.15),
                        fontweight='bold', color='#2c3e50', arrowprops=dict(facecolor='#2c3e50', shrink=0.08, width=1, headwidth=6))

    ax_pdf.set_ylabel("Dólares (USD)")
    ax_pdf.set_xlabel("Años")
    ax_pdf.set_xlim(0, 30.5)
    ax_pdf.yaxis.set_major_formatter(mtick.StrMethodFormatter('${x:,.0f}'))
    ax_pdf.legend(loc='upper left')

    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        plt.savefig(tmp.name, dpi=200, bbox_inches='tight')
        plot_p = tmp.name

    if pdf.get_y() > 160:
        pdf.add_page()

    pdf.image(plot_p, x=15, w=180)
    plt.close(fig_pdf)

    try:
        os.remove(plot_p)
    except OSError:
        pass

    return pdf.output(dest='S').encode('latin-1')


st.sidebar.download_button("📥 Descargar Propuesta PDF", data=generar_pdf(), file_name=f"Propuesta_{nombre_cliente}.pdf")
