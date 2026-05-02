import tempfile
import os

def crear_pdf():
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    
    # --- Encabezado ---
    pdf.set_fill_color(31, 119, 180)
    pdf.rect(0, 0, 210, 35, 'F')
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Arial', 'B', 18)
    pdf.cell(0, 15, f'PROPUESTA SOLAR - {tipo_proyecto.upper()}', 0, 1, 'C')
    
    # --- Datos del Proyecto ---
    pdf.set_text_color(0, 0, 0)
    pdf.ln(25)
    pdf.set_font('Arial', 'B', 12); pdf.cell(0, 10, 'DATOS DEL PROYECTO', 0, 1, 'L')
    pdf.set_font('Arial', '', 10)
    pdf.cell(95, 7, f'Cliente: {nombre_cliente}')
    pdf.cell(95, 7, f'Ciudad: {ciudad_sel}', 0, 1)
    pdf.cell(95, 7, f'Inversión: ${costo_planta_total:,.2f}')
    pdf.cell(95, 7, f'Payback: {payback_text}', 0, 1)

    # --- GENERACIÓN DEL GRÁFICO DE FLUJO DE CAJA ---
    # Extraemos los datos de la tabla para graficar
    años = [d['Año'] for d in data_tabla]
    # Limpiamos los strings de la tabla para convertirlos a números
    ahorros = [float(d['Ahorro Total Año'].replace('$', '').replace(',', '')) for d in data_tabla]
    acumulado = [float(d['Acumulado'].replace('$', '').replace(',', '')) for d in data_tabla]

    fig, ax1 = plt.subplots(figsize=(10, 5))

    # Barras para ahorro anual
    ax1.bar(años, ahorros, color='#AED6F1', label='Ahorro Anual (USD)')
    ax1.set_xlabel('Año')
    ax1.set_ylabel('Ahorro Anual (USD)')
    
    # Línea para flujo acumulado
    ax2 = ax1.twinx()
    ax2.plot(años, acumulado, color='#1F618D', marker='o', linewidth=2, label='Flujo Acumulado')
    ax2.axhline(y=costo_planta_total, color='r', linestyle='--', label='Inversión Inicial')
    ax2.set_ylabel('Acumulado (USD)')
    
    plt.title('Proyección de Flujo de Caja y Recuperación')
    fig.legend(loc='upper left', bbox_to_anchor=(0.1, 0.9))
    plt.tight_layout()

    # Guardar gráfico en archivo temporal
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmpfile:
        plt.savefig(tmpfile.name, format='png', dpi=150)
        plot_path = tmpfile.name

    # Insertar gráfico en el PDF
    pdf.image(plot_path, x=15, y=pdf.get_y() + 10, w=180)
    pdf.ln(95) # Espacio para que la tabla no se solape con la imagen

    # --- Tabla de Datos ---
    pdf.set_font('Arial', 'B', 10); pdf.set_fill_color(31, 119, 180); pdf.set_text_color(255, 255, 255)
    pdf.cell(15, 8, 'Año', 1, 0, 'C', True)
    pdf.cell(40, 8, 'Prod. kWh', 1, 0, 'C', True)
    pdf.cell(45, 8, 'Ahorro Año', 1, 0, 'C', True)
    pdf.cell(45, 8, 'Acumulado', 1, 1, 'C', True)
    
    pdf.set_text_color(0, 0, 0); pdf.set_font('Arial', '', 9)
    # Mostramos solo los primeros 15 años en la primera hoja o ajustamos según espacio
    for d in data_tabla:
        pdf.cell(15, 7, str(d['Año']), 1, 0, 'C')
        pdf.cell(40, 7, d['Prod. (kWh/año)'], 1, 0, 'C')
        pdf.cell(45, 7, d['Ahorro Total Año'], 1, 0, 'C')
        pdf.cell(45, 7, d['Acumulado'], 1, 1, 'C')

    # Limpieza del archivo temporal
    res = pdf.output(dest='S').encode('latin-1')
    os.remove(plot_path)
    return res
