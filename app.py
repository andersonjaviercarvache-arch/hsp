import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
from fpdf import FPDF
from PIL import Image as PILImage
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

# --- ACTIVOS FIJOS (logo, fotos de portafolio) ---
# Deben vivir en una carpeta "assets/" junto a este script en el repositorio.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

ARCHIVOS_ASSETS_REQUERIDOS = [
    "logo_portada.png",
]


def _ruta_activo(nombre):
    return os.path.join(ASSETS_DIR, nombre)


def _imagen_segura(pdf, ruta, x, y, w=None, h=None):
    """Inserta una imagen solo si el archivo existe; si falta, no rompe la generación del PDF."""
    if os.path.exists(ruta):
        if w is not None and h is not None:
            pdf.image(ruta, x=x, y=y, w=w, h=h)
        elif w is not None:
            pdf.image(ruta, x=x, y=y, w=w)
        else:
            pdf.image(ruta, x=x, y=y)
        return True
    return False


def _texto_pdf_seguro(texto):
    """Limpia texto proveniente de fuentes externas (planillas OCR, entradas del usuario) para que
    nunca rompa la generación del PDF por un caracter no soportado por la fuente Arial básica
    (que solo admite Latin-1). Reemplaza los símbolos más comunes (guiones largos, comillas
    tipográficas, viñetas, etc.) y descarta cualquier otro caracter no representable."""
    if texto is None:
        return ""
    texto = str(texto)
    reemplazos = {
        "\u2014": "-", "\u2013": "-", "\u2018": "'", "\u2019": "'",
        "\u201c": '"', "\u201d": '"', "\u2026": "...", "\u2022": "-",
        "\u00a0": " ",
    }
    for buscado, reemplazo in reemplazos.items():
        texto = texto.replace(buscado, reemplazo)
    return texto.encode("latin-1", errors="replace").decode("latin-1")


class PropuestaPDF(FPDF):
    """Agrega automáticamente, en TODAS las páginas, el pie de página de confidencialidad y número de hoja."""
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(130, 130, 130)
        self.cell(0, 10, 'Latitud Solar - Propuesta confidencial, de uso exclusivo del destinatario.', 0, 0, 'C')
        self.set_y(-15)
        self.set_x(-25)
        self.set_font('Arial', '', 8)
        self.cell(10, 10, str(self.page_no()), 0, 0, 'R')
        self.set_text_color(0, 0, 0)

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


def _extraer_monto_energia(texto):
    """Extrae el monto que corresponde SOLO al consumo de energía (excluye alumbrado público,
    valores pendientes, intereses, bomberos, IVA, etc.). Busca la(s) línea(s) de 'Energía Activa',
    'Energía Reactiva' y 'Demanda Facturable' (estas últimas dos típicas en tarifas comerciales/
    industriales) y suma el último número de cada línea, que corresponde a la columna Monto ($)."""
    patron_lineas = r"(?:Energ[íi]a\s*Activa[^\n]*|Energ[íi]a\s*Reactiva[^\n]*|Demanda\s*Facturable[^\n]*)"
    lineas = re.findall(patron_lineas, texto, flags=re.IGNORECASE)
    montos = []
    for linea in lineas:
        numeros = re.findall(r"\d+(?:[.,]\d+)?", linea)
        if numeros:
            montos.append(float(numeros[-1].replace(",", ".")))
    return round(sum(montos), 2) if montos else None


def _extraer_valor_total_respaldo(texto):
    """Respaldo si no se pudo aislar el monto de energía: usa el Valor/Total general de la factura."""
    patrones = [
        r"(?:VALOR\s*A\s*PAGAR|VALOR\s*TOTAL\s*A\s*PAGAR|VALOR\s*TOTAL)[^\d]{0,20}(\d[\d.,]*\d|\d)",
        r"(?:TOTAL\s*A\s*PAGAR|TOTAL\s*PLANILLA|TOTAL\s*FACTURA|TOTAL\s*GENERAL|TOTAL\s*USD|IMPORTE\s*A\s*PAGAR|PAGO\s*TOTAL)[^\d]{0,20}(\d[\d.,]*\d|\d)",
    ]
    for patron in patrones:
        coincidencias = re.findall(patron, texto, flags=re.IGNORECASE)
        if coincidencias:
            try:
                return float(coincidencias[-1].replace(",", "."))
            except ValueError:
                pass
    coincidencias_dolar = re.findall(r"\$\s*(\d[\d.,]*\d|\d)", texto)
    if coincidencias_dolar:
        try:
            return float(coincidencias_dolar[-1].replace(",", "."))
        except ValueError:
            pass
    return None


def extraer_datos_planilla(texto):
    """Extrae datos de una planilla eléctrica ecuatoriana (CNEL u otra), best-effort.
    Nota: en varias plantillas de CNEL, el extractor de texto separa las etiquetas de sus valores
    (ej. 'Nombre Cliente' aparece lejos del nombre real). Por eso el cliente/contrato se buscan por
    estructura (número de cuenta contrato seguido del nombre en mayúsculas) en vez de por etiqueta."""
    consumos = [float(x.replace(",", ".")) for x in re.findall(r"(\d{2,5}(?:[.,]\d+)?)\s*kWh", texto, flags=re.IGNORECASE)]

    # Contrato + Cliente: se identifican por estructura (numero largo seguido de un nombre en MAYÚSCULAS)
    m_estructura = re.search(r"\b(\d{9,15})\s*\n\s*([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ ]{9,60})\n", texto)
    contrato = m_estructura.group(1) if m_estructura else _buscar_texto(
        r"(?:N[uú]mero\s*de\s*Cuenta\s*Contrato|Cuenta\s*Contrato|N[°º]?\s*de?\s*Contrato|N[uú]mero\s*de\s*Suministro)[:\s#Nn°º]*([\w\-]{4,20})", texto)
    cliente = m_estructura.group(2).strip() if m_estructura else _buscar_texto(
        r"(?:Nombre\s*del?\s*Cliente|Cliente)[:\s]+([A-ZÁÉÍÓÚÑ][^\n]{3,60})", texto)

    # Dirección: suele ser la línea más larga con separadores "/" típicos de sectores/urbanizaciones
    direccion = None
    candidatas_direccion = re.findall(r"[^\n]{25,180}/[^\n]{3,100}", texto)
    if candidatas_direccion:
        direccion = max(candidatas_direccion, key=len).strip()
    if not direccion:
        direccion = _buscar_texto(r"(?:Direcci[oó]n\s*del?\s*servicio|Direcci[oó]n)[:\s]+([^\n]{5,120})", texto)

    monto_energia = _extraer_monto_energia(texto)
    valor_pagar = monto_energia if monto_energia is not None else _extraer_valor_total_respaldo(texto)

    # Fecha del período facturado (para etiquetar el mes en la tabla histórica): busca "Fecha desde Fecha hasta"
    # seguido de las dos fechas, y toma la segunda (fin del período = mes que se está facturando)
    etiqueta_mes = None
    m_fechas = re.search(r"Fecha\s*desde\s*Fecha\s*hasta[^\d]{0,40}(\d{2}[-/]\d{2}[-/]\d{4})\s+(\d{2}[-/]\d{2}[-/]\d{4})", texto, flags=re.IGNORECASE)
    if m_fechas:
        etiqueta_mes = m_fechas.group(2)

    return {
        "cliente": cliente,
        "contrato": contrato,
        "direccion": direccion,
        "valor_pagar": valor_pagar,
        "consumos_kwh": consumos,
        "etiqueta_mes": etiqueta_mes,
    }


