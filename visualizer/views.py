from django.shortcuts import render, HttpResponse,redirect
from django.conf import settings
from django.urls import reverse
from .utils import (
    get_file_extension, save_temp_file, remove_temp_file, 
    create_dataframe, convert_to_float, validate_columns, SUPPORTED_FILE_TYPES
)
from .visualization import PieChartVisualizer ,ScatterPlotVisualizer,BasicChartVisualizer,HeatMapVisualizer # Import other visualizers as needed
import pandas as pd
import json
from io import BytesIO
import base64
import matplotlib.pyplot as plt
from visualizer.models import ApiRegistros
from django.views.decorators.http import require_GET
from django.http import JsonResponse
from collections import Counter
import numpy as np

def home(request):
    return render(request, 'home.html')

def read_and_format_file(request):
    if request.method != 'POST' or 'archivo-cargado' not in request.FILES:
        return HttpResponse("Error 400: El archivo no se cargó correctamente.")
    
    file = request.FILES['archivo-cargado']
    file_extension = get_file_extension(str(file))
    
    if file_extension not in SUPPORTED_FILE_TYPES:
        return HttpResponse("Error 400: Formato de archivo no soportado. Use CSV o JSON.")
    
    temp_path = save_temp_file(file, file_extension)
    
    try:
        if file_extension == 'csv':
            data, headers = process_csv_file(temp_path)
        else:
            data, headers = process_json_file(temp_path)
        
        # Guardar datos en la sesión
        request.session['lista_datos'] = data
        request.session['lista_encabezados'] = headers
        
        context = {
            'diccionario': {
                'headers': headers,
                'cant_filas': len(data),
                'visualization_url': reverse('loaded_file_visulization')
            }
        }
        return render(request, 'home.html', context)
    
    except Exception as e:
        return HttpResponse(f"Error al procesar el archivo: {str(e)}")
    finally:
        remove_temp_file(temp_path)

def process_csv_file(file_path):
    """Procesa un archivo CSV y devuelve datos y encabezados."""
    data = pd.read_csv(file_path, header=None, encoding='latin1').values.tolist()
    
    if not data:
        raise ValueError("El archivo CSV está vacío.")
    
    headers = data[0]
    rows = [row for row in data[1:] if row]  # Filtrar filas vacías
    
    processed_data = []
    for row in rows:
        processed_row = [convert_to_float(value) for value in row]
        processed_data.append(processed_row)
    
    return processed_data, headers

