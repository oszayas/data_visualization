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
import seaborn as sns
import plotly.express as px
import plotly.io as pio
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
        libreria = request.POST.get('libreria', 'matplotlib')
        lista_datos = request.session.get('lista_datos', [])
        lista_encabezados = request.session.get('lista_encabezados', [])    
        
        if not lista_datos or not lista_encabezados:
            return HttpResponse("Error: No hay datos cargados para graficar.")
        
        val_x = list(range(1, int(numero_filas_elegidas) + 1))
        
        try:
            indexes = [lista_encabezados.index(col) for col in columnas_elegidas]
        except ValueError as e:
            return HttpResponse(f"Error: {str(e)}")
        
        # Crear DataFrame para visualización
        data_dict = {'x': val_x}
        for idx, col in zip(indexes, columnas_elegidas):
            data_dict[col] = [lista_datos[i][idx] for i in range(int(numero_filas_elegidas))]
        df = pd.DataFrame(data_dict)
        
        # Manejo especial para gráficos de pastel
        if grafico_elegido == 'pastel':
            # Calcular sumas correctamente
            sumas = []
            for idx in indexes:
                suma_columna = sum(lista_datos[i][idx] for i in range(int(numero_filas_elegidas)))
                sumas.append(suma_columna)
            
            # Verificar si hay datos para graficar
            if sum(sumas) == 0:
                return HttpResponse("Error: No hay datos válidos para generar el gráfico de pastel.")
            
            # Crear figura según la librería seleccionada
            if libreria == 'seaborn':
                plt.figure(figsize=(10, 8))
                sns.set_style("whitegrid")
                
                # Crear paleta de colores con Seaborn
                palette = sns.color_palette("husl", len(columnas_elegidas))
                
                # Crear gráfico de pastel
                plt.pie(
                    sumas,
                    labels=columnas_elegidas,
                    autopct=lambda p: '{:.1f}%'.format(p) if p > 0 else '',
                    startangle=90,
                    colors=palette,
                    wedgeprops={'linewidth': 1, 'edgecolor': 'white'},
                    textprops={'fontsize': 12}
                )
                
                plt.title('Distribución por Columnas\n(Seaborn Style)', pad=20)
                plt.axis('equal')
                
                # Convertir a HTML
                buf = BytesIO()
                plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
                buf.seek(0)
                image_base64 = base64.b64encode(buf.read()).decode('utf-8')
                grafico_html = f'<img src="data:image/png;base64,{image_base64}" style="max-width:100%;">'
                plt.close()
                buf.close()
                
                return render(request, 'file_upload.html', {'grafico_html': grafico_html})
            
            elif libreria == 'plotly':
                # Versión con Plotly
                fig = px.pie(
                    values=sumas,
                    names=columnas_elegidas,
                    title='Distribución por Columnas (Plotly)',
                    color_discrete_sequence=px.colors.qualitative.Plotly
                )
                fig.update_traces(
                    textposition='inside',
                    textinfo='percent+label',
                    marker=dict(line=dict(color='white', width=1)))
                fig.update_layout(
                    uniformtext_minsize=12,
                    uniformtext_mode='hide'
                )
                
                grafico_html = fig.to_html(full_html=False, include_plotlyjs='cdn')
                return render(request, 'file_upload.html', {'grafico_html': grafico_html})
            
            else:
                # Versión con matplotlib estándar
                fig = plt.figure(figsize=(10, 8))
                patches, texts, autotexts = plt.pie(
                    sumas,
                    labels=columnas_elegidas,
                    autopct='%1.1f%%',
                    startangle=90,
                    colors=plt.cm.tab20.colors
                )
                
                plt.axis('equal')
                plt.title('Distribución por Columnas', pad=20)
                for text in texts + autotexts:
                    text.set_fontsize(10)
                
                grafico_html = mpld3.fig_to_html(fig)
                plt.close(fig)
                return render(request, 'file_upload.html', {'grafico_html': grafico_html})
        
        # Opción para usar Plotly (excepto pastel)
        if libreria == 'plotly':
            if len(columnas_elegidas) == 1:
                # Gráfico simple para una sola columna
                col = columnas_elegidas[0]
                if grafico_elegido == 'lineas':
                    fig = px.line(df, x='x', y=col, title=f'Gráfico de Líneas - {col}')
                elif grafico_elegido == 'barras':
                    fig = px.bar(df, x='x', y=col, title=f'Gráfico de Barras - {col}')
                elif grafico_elegido == 'bigotes':
                    fig = px.box(df, y=col, title=f'Gráfico de Bigotes - {col}')
                
                grafico_html = fig.to_html(full_html=False, include_plotlyjs='cdn')
                return render(request, 'file_upload.html', {'grafico_html': grafico_html})
            else:
                # Gráficos múltiples en subplots
                from plotly.subplots import make_subplots
                import plotly.graph_objects as go
                
                fig = make_subplots(rows=len(columnas_elegidas), cols=1, subplot_titles=columnas_elegidas)
                
                for i, col in enumerate(columnas_elegidas, 1):
                    if grafico_elegido == 'lineas':
                        trace = go.Scatter(x=df['x'], y=df[col], name=col)
                    elif grafico_elegido == 'barras':
                        trace = go.Bar(x=df['x'], y=df[col], name=col)
                    elif grafico_elegido == 'bigotes':
                        trace = go.Box(y=df[col], name=col)
                    
                    fig.add_trace(trace, row=i, col=1)
                
                fig.update_layout(
                    height=300 * len(columnas_elegidas),
                    showlegend=False,
                    title_text="Visualización de Datos (Plotly)"
                )
                
                grafico_html = fig.to_html(full_html=False, include_plotlyjs='cdn')
                return render(request, 'file_upload.html', {'grafico_html': grafico_html})
        
        # Opción para usar Seaborn (excepto pastel)
        elif libreria == 'seaborn':
            plots = []
            for col in columnas_elegidas:
                plt.figure(figsize=(10, 6))
                sns.set_style("whitegrid")
                
                if grafico_elegido == 'lineas':
                    sns.lineplot(data=df, x='x', y=col, linewidth=2.5, color='royalblue')
                    plt.title(f"Gráfico de Líneas - {col} (Seaborn)", pad=15)
                elif grafico_elegido == 'barras':
                    sns.barplot(data=df, x='x', y=col, color='steelblue')
                    plt.title(f"Gráfico de Barras - {col} (Seaborn)", pad=15)
                elif grafico_elegido == 'bigotes':
                    sns.boxplot(data=df, y=col, color='lightgreen')
                    plt.title(f"Gráfico de Bigotes - {col} (Seaborn)", pad=15)
                
                plt.xlabel("Valores", labelpad=10)
                plt.ylabel(col, labelpad=10)
                plt.tight_layout()
                
                # Convertir a imagen base64
                buf = BytesIO()
                plt.savefig(buf, format='png', dpi=100)
                buf.seek(0)
                image_base64 = base64.b64encode(buf.read()).decode('utf-8')
                plots.append(f'<img src="data:image/png;base64,{image_base64}" style="max-width:100%;">')
                plt.close()
                buf.close()
            
            if len(plots) == 1:
                return render(request, 'file_upload.html', {'grafico_html': plots[0]})
            else:
                grafico_html = '<div style="display: flex; flex-direction: column; gap: 20px;">' + \
                              ''.join([f'<div>{plot}</div>' for plot in plots]) + \
                              '</div>'
                return render(request, 'file_upload.html', {'grafico_html': grafico_html})
        
        # Opción para usar ggplot
        elif libreria == 'ggplot':
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
        
        # Opción por defecto: matplotlib
        else:
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