st.set_page_config(page_title="Latitud Solar - Generador de Propuestas", layout="wide")

valores_default = {
    "nombre_cliente": "Martillo Jara Angel Cristobal",
    "costo_kwp": 850.0,
    "consumo_mensual": 1228.0,
    "pago_planilla": 149.94,
    "ubicacion_cliente": "",
    "numero_contrato": "",
    "n_proyecto": "P0000000010",
    "ciudad_sel": "Guayaquil",
    "tipo_proyecto": "Residencial",
    "vendedor": "Ing. Solar",
    "usar_tiempo_real": True,
    "pct_autosuficiencia": 95.0,
    "potencia_manual": 0.0,
    "potencia_panel_wp": 625.0,
    "area_panel_m2": 2.74,
    "deg_y1_pct": 2.0,
    "atenuacion_pct": 0.55,
    "anios_beneficio": 2,
    "modo_manual": False,
}
for _clave, _valor in valores_default.items():
    if _clave not in st.session_state:
        st.session_state[_clave] = _valor

# --- SIDEBAR PASO 1: CARGA DE LA PLANILLA (debe ejecutarse ANTES que cualquier widget con las mismas claves) ---
st.sidebar.header("📄 Paso 1: Sube tu Planilla Eléctrica")
if not OCR_DISPONIBLE:
    st.sidebar.caption("⚠️ OCR no disponible en este entorno (falta tesseract/poppler). Solo se procesarán PDFs con texto seleccionable; fotos o escaneos deberán ingresarse a mano.")

archivo_planilla = st.sidebar.file_uploader("Sube la planilla (PDF, JPG o PNG)", type=["pdf", "jpg", "jpeg", "png"], key="uploader_planilla")

if archivo_planilla is not None:
    texto_planilla, metodo_planilla = extraer_texto_archivo(archivo_planilla)
    if metodo_planilla == "fallo":
        st.sidebar.error("No se pudo leer este archivo (ni texto ni OCR). Ingresa los valores manualmente abajo.")
    else:
        datos_planilla = extraer_datos_planilla(texto_planilla)
        with st.sidebar.expander("👁️ Vista previa de lo detectado", expanded=True):
            st.markdown(f"**Cliente:** {datos_planilla['cliente'] or '❌ No detectado'}")
            st.markdown(f"**Contrato:** {datos_planilla['contrato'] or '❌ No detectado'}")
            st.markdown(f"**Dirección:** {datos_planilla['direccion'] or '❌ No detectado'}")
            st.markdown(f"**Monto:** {datos_planilla['valor_pagar'] if datos_planilla['valor_pagar'] is not None else '❌ No detectado'}")
            st.markdown(f"**Consumo (kWh):** {datos_planilla['consumos_kwh'] or '❌ No detectado'}")
            if not datos_planilla['cliente'] or not datos_planilla['contrato'] or not datos_planilla['direccion']:
                st.caption("⚠️ Algún campo no se detectó — al aplicar, ese campo específico se deja tal cual estaba (no se borra). Si esto se repite con tus planillas, compárteme el texto para ajustar el patrón.")
        if st.sidebar.button("✅ Aplicar Datos de esta Planilla", key="btn_aplicar_planilla", use_container_width=True):
            if datos_planilla["cliente"]:
                st.session_state.nombre_cliente = datos_planilla["cliente"]
            if datos_planilla["contrato"]:
                st.session_state.numero_contrato = datos_planilla["contrato"]
            if datos_planilla["direccion"]:
                st.session_state.ubicacion_cliente = datos_planilla["direccion"]
            if datos_planilla["consumos_kwh"]:
                # Cada planilla trae normalmente UN solo mes de consumo (el período facturado).
                # Por eso se AGREGA como fila nueva a la tabla histórica en vez de reemplazarla,
                # para ir acumulando el historial de varios meses a medida que subes más planillas.
                consumo_mes = sum(datos_planilla["consumos_kwh"])  # si hay más de un valor en la misma planilla, se suman
                etiqueta = datos_planilla.get("etiqueta_mes")

                tabla_actual = st.session_state.tabla_historico
                es_tabla_de_ejemplo = (
                    len(tabla_actual) == 3
                    and list(tabla_actual["Mes"]) == ["Mes 1", "Mes 2", "Mes 3"]
                    and list(tabla_actual["Consumo (kWh)"]) == [737.0, 1044.0, 1228.0]
                )
                if es_tabla_de_ejemplo:
                    tabla_actual = pd.DataFrame({"Mes": [], "Consumo (kWh)": []})

                if not etiqueta:
                    etiqueta = f"Mes {len(tabla_actual) + 1}"

                fila_nueva = pd.DataFrame({"Mes": [etiqueta], "Consumo (kWh)": [consumo_mes]})
                tabla_actualizada = pd.concat([tabla_actual, fila_nueva], ignore_index=True)
                tabla_actualizada = tabla_actualizada.drop_duplicates(subset="Mes", keep="last").reset_index(drop=True)

                st.session_state.tabla_historico = tabla_actualizada
                st.session_state.consumo_mensual = round(tabla_actualizada["Consumo (kWh)"].mean(), 2)
            if datos_planilla["valor_pagar"]:
                st.session_state.pago_planilla = datos_planilla["valor_pagar"]
            st.sidebar.success("✅ Datos aplicados — revisa los campos abajo.")
            st.rerun()