def process_json_file(file_path):
    """Procesa un archivo JSON y devuelve datos y encabezados."""
    with open(file_path, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
    
    if isinstance(json_data, list):
        df = pd.DataFrame(json_data)
    elif isinstance(json_data, dict):
        df = pd.DataFrame.from_dict(json_data, orient='index').T
    else:
        raise ValueError("Formato JSON no soportado.")
    
    data = df.values.tolist()
    headers = df.columns.tolist()
    
    if not headers:
        headers = [f"Columna_{i}" for i in range(len(data[0]))]
    
    processed_data = []
    for row in data:
        processed_row = [convert_to_float(value) for value in row]
        processed_data.append(processed_row)
    
    return processed_data, headers

def loaded_file_visualization(request):
    if request.method != 'POST':
        return HttpResponse("Método no permitido")
    
    required_params = ['grafico', 'columnas', 'cant_filas_usar']
    if not all(param in request.POST for param in required_params):
        return HttpResponse("Parámetros faltantes en la solicitud")
    
    graph_type = request.POST['grafico']
    columns = request.POST.getlist('columnas')
    num_rows = request.POST['cant_filas_usar']
    library = request.POST.get('libreria', 'matplotlib')
    
    data = request.session.get('lista_datos', [])
    headers = request.session.get('lista_encabezados', [])
    
    if not data or not headers:
        return HttpResponse("Error: No hay datos cargados para graficar.")
    
    # Validación de columnas para gráficos especiales
    if graph_type in ['dispersion', 'calor'] and len(columns) < 2:
        return HttpResponse(f"Error: Para gráficos de {graph_type} se necesitan al menos 2 columnas seleccionadas.")
    
    # Seleccionar el visualizador adecuado según el tipo de gráfico
    if graph_type == 'pastel':
        visualizer = PieChartVisualizer(request, graph_type, columns, num_rows, data, headers)
    elif graph_type == 'dispersion':
        visualizer = ScatterPlotVisualizer(request, graph_type, columns, num_rows, data, headers)
    elif graph_type == 'calor':
        visualizer = HeatMapVisualizer(request, graph_type, columns, num_rows, data, headers)
    elif graph_type in ['lineas', 'barras', 'bigotes']:
        visualizer = BasicChartVisualizer(request, graph_type, columns, num_rows, data, headers)
    else:
        return HttpResponse("Tipo de gráfico no soportado")
    
    graph_html = visualizer.render()
    return render(request, 'file_upload.html', {'grafico_html': graph_html})

def extraer_base_datos(request):
    context = {}
    
    if request.method == 'POST':
        chart_type = request.POST.get('chart_type', 'lineas')
        data_type = request.POST.get('data_type', 'fechas')
        
        # Obtener y procesar registros
        records = ApiRegistros.objects.all()
        results = [json.loads(record.metadata) for record in records]
        
        # Procesar autores y fechas
        autores = []
        fechas = []
        
        for result in results:
            if not result:
                continue
                
            # Procesar autores
            autores_data = result.get("_map", {}).get('creator', [])
            if autores_data:
                if isinstance(autores_data[0], list):
                    autores.extend([autor.strip() for sublist in autores_data for autor in sublist if autor.strip()])
                else:
                    autores.extend([autor.strip() for autor in autores_data if autor.strip()])
            
            # Procesar fechas
            fecha_data = result.get("_map", {}).get('date', [])
            if fecha_data:
                fechas.append(fecha_data)
        
        # Procesamiento de fechas
        diccionario_fechas = {}
        for fecha in fechas:
            if fecha and len(fecha) > 0:
                year = fecha[0].split('-')[0]
                diccionario_fechas[year] = diccionario_fechas.get(year, 0) + 1
        
        # Procesamiento de autores
        contador_autores = Counter(autores)
        autores_ordenados = sorted(contador_autores.items(), key=lambda x: x[1], reverse=True)
        
        # Preparar datos según el tipo seleccionado
        if data_type == 'fechas':
            sorted_data = sorted(diccionario_fechas.items())
            labels = [item[0] for item in sorted_data]
            values = [item[1] for item in sorted_data]
            title_prefix = "Publicaciones por Año"
            x_label = "Año"
            table_header = ("Año", "Publicaciones")
        else:
            top_autores = autores_ordenados[:15]  # Mostrar top 15 autores
            labels = [item[0] for item in top_autores]
            values = [item[1] for item in top_autores]
            title_prefix = "Autores más Productivos"
            x_label = "Autor"
            table_header = ("Autor", "Publicaciones")
            sorted_data = top_autores
        
        # Generar el gráfico
        plt.figure(figsize=(12, 7))
        
        if chart_type == 'lineas':
            plt.plot(labels, values, marker='o', linestyle='-', color='b')
        elif chart_type == 'barras':
            plt.bar(labels, values, color='b')
        elif chart_type == 'pastel':
            plt.pie(values, labels=labels, autopct='%1.1f%%')
        elif chart_type == 'bigotes':
            # Preparar datos para el boxplot
            if data_type == 'fechas':
                # Boxplot de distribución de años
                try:
                    years = [int(year) for year in diccionario_fechas.keys()]
                    plt.boxplot([years], 
                            vert=True, 
                            patch_artist=True,
                            boxprops=dict(facecolor='lightblue'),
                            medianprops=dict(color='red'))
                    plt.title('Distribución de Años de Publicación')
                    plt.ylabel('Año')
                    plt.xticks([1], ['Años'])
                except ValueError as e:
                    plt.text(0.5, 0.5, 'Error: Datos de año no válidos', 
                            ha='center', va='center')
                    plt.title('Diagrama de Bigotes - Error')
            else:
                # Boxplot de distribución de publicaciones por autor
                all_counts = [count for _, count in autores_ordenados]
                plt.boxplot([all_counts],
                        vert=True,
                        patch_artist=True,
                        boxprops=dict(facecolor='lightgreen'),
                        medianprops=dict(color='red'))
                plt.title('Distribución de Publicaciones por Autor')
                plt.ylabel('Publicaciones')
                plt.xticks([1], ['Publicaciones'])
            plt.grid(True, axis='y')
        elif chart_type == 'calor':
            plt.figure(figsize=(12, 8))
            
            if data_type == 'fechas':
                # Heatmap de publicaciones por año/mes
                try:
                    # Procesar fechas para obtener año y mes
                    year_month_counts = {}
                    for fecha in fechas:
                        if fecha and len(fecha) > 0:
                            parts = fecha[0].split('-')
                            if len(parts) >= 2:
                                year_month = f"{parts[0]}-{parts[1]}"
                                year_month_counts[year_month] = year_month_counts.get(year_month, 0) + 1
                    
                    if not year_month_counts:
                        raise ValueError("No hay datos de fecha válidos")
                    
                    # Crear matriz para el heatmap
                    years = sorted({ym.split('-')[0] for ym in year_month_counts.keys()})
                    months = [f"{m:02d}" for m in range(1, 13)]  # Meses 01-12
                    heatmap_data = np.zeros((len(years), len(months)))
                    
                    for ym, count in year_month_counts.items():
                        year, month = ym.split('-')
                        y_idx = years.index(year)
                        m_idx = months.index(month)
                        heatmap_data[y_idx, m_idx] = count
                    
                    # Crear heatmap
                    plt.imshow(heatmap_data, cmap='YlOrRd', aspect='auto')
                    plt.colorbar(label='Número de Publicaciones')
                    
                    # Configurar ejes
                    plt.xticks(np.arange(len(months)), months)
                    plt.yticks(np.arange(len(years)), years)
                    plt.xlabel('Cantidad')
                    plt.ylabel('Año')
                    plt.title('Mapa de Calor: Publicaciones por Año y Mes')
                    
                except Exception as e:
                    plt.text(0.5, 0.5, f'Error en datos: {str(e)}', 
                            ha='center', va='center')
                    plt.title('Mapa de Calor - Error')
            
            else:
                # Heatmap de co-autoría (ejemplo simplificado)
                try:
                    # Esto es un ejemplo - necesitarías lógica más compleja para co-autoría real
                    top_autores = [autor for autor, _ in autores_ordenados[:10]]
                    coautor_matrix = np.random.randint(0, 10, size=(10, 10))  # Datos de ejemplo
                    
                    # Hacer la diagonal 0 para mejor visualización
                    np.fill_diagonal(coautor_matrix, 0)
                    
                    plt.imshow(coautor_matrix, cmap='Blues', aspect='auto')
                    plt.colorbar(label='Colaboraciones')
                    
                    # Configurar ejes
                    plt.xticks(np.arange(len(top_autores)), top_autores, rotation=45, ha='right')
                    plt.yticks(np.arange(len(top_autores)), top_autores)
                    plt.title('Mapa de Calor: Colaboraciones entre Autores (Ejemplo)')
                    
                except Exception as e:
                    plt.text(0.5, 0.5, 'Datos insuficientes para mapa de colaboraciones', 
                            ha='center', va='center')
                    plt.title('Mapa de Calor - Información no disponible')
            
            plt.tight_layout()
    
    
        
        plt.title(f'{title_prefix} ({chart_type.capitalize()})')
        plt.xlabel(x_label)
        plt.ylabel('Cantidad')
        plt.grid(True)
        plt.xticks(rotation=45 if data_type == 'autores' else 0)
        plt.tight_layout()
        
        # Convertir gráfico a base64
        buffer = BytesIO()
        plt.savefig(buffer, format='png', bbox_inches='tight')
        buffer.seek(0)
        graphic = base64.b64encode(buffer.getvalue()).decode('utf-8')
        plt.close()
        
        # Preparar datos para la tabla
        table_rows = [(str(item[0]), str(item[1])) for item in sorted_data]
        total = sum(values)
        
        context = {
            'graphic': graphic,
            'table_header': table_header,
            'table_rows': table_rows,
            'total': total,
            'total_registros': len(results),
            'autores_publicaciones': autores_ordenados,
            'selected_data_type': data_type,
            'selected_chart_type': chart_type,
            'show_autores_list': data_type == 'fechas'
        }
    
    return render(request, 'algo.html', context)