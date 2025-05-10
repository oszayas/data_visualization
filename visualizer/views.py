from django.shortcuts import render,HttpResponse
from django.conf import settings
import re
import pandas as pd
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64

# Create your views here.

def home(request):
         
    return render(request,'home.html')

def read_and_format_file(request):
    print("Llegamos")
    '''Función para leer y obtener datos del archivo'''
    if request.method == 'POST':        
        if 'archivo-cargado' in request.FILES:
            file = request.FILES.get('archivo-cargado')
            str_file = str(request.FILES.get('archivo-cargado'))
            file_extension = re.search(r'\.([^.]*)$',str_file).group(1)

            if file_extension == 'csv':
                temp_path = os.path.join(settings.MEDIA_ROOT, 'temp_csv')
                with open(temp_path,'wb+') as destination:
                    for chunck in file.chunks():
                        destination.write(chunck)
                
                data = pd.read_csv(temp_path, header = None,encoding='latin1')                
                
                datos = data.values.tolist()
                encabezados = datos[0]
                filas = len(datos) - 1                
                lista_datos = []
                

                for i in range(1, filas + 1):
                    lista_temp = []
                    for z in range(len(datos[i])):
                        lista_temp.append(float(datos[i][z]))
                    lista_datos.append(lista_temp)
                diccionario = {'headers':encabezados,'cant_filas':filas,'contenido_filas':lista_datos}
                return render(request,'home.html',{'diccionario':diccionario})
        else:
            return HttpResponse("Error 400: El archivo no se cargó correctamente.")

def loaded_file_visulization(request):
    """                            
    plt.figure(figsize = (10,6))
    plt.bar(encabezados,lista_datos[0])                
    plt.title("Datos CSV")
    plt.tight_layout()
    buffer = io.BytesIO()
    plt.savefig(buffer,format = 'png')
    buffer.seek(0)
    imagen = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close()        
    return render(request,'file_upload.html',{'imagen':imagen})
    """ 