# --- SIDEBAR: INFORMACIÓN DEL CLIENTE (solo en Modo Manual) ---
if st.session_state.modo_manual:
    st.sidebar.header("📋 Información del Cliente")
    nombre_cliente = st.sidebar.text_input("Nombre del Cliente", key="nombre_cliente")
    n_proyecto = st.sidebar.text_input("Número de Proyecto", key="n_proyecto")
    numero_contrato = st.sidebar.text_input("N° de Contrato / Cuenta", key="numero_contrato")
    ubicacion_cliente = st.sidebar.text_input("📍 Ubicación / Dirección del Proyecto", key="ubicacion_cliente")
    tipo_proyecto = st.sidebar.selectbox("Tipo de Proyecto", ["Residencial", "Comercial"], key="tipo_proyecto")
    vendedor = st.sidebar.text_input("Asesor Comercial", key="vendedor")
else:
    nombre_cliente = st.session_state.nombre_cliente
    n_proyecto = st.session_state.n_proyecto
    numero_contrato = st.session_state.numero_contrato
    ubicacion_cliente = st.session_state.ubicacion_cliente
    tipo_proyecto = st.session_state.tipo_proyecto
    vendedor = st.session_state.vendedor

# --- SIDEBAR: METEOROLOGÍA (solo en Modo Manual) ---
if st.session_state.modo_manual:
    st.sidebar.header("🌐 Meteorología")
    usar_tiempo_real = st.sidebar.checkbox(
        "Usar meteorología en tiempo real (NASA POWER)", key="usar_tiempo_real",
        help="Consulta climatología satelital multi-anual real por coordenadas. Si falla la conexión, se usan valores de referencia locales."
    )
else:
    usar_tiempo_real = st.session_state.usar_tiempo_real

# --- SIDEBAR: PARÁMETROS - HOJA PERFIL DE CONSUMO (solo en Modo Manual) ---
if st.session_state.modo_manual:
    st.sidebar.header("⚙️ Parámetros - Hoja Perfil de Consumo")
    pct_autosuficiencia = st.sidebar.slider(
        "% Autosuficiencia Solar (Cobertura)", min_value=0.0, max_value=100.0, step=0.5, key="pct_autosuficiencia",
        help="Porcentaje del consumo que cubrirá la planta solar. El resto se muestra como aporte de la red."
    )
    potencia_manual = st.sidebar.number_input(
        "Potencia a Instalar Manual (kWp)", min_value=0.0, step=0.1, key="potencia_manual",
        help="Déjalo en 0 para usar la potencia sugerida automáticamente calculada. Si ingresas un valor, este sobreescribe la sugerida en todos los cálculos."
    )
else:
    pct_autosuficiencia = st.session_state.pct_autosuficiencia
    potencia_manual = st.session_state.potencia_manual
pct_aporte_red = 100.0 - pct_autosuficiencia

# --- SIDEBAR: COMPONENTES DEL SISTEMA (solo en Modo Manual) ---
if st.session_state.modo_manual:
    st.sidebar.header("🔧 Componentes del Sistema")
    potencia_panel_wp = st.sidebar.number_input(
        "Potencia por Panel (Wp)", min_value=100.0, max_value=1000.0, step=5.0, key="potencia_panel_wp",
        help="Potencia nominal de un solo panel. Se usa para calcular el número de módulos necesarios."
    )
    area_panel_m2 = st.sidebar.number_input(
        "Área por Panel (m²)", min_value=1.0, max_value=5.0, step=0.01, key="area_panel_m2",
        help="Área física de un solo panel (típico ~2.6-2.8 m² en paneles grandes de 600+ Wp)."
    )
else:
    potencia_panel_wp = st.session_state.potencia_panel_wp
    area_panel_m2 = st.session_state.area_panel_m2

# --- SIDEBAR: FOTOS ESPECÍFICAS DEL PROYECTO (editables, distintas para cada cliente) ---
st.sidebar.header("📷 Fotos de este Proyecto")
st.sidebar.caption("A diferencia de 'Casos de éxito' (fijas), estas fotos son propias de cada techo/proyecto.")
foto_ahorro_subida = st.sidebar.file_uploader(
    "Foto del techo (página Propuesta de Ahorro)", type=["jpg", "jpeg", "png"], key="uploader_foto_ahorro"
)
foto_cubierta_antes_subida = st.sidebar.file_uploader(
    "Foto Distribución a Cubierta — Antes", type=["jpg", "jpeg", "png"], key="uploader_cubierta_antes"
)
foto_cubierta_despues_subida = st.sidebar.file_uploader(
    "Foto Distribución a Cubierta — Después", type=["jpg", "jpeg", "png"], key="uploader_cubierta_despues"
)


def _guardar_temporal(archivo_subido):
    """Guarda un archivo subido por el usuario en un archivo temporal y devuelve su ruta (o None)."""
    if archivo_subido is None:
        return None
    sufijo = os.path.splitext(archivo_subido.name)[1] or ".jpg"
    with tempfile.NamedTemporaryFile(delete=False, suffix=sufijo) as tmp:
        tmp.write(archivo_subido.getvalue())
        return tmp.name


ruta_foto_ahorro_subida = _guardar_temporal(foto_ahorro_subida)
ruta_foto_cubierta_antes_subida = _guardar_temporal(foto_cubierta_antes_subida)
ruta_foto_cubierta_despues_subida = _guardar_temporal(foto_cubierta_despues_subida)

st.title("☀️ Sistema de Simulación Fotovoltaica - Latitud Solar")

col_modo1, col_modo2 = st.columns([4, 1])
with col_modo2:
    st.toggle("🔧 Modo Manual", key="modo_manual", help="Muestra todos los controles avanzados para ajustar cada parámetro a mano.")

if not st.session_state.modo_manual:
    st.caption("Modo simple: sube tu planilla y las fotos del proyecto, y descarga la propuesta ya calculada. Activa el 'Modo Manual' si quieres ajustar los parámetros a mano.")

# --- DIAGNÓSTICO: verificar que la carpeta assets/ esté completa (logo) ---
_faltantes = [f for f in ARCHIVOS_ASSETS_REQUERIDOS if not os.path.exists(_ruta_activo(f))]
if _faltantes:
    st.error(
        f"⚠️ Faltan {len(_faltantes)} de {len(ARCHIVOS_ASSETS_REQUERIDOS)} archivos en la carpeta `assets/` "
        f"(por eso la portada del PDF sale en blanco).\n\n"
        f"Ruta donde se está buscando: `{ASSETS_DIR}`\n\n"
        f"Archivos faltantes: {', '.join(_faltantes)}"
    )

