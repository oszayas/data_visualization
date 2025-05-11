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
import mpld3

# Create your views here.
def home(request):
         
    return render(request,'home.html')

def read_and_format_file(request):    
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
                request.session['lista_datos'] = lista_datos
                request.session['lista_encabezados'] = encabezados    
                diccionario = {'headers':encabezados,'cant_filas':filas}
                return render(request,'home.html',{'diccionario':diccionario})
        else:
            return HttpResponse("Error 400: El archivo no se cargó correctamente.")


def loaded_file_visulization(request):
    if request.method == 'POST':
        grafico_elegido = request.POST.get('grafico')
        columnas_elegidas = request.POST.getlist('columnas')
        numero_filas_elegidas = request.POST.get('cant_filas_usar')
        lista_datos = request.session.get('lista_datos',[])
        lista_encabezados = request.session.get('lista_encabezados',[])    
                
        if grafico_elegido == 'lineas':
            index = lista_encabezados.index(columnas_elegidas[0])
            datos_graficar = []
            for i in lista_datos:
                datos_graficar.append(i[index])
            plt.figure(figsize = (8,4))
            plt.plot([1,2,3,4,5],datos_graficar)                
            plt.title(f"Datos {columnas_elegidas[0]}")
            plt.xlabel("Tiempo")
            plt.ylabel(f"{columnas_elegidas[0]}")
            plt.tight_layout()            
            grafico_html = mpld3.fig_to_html(plt.gcf())
            plt.close()        
            return render(request,'file_upload.html',{'grafico_html':grafico_html})
        
        
        

        
    
        