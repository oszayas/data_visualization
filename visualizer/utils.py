import re
import os
import json
import base64
from io import BytesIO
import pandas as pd
import matplotlib
matplotlib.use('Agg')
from django.conf import settings

SUPPORTED_FILE_TYPES = ['csv', 'json']
DEFAULT_LIBRARY = 'matplotlib'

def get_file_extension(filename):
    """Obtiene la extensión del archivo en minúsculas."""
    return re.search(r'\.([^.]*)$', filename).group(1).lower()
def save_temp_file(file, extension):
    """Guarda un archivo temporalmente y devuelve su ruta."""
    temp_path = os.path.join(settings.MEDIA_ROOT, f'temp_{extension}')
    with open(temp_path, 'wb+') as destination:
        for chunk in file.chunks():
            destination.write(chunk)
    return temp_path
def remove_temp_file(path):
    """Elimina un archivo temporal si existe."""
    if os.path.exists(path):
        os.remove(path)
def convert_to_float(value):
    """Intenta convertir un valor a float, devuelve 0.0 si falla."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0
def create_dataframe(data, headers, num_rows):
    """Crea un DataFrame a partir de los datos y encabezados."""
    val_x = list(range(1, int(num_rows) + 1))
    data_dict = {'x': val_x}
    
    for header in headers:
        col_index = headers.index(header)
        data_dict[header] = [convert_to_float(row[col_index]) for row in data[:int(num_rows)]]
    
    return pd.DataFrame(data_dict)
def validate_columns(data, headers, selected_columns, num_rows):
    """Valida que las columnas seleccionadas tengan datos válidos."""
    valid_columns = []
    for col in selected_columns:
        col_index = headers.index(col)
        column_data = [convert_to_float(row[col_index]) for row in data[:int(num_rows)]]
        if any(d != 0.0 for d in column_data):
            valid_columns.append(col)
    return valid_columns
    
    def _figure_to_html(self, figure):
        buf = BytesIO()
        figure.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        image_base64 = base64.b64encode(buf.read()).decode('utf-8')
        html = f'<img src="data:image/png;base64,{image_base64}" style="max-width:100%;">'
        plt.close(figure)
        buf.close()
        return html
    
    def _ggplot_to_html(self, ggplot_obj):
        buf = BytesIO()
        ggplot_obj.save(buf, format='png', dpi=100, verbose=False)
        buf.seek(0)
        image_base64 = base64.b64encode(buf.read()).decode('utf-8')
        html = f'<img src="data:image/png;base64,{image_base64}" style="max-width:100%;">'
        buf.close()
        return html