# --- BLOQUE: DATOS HISTÓRICOS DE CONSUMO (determina el consumo mensual sugerido) ---
if "tabla_historico" not in st.session_state:
    st.session_state.tabla_historico = pd.DataFrame({
        "Mes": ["Mes 1", "Mes 2", "Mes 3"],
        "Consumo (kWh)": [737.0, 1044.0, 1228.0]
    })

if st.session_state.modo_manual:
    st.subheader("📊 Consumo Histórico del Cliente")
    st.caption("Ingresa los meses y consumos reales (ej. de planillas). El promedio se puede usar como Consumo Mensual, que es lo que determina la potencia sugerida de la planta.")

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
else:
    historico_editado = st.session_state.tabla_historico
    meses_hist = historico_editado["Mes"].astype(str).tolist()
    valores_hist = pd.to_numeric(historico_editado["Consumo (kWh)"], errors="coerce").fillna(0).tolist()
    suma_hist = sum(valores_hist)
    promedio_hist = suma_hist / len(valores_hist) if valores_hist else 0

# --- BLOQUE 1: PARÁMETROS TÉCNICOS ---
if st.session_state.modo_manual:
    with st.container():
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            ciudad_sel = st.selectbox("📍 Ubicación", list(ciudades_data.keys()), key="ciudad_sel")
        with col2:
            consumo_mensual = st.number_input("⚡ Consumo (kWh/mes)", key="consumo_mensual")
        with col3:
            pago_planilla = st.number_input("💵 Planilla USD/mes", key="pago_planilla")
            costo_kwh = pago_planilla / consumo_mensual if consumo_mensual > 0 else 0
        with col4:
            deg_y1 = st.number_input("📉 Deg. Año 1 (%)", key="deg_y1_pct") / 100
        with col5:
            atenuacion = st.number_input("📉 Aten. Anual (%)", key="atenuacion_pct") / 100
else:
    ciudad_sel = st.session_state.ciudad_sel
    consumo_mensual = st.session_state.consumo_mensual
    pago_planilla = st.session_state.pago_planilla
    costo_kwh = pago_planilla / consumo_mensual if consumo_mensual > 0 else 0
    deg_y1 = st.session_state.deg_y1_pct / 100
    atenuacion = st.session_state.atenuacion_pct / 100

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

pr_calculado = 0.82 - (max(0, temp_prom - 15) * 0.0045)
potencia_sug = consumo_mensual / (hsp_avg * pr_calculado * 30.44)

# Potencia final: usa la manual si fue ingresada (> 0), si no, la sugerida
potencia_final = potencia_manual if potencia_manual > 0 else potencia_sug
generacion_y1 = potencia_final * hsp_avg * pr_calculado * 365

numero_paneles = math.ceil((potencia_final * 1000) / potencia_panel_wp) if potencia_panel_wp > 0 else 0
area_total_paneles_m2 = numero_paneles * area_panel_m2

if "inv_total" not in st.session_state:
    st.session_state.inv_total = st.session_state.costo_kwp * potencia_final

if st.session_state.modo_manual:
    with st.expander("🔍 Análisis Meteorológico y Técnico", expanded=True):
        st.caption(f"Fuente de datos meteorológicos: **{fuente_meteo}**")
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Potencia Sugerida", f"{potencia_sug:.2f} kWp")
        m2.metric("Potencia Instalada (final)", f"{potencia_final:.2f} kWp",
                   delta="Override manual" if potencia_manual > 0 else None)
        m3.metric("HSP Promedio", f"{hsp_avg:.2f} h/día")
        m4.metric("PR (Factor de Corrección)", f"{pr_calculado:.2%}")
        m5.metric("Costo kWh", f"${costo_kwh:.4f}")

# --- BLOQUE 2: INVERSIÓN Y AHORRO TRIBUTARIO ---
def sync_kwp(): st.session_state.inv_total = st.session_state.costo_kwp * potencia_final
def sync_inv(): st.session_state.costo_kwp = st.session_state.inv_total / potencia_final if potencia_final > 0 else 0

if st.session_state.modo_manual:
    st.subheader("💰 Inversión y Beneficios")
    c_inv1, c_inv2, c_inv3 = st.columns(3)
    with c_inv1:
        st.number_input("Inversión Total (USD)", key="inv_total", on_change=sync_inv)
    with c_inv2:
        st.number_input("Costo por kWp (USD)", key="costo_kwp", on_change=sync_kwp)
    with c_inv3:
        años_beneficio = st.number_input("Años a Aplicar el Beneficio Tributario", min_value=1, max_value=10, step=1, key="anios_beneficio")

        if tipo_proyecto == "Comercial":
            porcentaje_distribucion = 100.0 / años_beneficio
            st.info(f"Beneficio: **{porcentaje_distribucion:.2f}%** anual de la Inversión Total por {años_beneficio} año(s).")
        else:
            porcentaje_distribucion = 0.0
            st.info("El beneficio tributario aplica únicamente para proyectos Comerciales.")
else:
    años_beneficio = st.session_state.anios_beneficio
    porcentaje_distribucion = (100.0 / años_beneficio) if tipo_proyecto == "Comercial" else 0.0

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

# --- Series usadas también por el PDF (deben calcularse siempre, independientemente del modo) ---
plot_años = [0] + años
plot_acumulados = [0] + acumulados
años_ser = pd.Series(plot_años)
acumulados_ser = pd.Series(plot_acumulados)

if st.session_state.modo_manual:
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

if st.session_state.modo_manual:
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
        ax_dona.pie(sizes, colors=colors_dona, startangle=90, counterclock=False, wedgeprops=dict(width=0.35),
                    autopct='%1.0f%%', pctdistance=0.82, textprops={'fontsize': 8, 'fontweight': 'bold', 'color': '#333'})
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
def _alto_imagen_mm(ruta, ancho_mm):
    """Calcula la altura real (en mm) que tendrá una imagen al insertarla con un ancho fijo,
    a partir de sus dimensiones reales en píxeles. Evita solapamientos cuando una imagen
    (ej. una que incluye leyenda) resulta más alta de lo esperado."""
    with PILImage.open(ruta) as img:
        w_px, h_px = img.size
    return ancho_mm * (h_px / w_px)


def agregar_encabezado(pdf):
    ruta_logo = _ruta_activo("logo_portada.png")
    if os.path.exists(ruta_logo):
        alto_logo = _alto_imagen_mm(ruta_logo, 32)
        pdf.image(ruta_logo, x=15, y=10, w=32, h=alto_logo)

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
    pdf.cell(25, 5, 'T ELEFONOS:', 0, 0, 'R')
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


