from django.shortcuts import render, HttpResponse
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
from plotnine import ggplot, aes, geom_line, geom_col, geom_boxplot, labs, theme, element_text, coord_flip
from io import BytesIO

# Create your views here.
def home(request):
    return render(request, 'home.html')

def read_and_format_file(request):    
    '''Función para leer y obtener datos del archivo'''
    if request.method == 'POST':        
        if 'archivo-cargado' in request.FILES:
            file = request.FILES.get('archivo-cargado')
            str_file = str(request.FILES.get('archivo-cargado'))
            file_extension = re.search(r'\.([^.]*)$', str_file).group(1)

            if file_extension == 'csv':
                temp_path = os.path.join(settings.MEDIA_ROOT, 'temp_csv')
                with open(temp_path, 'wb+') as destination:
                    for chunck in file.chunks():
                        destination.write(chunck)
                
                data = pd.read_csv(temp_path, header=None, encoding='latin1')                
                
                datos = data.values.tolist()
                encabezados = datos[0]
                filas = len(datos) - 1                
                lista_datos = []
                
                for i in range(1, filas + 1):
                    lista_temp = []
                    for z in range(len(datos[i])):
                        try:
                            lista_temp.append(float(datos[i][z]))
                        except ValueError:
                            lista_temp.append(0.0)  # Manejo de valores no numéricos
                    lista_datos.append(lista_temp)
                
                request.session['lista_datos'] = lista_datos
                request.session['lista_encabezados'] = encabezados    
                diccionario = {'headers': encabezados, 'cant_filas': filas}
                return render(request, 'home.html', {'diccionario': diccionario})
        else:
            return HttpResponse("Error 400: El archivo no se cargó correctamente.")

def loaded_file_visulization(request):
    if request.method == 'POST':
        grafico_elegido = request.POST.get('grafico')
        columnas_elegidas = request.POST.getlist('columnas')
        numero_filas_elegidas = request.POST.get('cant_filas_usar')
        lista_datos = request.session.get('lista_datos', [])
        lista_encabezados = request.session.get('lista_encabezados', [])    
        
        if not lista_datos or not lista_encabezados:
            return HttpResponse("Error: No hay datos cargados para graficar.")
        
        val_x = list(range(1, int(numero_filas_elegidas) + 1))
        
        try:
            indexes = [lista_encabezados.index(col) for col in columnas_elegidas]
        except ValueError as e:
            return HttpResponse(f"Error: {str(e)}")
        
        # Crear DataFrame para ggplot
        data_dict = {'x': val_x}
        for idx, col in zip(indexes, columnas_elegidas):
            data_dict[col] = [lista_datos[i][idx] for i in range(int(numero_filas_elegidas))]
        df = pd.DataFrame(data_dict)
        
        # Manejo especial para gráficos de pastel (ggplot no los maneja bien)
        if grafico_elegido == 'pastel':
            fig = plt.figure(figsize=(10, 8))
            sumas = [sum([lista_datos[i][idx]] for i in range(int(numero_filas_elegidas))) for idx in indexes]
            
            patches, texts, autotexts = plt.pie(
                sumas,
                labels=columnas_elegidas,
                autopct='%1.1f%%',
                startangle=90,
                colors=plt.cm.tab20.colors
            )
            
            plt.axis('equal')
            for text in texts + autotexts:
                text.set_fontsize(10)
            
            grafico_html = mpld3.fig_to_html(fig)
            plt.close(fig)
            return render(request, 'file_upload.html', {'grafico_html': grafico_html})
        
        # Opción para usar ggplot
        usar_ggplot = request.POST.get('usar_ggplot', False)
        
        if usar_ggplot:
            # Versión con ggplot/plotnine
            plots = []
            for col in columnas_elegidas:
                if grafico_elegido == 'lineas':
                    p = (ggplot(df, aes(x='x', y=col)) 
                         + geom_line(color='blue') 
                         + labs(title=f"Datos {col}", x="Tiempo", y=col) 
                         + theme(axis_text_x=element_text(rotation=45, hjust=1)))
                
                elif grafico_elegido == 'barras':
                    p = (ggplot(df, aes(x='x', y=col)) 
                         + geom_col(fill='steelblue') 
                         + labs(title=f"Datos {col}", x="Valores", y=col) 
                         + theme(axis_text_x=element_text(rotation=45, hjust=1)))
                
                elif grafico_elegido == 'bigotes':
                    df_melted = df.melt(id_vars=['x'], value_vars=[col], 
                                       var_name='variable', value_name='value')
                    p = (ggplot(df_melted, aes(x='variable', y='value')) 
                         + geom_boxplot(fill='lightgreen') 
                         + labs(title=f"Datos {col}", x="", y=col) 
                         + coord_flip())
                
                # Convertir a imagen base64
                buf = BytesIO()
                p.save(buf, format='png', dpi=100, verbose=False)
                buf.seek(0)
                image_base64 = base64.b64encode(buf.read()).decode('utf-8')
                plots.append(f'<img src="data:image/png;base64,{image_base64}" style="max-width:100%;">')
                buf.close()
            
            if len(plots) == 1:
                return render(request, 'file_upload.html', {'grafico_html': plots[0]})
            else:
                grafico_html = '<div style="display: flex; flex-direction: column; gap: 20px;">' + \
                              ''.join([f'<div>{plot}</div>' for plot in plots]) + \
                              '</div>'
                return render(request, 'file_upload.html', {'grafico_html': grafico_html})
        
        else:
            # Versión original con matplotlib
            fig, axs = plt.subplots(len(columnas_elegidas), 1, 
                                   figsize=(8, 4 * len(columnas_elegidas)),
                                   squeeze=False)
            axs = axs.flatten()
            
            for i, (ax, idx, col) in enumerate(zip(axs, indexes, columnas_elegidas)):
                datos = [lista_datos[row][idx] for row in range(int(numero_filas_elegidas))]
                
                if grafico_elegido == 'lineas':
                    ax.plot(val_x, datos)
                elif grafico_elegido == 'barras':
                    ax.bar(val_x, datos)
                elif grafico_elegido == 'bigotes':
                    ax.boxplot(datos)
                    ax.set_xticks([])
                
                ax.set_title(f"Datos {col}")
                ax.set_xlabel("Valores")
                ax.set_ylabel(col)
            
            plt.tight_layout()
            grafico_html = mpld3.fig_to_html(fig)
            plt.close(fig)
            return render(request, 'file_upload.html', {'grafico_html': grafico_html})