# --- PÁGINA: PORTADA ---
def agregar_pagina_portada(pdf, potencia_kwp):
    pdf.add_page()
    pdf.set_y(90)
    ruta_logo = _ruta_activo("logo_portada.png")
    if os.path.exists(ruta_logo):
        alto_logo = _alto_imagen_mm(ruta_logo, 130)
        pdf.image(ruta_logo, x=(210 - 130) / 2, y=90, w=130)
        pdf.set_y(90 + alto_logo + 15)
    else:
        pdf.set_font('Arial', 'B', 26)
        pdf.cell(0, 15, 'Latitud Solar', 0, 1, 'C')
        pdf.ln(10)

    pdf.set_font('Arial', 'B', 18)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, f'PROPUESTA TÉCNICA ECONÓMICA {potencia_kwp:.0f}KWP', 0, 1, 'C')


# --- PÁGINAS: CASOS DE ÉXITO (fijas, siempre las mismas fotos de portafolio) ---
def _encabezado_casos_exito(pdf):
    ruta_icono = _ruta_activo("logo_icono.png")
    if os.path.exists(ruta_icono):
        pdf.image(ruta_icono, x=15, y=15, w=14)
    pdf.set_xy(32, 17)
    pdf.set_font('Arial', 'B', 11)
    pdf.set_text_color(20, 20, 20)
    pdf.cell(0, 5, 'LATITUDSOLAR', 0, 2, 'L')
    pdf.set_x(32)
    pdf.cell(0, 5, 'C.LTDA.', 0, 1, 'L')

    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(31, 119, 180)
    pdf.set_xy(120, 20)
    pdf.cell(75, 8, 'Casos de éxito', 0, 1, 'R')
    pdf.set_text_color(0, 0, 0)


def _pie_pagina_contacto(pdf):
    pdf.set_y(275)
    pdf.set_font('Arial', '', 9)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(0, 5, '0969952794', 0, 1, 'L')
    pdf.cell(0, 5, 'ventas@latitudsolarecuador.com', 0, 1, 'L')
    pdf.set_text_color(0, 0, 0)


def agregar_pagina_casos_exito(pdf, fotos):
    """fotos: lista de rutas de imagen (hasta 4), organizadas en 2 filas de 2.
    Nota: algunas de estas imágenes son en realidad un collage de 2 fotos combinadas en un solo
    archivo (así vienen del material original), y varían bastante en proporción (unas panorámicas,
    otras verticales). Por eso, para cada fila, se calcula la altura que hace que el ancho total
    de sus 2 fotos llene exactamente el ancho disponible de la página — sin distorsionar ninguna
    y sin que ninguna se salga del margen."""
    pdf.add_page()
    _encabezado_casos_exito(pdf)

    ANCHO_DISPONIBLE = 180
    GAP_X = 6
    GAP_Y = 14
    y = 45

    for i in range(0, len(fotos), 2):
        par = fotos[i:i + 2]
        proporciones = []
        for ruta in par:
            ruta_completa = _ruta_activo(ruta)
            if os.path.exists(ruta_completa):
                with PILImage.open(ruta_completa) as img:
                    w_px, h_px = img.size
                proporciones.append(w_px / h_px)
            else:
                proporciones.append(None)

        suma_proporciones = sum(p for p in proporciones if p) or 1
        alto_fila = (ANCHO_DISPONIBLE - GAP_X) / suma_proporciones

        x = 15
        for ruta, prop in zip(par, proporciones):
            if prop is None:
                continue
            ruta_completa = _ruta_activo(ruta)
            try:
                ancho = alto_fila * prop
                pdf.image(ruta_completa, x=x, y=y, w=ancho, h=alto_fila)
                x += ancho + GAP_X
            except Exception:
                pass
        y += alto_fila + GAP_Y

    _pie_pagina_contacto(pdf)




# --- PÁGINA: PROPUESTA DE AHORRO ---
def agregar_pagina_propuesta_ahorro(pdf, nombre_cliente, potencia_final, numero_paneles, potencia_panel_wp,
                                     area_total_m2, respaldo_kw, inv_final, ahorro_vida_util, payback_exacto,
                                     ruta_foto_techo=None):
    pdf.add_page()
    agregar_encabezado(pdf)
    agregar_titulo_principal(pdf, 'PROPUESTA DE AHORRO')

    pdf.set_font('Arial', '', 10.5)
    texto_intro = (
        f"Propuesta técnica y económica para la implementación de una planta solar fotovoltaica On-Grid "
        f"con respaldo de energía, diseñada para optimizar los costos energéticos y promover la sostenibilidad "
        f"de la residencia de {_texto_pdf_seguro(nombre_cliente).upper()}."
    )
    pdf.multi_cell(0, 6, texto_intro)
    pdf.ln(4)

    if ruta_foto_techo and os.path.exists(ruta_foto_techo):
        ancho_foto = 130
        alto_foto = _alto_imagen_mm(ruta_foto_techo, ancho_foto)
        x_foto = (210 - ancho_foto) / 2
        y_foto = pdf.get_y()
        pdf.image(ruta_foto_techo, x=x_foto, y=y_foto, w=ancho_foto)
        pdf.set_draw_color(220, 30, 30)
        pdf.set_line_width(1)
        pdf.rect(x_foto, y_foto, ancho_foto, alto_foto)
        pdf.set_y(y_foto + alto_foto + 8)
    else:
        pdf.ln(11)

    filas = [
        ("Potencia FV", f"{potencia_final:.0f} kWp"),
        ("Total de módulos", f"{numero_paneles} unidades"),
        ("Área de los módulos", f"{area_total_m2:,.2f} m²"),
        ("Respaldo de cargas críticas", f"{respaldo_kw:.0f} kW/h"),
        ("Vida útil y producción de energía", "30 años"),
        ("Costo de planta solar", f"{inv_final:,.2f} USD"),
        ("Ahorro en vida útil", f"${ahorro_vida_util:,.2f} USD"),
        ("Recuperación de inversión", f"{payback_exacto:.1f} años" if payback_exacto else "N/A"),
    ]

    if pdf.get_y() > 230:
        pdf.add_page()
        agregar_encabezado(pdf)

    y_tabla = pdf.get_y()
    ancho_tabla = 180
    pdf.set_fill_color(31, 119, 180)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Arial', 'B', 10)
    pdf.set_xy(15, y_tabla)
    pdf.cell(90, 9, 'Parámetro', 0, 0, 'L', fill=True)
    pdf.cell(90, 9, 'Unidades / Valor', 0, 1, 'L', fill=True)

    pdf.set_font('Arial', '', 10)
    for i, (parametro, valor) in enumerate(filas):
        es_ahorro_vida_util = parametro == "Ahorro en vida útil"
        if es_ahorro_vida_util:
            color_fondo = (163, 219, 190)
        elif i % 2 == 0:
            color_fondo = (245, 246, 247)
        else:
            color_fondo = (255, 255, 255)
        pdf.set_fill_color(*color_fondo)
        pdf.set_text_color(50, 50, 50) if es_ahorro_vida_util else pdf.set_text_color(90, 90, 90)
        pdf.set_font('Arial', 'B', 10) if es_ahorro_vida_util else pdf.set_font('Arial', '', 10)
        pdf.cell(90, 9, parametro, 0, 0, 'L', fill=True)
        pdf.set_text_color(39, 174, 96)
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(90, 9, valor, 0, 1, 'L', fill=True)
        pdf.set_font('Arial', '', 10)
    pdf.set_text_color(0, 0, 0)


# --- PÁGINA: DISTRIBUCIÓN A CUBIERTA (fotos editables, propias de cada proyecto) ---
def agregar_pagina_distribucion_cubierta(pdf, ruta_foto_antes=None, ruta_foto_despues=None):
    pdf.add_page()
    agregar_encabezado(pdf)
    agregar_titulo_principal(pdf, 'DISTRIBUCIÓN A CUBIERTA')

    y = pdf.get_y()

    if ruta_foto_antes and os.path.exists(ruta_foto_antes):
        ancho = 180
        alto = _alto_imagen_mm(ruta_foto_antes, ancho)
        pdf.image(ruta_foto_antes, x=(210 - ancho) / 2, y=y, w=ancho)
        y += alto + 10

    if ruta_foto_despues and os.path.exists(ruta_foto_despues):
        ancho = 180
        alto = _alto_imagen_mm(ruta_foto_despues, ancho)
        pdf.image(ruta_foto_despues, x=(210 - ancho) / 2, y=y, w=ancho)
    # Si no se sube ninguna foto, la página queda solo con el título (plantilla vacía).


# --- PÁGINA: ALCANCE DE SUMINISTRO Y COMPONENTES ---
def agregar_pagina_alcance_suministro(pdf, potencia_final, numero_paneles, potencia_panel_wp):
    pdf.add_page()
    agregar_encabezado(pdf)
    agregar_titulo_principal(pdf, 'ALCANCE DE SUMINISTRO Y COMPONENTES')

    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 8, '1. ALCANCE DEL PROYECTO', 0, 1, 'L')
    pdf.set_font('Arial', '', 10)
    texto_alcance = (
        f"El proyecto comprende la ejecución integral de un sistema de generación fotovoltaica de "
        f"{potencia_final:.0f}KWP bajo la modalidad \"llave en mano\", que incluye desde la ingeniería, "
        f"suministro y montaje, hasta la gestión administrativa necesaria para la puesta en marcha legal "
        f"ante la empresa eléctrica CNEL."
    )
    pdf.multi_cell(0, 6, texto_alcance)
    pdf.ln(6)

    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 8, '3. Tabla de Suministro y Componentes', 0, 1, 'L')

    componentes = [
        ("Paneles Solares", f"{numero_paneles} unidades (Longi, Trina o Yingli) de {potencia_panel_wp:.0f}Wp", "Incluido"),
        ("Inversores", "Sistema de inversores híbridos con inyección a red y respaldo.", "Incluido"),
        ("Estructura de Montaje", "Aluminio anodizado (mid/end clamps y tornillería)", "Incluido"),
        ("Protecciones Eléctricas", "Tableros de protección en DC y AC", "Incluido"),
        ("Canalización y Cableado", "Cableado fotovoltaico y tubería", "Incluido"),
        ("Sistema de Monitoreo", "Sistema de monitoreo remoto", "Incluido"),
        ("Gestión de Medidor", "Tramitación legal ante CNEL", "Incluido"),
        ("Instalación y Puesta en Marcha", "Mano de obra especializada", "Incluido"),
        ("Inducción y Capacitación", "Sesión técnica", "Incluido"),
        ("Mantenimiento", "Primer año de mantenimiento preventivo", "Gratis"),
    ]

    anchos = [45, 105, 30]
    pdf.set_fill_color(31, 119, 180)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Arial', 'B', 9.5)
    pdf.cell(anchos[0], 9, 'Componente / Servicio', 0, 0, 'L', fill=True)
    pdf.cell(anchos[1], 9, 'Cantidad / Especificación', 0, 0, 'L', fill=True)
    pdf.cell(anchos[2], 9, 'Estado', 0, 1, 'C', fill=True)

    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', '', 9)
    for i, (comp, espec, estado) in enumerate(componentes):
        if pdf.get_y() > 265:
            pdf.add_page()
            agregar_encabezado(pdf)
        y_ini = pdf.get_y()
        if i % 2 == 0:
            pdf.set_fill_color(245, 246, 247)
        else:
            pdf.set_fill_color(255, 255, 255)
        pdf.multi_cell(anchos[0], 7, comp, 0, 'L', fill=True)
        y_fin_izq = pdf.get_y()
        pdf.set_xy(15 + anchos[0], y_ini)
        pdf.multi_cell(anchos[1], 7, espec, 0, 'L', fill=True)
        y_fin_centro = pdf.get_y()
        alto_fila = max(y_fin_izq, y_fin_centro) - y_ini
        pdf.set_xy(15 + anchos[0] + anchos[1], y_ini)
        pdf.cell(anchos[2], alto_fila, estado, 0, 1, 'C', fill=True)
        pdf.set_y(max(y_fin_izq, y_fin_centro))


# --- PÁGINA: RESUMEN FINAL SIMPLIFICADO (tabla ejecutiva + saldo a favor) ---
def agregar_pagina_resumen_final(pdf, tipo_proyecto, payback_exacto, ahorro_vida_util, inv_final, data_rows):
    pdf.add_page()
    agregar_encabezado(pdf)
    agregar_titulo_principal(pdf, f'PROPUESTA SOLAR - {tipo_proyecto.upper()}')

    saldo_favor = ahorro_vida_util - inv_final
    pdf.set_font('Arial', '', 10.5)
    texto_resumen = (
        f"La inversión se recupera en {payback_exacto:.1f} años solo con el ahorro energético. "
        f"Al trigésimo año el beneficio acumulado será de ${ahorro_vida_util:,.2f}, dejando un saldo a favor "
        f"neto constante que maximizará la liquidez durante los 30 años de vida útil de la planta solar."
    ) if payback_exacto else "Proyección de ahorro a 30 años."
    pdf.multi_cell(0, 6, texto_resumen)
    pdf.ln(4)

    headers = ['Año', 'Ahorro Energético', 'Ahorro Tributario', 'Ahorro Total Anual', 'Ahorro Acumulado']
    anchos = [20, 40, 40, 40, 40]
    pdf.set_fill_color(31, 119, 180)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Arial', 'B', 9)
    for i, h in enumerate(headers):
        pdf.cell(anchos[i], 8, h, 1, 0, 'C', fill=True)
    pdf.ln()

    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', '', 8.5)
    for row in data_rows:
        if pdf.get_y() > 260:
            pdf.add_page()
            agregar_encabezado(pdf)
            pdf.set_fill_color(31, 119, 180); pdf.set_text_color(255, 255, 255); pdf.set_font('Arial', 'B', 9)
            for i, h in enumerate(headers):
                pdf.cell(anchos[i], 8, h, 1, 0, 'C', fill=True)
            pdf.ln()
            pdf.set_text_color(0, 0, 0); pdf.set_font('Arial', '', 8.5)
        pdf.cell(anchos[0], 7, f"Año {row['Año']}", 1, 0, 'C')
        pdf.cell(anchos[1], 7, row['Ahorro Energía'], 1, 0, 'C')
        pdf.cell(anchos[2], 7, row['Ahorro Trib.'], 1, 0, 'C')
        pdf.cell(anchos[3], 7, row['Ahorro Año'], 1, 0, 'C')
        pdf.cell(anchos[4], 7, row['Acumulado'], 1, 1, 'C')

    pdf.ln(4)
    ancho_resumen = sum(anchos)
    filas_resumen = [
        ("Capital Total Ahorrado", f"${ahorro_vida_util:,.2f}", True),
        ("Inversión Inicial Estimada", f"-${inv_final:,.2f}", False),
        ("Saldo a Favor Neto", f"${saldo_favor:,.2f}", True),
        ("Retorno de Inversión", f"{payback_exacto:.1f} años" if payback_exacto else "N/A", False),
    ]
    for etiqueta, valor, negrita in filas_resumen:
        if pdf.get_y() > 270:
            pdf.add_page()
            agregar_encabezado(pdf)
        pdf.set_font('Arial', 'B' if negrita else '', 10)
        pdf.cell(ancho_resumen - 50, 8, etiqueta, 0, 0, 'R' if not negrita else 'R')
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(50, 8, valor, 0, 1, 'C')


def agregar_pagina_perfil_consumo(pdf):
    """Nueva hoja: PERFIL DE CONSUMO ENERGÉTICO"""
    pdf.add_page()
    agregar_encabezado(pdf)
    agregar_titulo_principal(pdf, 'PERFIL DE CONSUMO ENERGÉTICO')

    archivos_temp = []
    ANCHO_COL = 86

    # --- SECCIÓN 1 ---
    dibujar_titulo_seccion(pdf, '1. DISTRIBUCIÓN Y CAPACIDAD DE GENERACIÓN')
    y_seccion1 = pdf.get_y()

    fig_hist, ax_hist = plt.subplots(figsize=(5, 3.2))
    colores_barras = ['#95a5a6'] * (len(valores_hist) - 1) + ['#2c3e50'] if valores_hist else []
    ax_hist.bar(meses_hist, valores_hist, color=colores_barras if colores_barras else '#2c3e50')
    ax_hist.axhline(y=promedio_hist, color='red', linewidth=1.5)
    if valores_hist:
        ax_hist.set_ylim(0, max(max(valores_hist), promedio_hist) * 1.20)  # margen superior: evita que la barra/línea toquen el título
    ax_hist.set_ylabel('kWh')
    ax_hist.set_title('Histórico de Consumo Eléctrico', fontsize=10, fontweight='bold')
    fig_hist.tight_layout()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp1:
        plt.savefig(tmp1.name, dpi=200, bbox_inches='tight')
        ruta_hist = tmp1.name
    plt.close(fig_hist)
    archivos_temp.append(ruta_hist)

    fig_dona, ax_dona = plt.subplots(figsize=(5, 3.2))
    sizes = [pct_autosuficiencia, pct_aporte_red]
    colors_dona = ['#2ecc71', '#bdc3c7']
    ax_dona.pie(sizes, colors=colors_dona, startangle=90, counterclock=False, wedgeprops=dict(width=0.35),
                autopct='%1.0f%%', pctdistance=0.82, textprops={'fontsize': 8, 'fontweight': 'bold', 'color': '#333'})
    ax_dona.text(0, 0.08, f"{pct_autosuficiencia:.0f}%", ha='center', va='center', fontsize=22, fontweight='bold', color='#27ae60')
    ax_dona.text(0, -0.18, "AUTOSUFICIENCIA", ha='center', va='center', fontsize=8, color='#555')
    ax_dona.set_title('Cobertura Energética Proyectada', fontsize=10, fontweight='bold')
    # Nota: sin pdf.legend() externa a los ejes -> evita que el bbox_inches='tight' agrande la imagen
    # de forma impredecible. La leyenda se dibuja aparte, directamente en el PDF (ver más abajo).
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp2:
        plt.savefig(tmp2.name, dpi=200, bbox_inches='tight')
        ruta_dona = tmp2.name
    plt.close(fig_dona)
    archivos_temp.append(ruta_dona)

    alto_hist = _alto_imagen_mm(ruta_hist, ANCHO_COL)
    alto_dona = _alto_imagen_mm(ruta_dona, ANCHO_COL)
    alto_max_sec1 = max(alto_hist, alto_dona)

    pdf.image(ruta_hist, x=15, y=y_seccion1, w=ANCHO_COL)
    pdf.image(ruta_dona, x=109, y=y_seccion1, w=ANCHO_COL)

    # Leyenda de la dona dibujada directamente en el PDF (posición fija y predecible)
    y_leyenda = y_seccion1 + alto_dona + 2
    pdf.set_fill_color(46, 204, 113)
    pdf.rect(120, y_leyenda, 3, 3, 'F')
    pdf.set_font('Arial', '', 8)
    pdf.set_text_color(60, 60, 60)
    pdf.set_xy(124, y_leyenda - 1)
    pdf.cell(30, 5, 'Energía Solar', 0, 0)
    pdf.set_fill_color(189, 195, 199)
    pdf.rect(160, y_leyenda, 3, 3, 'F')
    pdf.set_xy(164, y_leyenda - 1)
    pdf.cell(30, 5, 'Red (CNEL)', 0, 0)
    pdf.set_text_color(0, 0, 0)

    y_despues_sec1 = y_seccion1 + alto_max_sec1 + 8
    pdf.set_y(y_despues_sec1)
    pdf.set_font('Arial', 'I', 8)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(90, 5, 'Análisis del consumo registrado en los últimos periodos.', 0, 0, 'C')
    pdf.set_text_color(0, 0, 0)
    pdf.set_y(y_despues_sec1 + 12)

    # --- SECCIÓN 2 ---
    dibujar_titulo_seccion(pdf, '2. IMPACTO ECONÓMICO Y REDUCCIÓN TARIFARIA')
    y_seccion2 = pdf.get_y()

    fig_tarifa, ax_tarifa = plt.subplots(figsize=(5, 3.2))
    barras = ax_tarifa.bar(['Red Eléctrica\n(CNEL)', 'Planta Solar\n(Latitud Solar)'], [costo_kwh, tarifa_nivelada], color=['#5d6d7e', '#2ecc71'])
    ax_tarifa.set_ylim(0, max(costo_kwh, tarifa_nivelada) * 1.20)
    for b in barras:
        ax_tarifa.annotate(f"${b.get_height():.3f}", xy=(b.get_x() + b.get_width() / 2, b.get_height()),
                            xytext=(0, 4), textcoords="offset points", ha='center', fontweight='bold')
    ax_tarifa.set_ylabel('Tarifa (USD/kWh)')
    fig_tarifa.tight_layout()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp3:
        plt.savefig(tmp3.name, dpi=200, bbox_inches='tight')
        ruta_tarifa = tmp3.name
    plt.close(fig_tarifa)
    archivos_temp.append(ruta_tarifa)

    ANCHO_TARIFA = 90
    alto_tarifa = _alto_imagen_mm(ruta_tarifa, ANCHO_TARIFA)
    pdf.image(ruta_tarifa, x=15, y=y_seccion2, w=ANCHO_TARIFA)

    ALTO_TARJETA = 24
    dibujar_tarjeta_metrica(
        pdf, x=112, y=y_seccion2, w=83, h=ALTO_TARJETA,
        titulo='TARIFA ACTUAL (RED CNEL)', valor=f"${costo_kwh:.3f} / kWh",
        color_fondo=(230, 233, 236), color_borde=(150, 160, 170), color_texto=(70, 80, 90)
    )
    dibujar_tarjeta_metrica(
        pdf, x=112, y=y_seccion2 + ALTO_TARJETA + 6, w=83, h=ALTO_TARJETA,
        titulo='TARIFA NIVELADA (PLANTA SOLAR)', valor=f"${tarifa_nivelada:.3f} / kWh",
        color_fondo=(230, 248, 240), color_borde=(46, 204, 113), color_texto=(39, 174, 96)
    )
    alto_max_sec2 = max(alto_tarifa, ALTO_TARJETA * 2 + 6)

    pdf.set_y(y_seccion2 + alto_max_sec2 + 8)
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
    pdf = PropuestaPDF()
    pdf.set_margins(15, 15, 15)

    ahorro_vida_util = acumulados[-1] if acumulados else 0.0
    respaldo_kw = potencia_final  # respaldo de cargas críticas = potencia instalada (sistema híbrido)

    # 1. Portada
    agregar_pagina_portada(pdf, potencia_final)

    # 2. Propuesta de ahorro
    agregar_pagina_propuesta_ahorro(
        pdf, nombre_cliente, potencia_final, numero_paneles, potencia_panel_wp,
        area_total_paneles_m2, respaldo_kw, inv_final, ahorro_vida_util, payback_exacto,
        ruta_foto_techo=ruta_foto_ahorro_subida
    )

    # 3. Distribución a cubierta (fotos propias del proyecto, si se subieron)
    agregar_pagina_distribucion_cubierta(
        pdf, ruta_foto_antes=ruta_foto_cubierta_antes_subida, ruta_foto_despues=ruta_foto_cubierta_despues_subida
    )

    # 4. Perfil de consumo energético
    agregar_pagina_perfil_consumo(pdf)

    # 5. Alcance de suministro y componentes
    agregar_pagina_alcance_suministro(pdf, potencia_final, numero_paneles, potencia_panel_wp)

    # 6. Análisis de Rentabilidad (datos del proyecto + resumen financiero + tabla técnica detallada + gráfico)
    pdf.add_page()
    agregar_encabezado(pdf)
    agregar_titulo_principal(pdf, 'ANÁLISIS DE RENTABILIDAD')

    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 8, 'DATOS DEL PROYECTO', 0, 1, 'L')
    pdf.set_font('Arial', '', 10)
    pdf.cell(95, 7, f'Cliente: {_texto_pdf_seguro(nombre_cliente)}', 0, 0)
    pdf.cell(0, 7, f'Ciudad: {ciudad_sel}', 0, 1)
    pdf.cell(95, 7, f'Proyecto: {n_proyecto}', 0, 0)
    pdf.cell(0, 7, f'N° Contrato: {_texto_pdf_seguro(numero_contrato) if numero_contrato else "N/A"}', 0, 1)
    pdf.cell(95, 7, f'Costo kWh: ${costo_kwh:.4f}', 0, 0)
    pdf.cell(0, 7, f'Potencia Instalada: {potencia_final:.2f} kWp', 0, 1)
    pdf.cell(0, 7, f'Ubicación: {_texto_pdf_seguro(ubicacion_cliente) if ubicacion_cliente else "N/A"}', 0, 1)

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

    salida_pdf = pdf.output(dest='S')
    if isinstance(salida_pdf, str):
        return salida_pdf.encode('latin-1')
    return bytes(salida_pdf)


st.divider()
_pdf_generado = generar_pdf()
col_desc1, col_desc2, col_desc3 = st.columns([1, 2, 1])
with col_desc2:
    st.download_button(
        "📥 Descargar Propuesta PDF", data=_pdf_generado, file_name=f"Propuesta_{nombre_cliente}.pdf",
        use_container_width=True, type="primary"
    )
st.sidebar.download_button("📥 Descargar Propuesta PDF", data=_pdf_generado, file_name=f"Propuesta_{nombre_cliente}.pdf")
