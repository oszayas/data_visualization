from io import BytesIO
import base64
import seaborn as sns
import plotly.express as px
import mpld3
from .utils import create_dataframe, validate_columns
import matplotlib.pyplot as plt
import mpld3
import seaborn as sns
import plotly.express as px
from plotnine import ggplot, aes, geom_line, geom_col, geom_boxplot, labs, theme, element_text, coord_flip, geom_point

class BaseVisualizer:
    def __init__(self, request, graph_type, columns, num_rows, data, headers):
        self.request = request
        self.graph_type = graph_type
        self.columns = columns
        self.num_rows = num_rows
        self.data = data
        self.headers = headers
        self.df = create_dataframe(data, headers, num_rows)
        self.valid_columns = validate_columns(data, headers, columns, num_rows)

    def render(self):
        raise NotImplementedError("Subclasses must implement this method")

class PieChartVisualizer(BaseVisualizer):
    def render(self):
        if not self.valid_columns:
            return "Error: No hay datos válidos para generar el gráfico."
        
        sumas = [sum(self.df[col]) for col in self.valid_columns]
        
        if sum(sumas) == 0:
            return "Error: No hay datos válidos para generar el gráfico de pastel."
        
        library = self.request.POST.get('libreria', 'matplotlib')
        
        if library == 'seaborn':
            return self._render_seaborn_pie(sumas)
        elif library == 'plotly':
            return self._render_plotly_pie(sumas)
        else:
            return self._render_matplotlib_pie(sumas)
    
    def _render_seaborn_pie(self, sumas):
        plt.figure(figsize=(10, 8))
        sns.set_style("whitegrid")
        palette = sns.color_palette("husl", len(self.valid_columns))
        
        plt.pie(
            sumas,
            labels=self.valid_columns,
            autopct=lambda p: '{:.1f}%'.format(p) if p > 0 else '',
            startangle=90,
            colors=palette,
            wedgeprops={'linewidth': 1, 'edgecolor': 'white'},
            textprops={'fontsize': 12}
        )
        
        plt.title('Distribución por Columnas\n(Seaborn Style)', pad=20)
        plt.axis('equal')
        
        return self._figure_to_html(plt)

    def _render_plotly_pie(self, sumas):
        fig = px.pie(
            values=sumas,
            names=self.valid_columns,
            title='Distribución por Columnas (Plotly)',
            color_discrete_sequence=px.colors.qualitative.Plotly
        )
        fig.update_traces(
            textposition='inside',
            textinfo='percent+label',
            marker=dict(line=dict(color='white', width=1)))
        fig.update_layout(uniformtext_minsize=12, uniformtext_mode='hide')
        return fig.to_html(full_html=False, include_plotlyjs='cdn')

    def _render_matplotlib_pie(self, sumas):
        fig = plt.figure(figsize=(10, 8))
        patches, texts, autotexts = plt.pie(
            sumas,
            labels=self.valid_columns,
            autopct='%1.1f%%',
            startangle=90,
            colors=plt.cm.tab20.colors
        )
        plt.axis('equal')
        plt.title('Distribución por Columnas', pad=20)
        for text in texts + autotexts:
            text.set_fontsize(10)
        return mpld3.fig_to_html(fig)

    def _figure_to_html(self, figure):
        buf = BytesIO()
        figure.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        image_base64 = base64.b64encode(buf.read()).decode('utf-8')
        html = f'<img src="data:image/png;base64,{image_base64}" style="max-width:100%;">'
        plt.close()
        buf.close()
        return html

class ScatterPlotVisualizer(BaseVisualizer):
    def _figure_to_html(self, figure):
        buf = BytesIO()
        figure.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        image_base64 = base64.b64encode(buf.read()).decode('utf-8')
        html = f'<img src="data:image/png;base64,{image_base64}" style="max-width:100%;">'
        plt.close()
        buf.close()
        return html
    
    def render(self):
        if len(self.valid_columns) < 2:
            return "Error: Se necesitan al menos 2 columnas para un gráfico de dispersión."
        
        library = self.request.POST.get('libreria', 'matplotlib')
        
        if library == 'plotly':
            fig = px.scatter(
                self.df, 
                x=self.valid_columns[0], 
                y=self.valid_columns[1],
                title=f'Gráfico de Dispersión: {self.valid_columns[0]} vs {self.valid_columns[1]}'
            )
            return fig.to_html(full_html=False, include_plotlyjs='cdn')
        
        elif library == 'seaborn':
            plt.figure(figsize=(10, 8))
            sns.set_style("whitegrid")
            sns.scatterplot(
                data=self.df,
                x=self.valid_columns[0],
                y=self.valid_columns[1],
                s=100,
                color='royalblue'
            )
            plt.title(f'Gráfico de Dispersión: {self.valid_columns[0]} vs {self.valid_columns[1]} (Seaborn)')
            return self._figure_to_html(plt)
        
        elif library == 'ggplot':
            p = (ggplot(self.df, aes(x=self.valid_columns[0], y=self.valid_columns[1]))
                 + geom_point(color='blue', size=3)
                 + labs(
                     title=f'Dispersión: {self.valid_columns[0]} vs {self.valid_columns[1]}',
                     x=self.valid_columns[0],
                     y=self.valid_columns[1]
                 ))
            return self._ggplot_to_html(p)
        
        else:  # matplotlib por defecto
            fig, ax = plt.subplots(figsize=(10, 8))
            ax.scatter(
                self.df[self.valid_columns[0]],
                self.df[self.valid_columns[1]],
                c='blue',
                alpha=0.7
            )
            ax.set_title(f'Gráfico de Dispersión: {self.valid_columns[0]} vs {self.valid_columns[1]}')
            return self._figure_to_html(fig)

class HeatMapVisualizer(BaseVisualizer):
    def _figure_to_html(self, figure):
        buf = BytesIO()
        figure.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        image_base64 = base64.b64encode(buf.read()).decode('utf-8')
        html = f'<img src="data:image/png;base64,{image_base64}" style="max-width:100%;">'
        plt.close()
        buf.close()
        return html
    
    def render(self):
        if len(self.valid_columns) < 2:
            return "Error: Se necesitan al menos 2 columnas para un mapa de calor."
        
        library = self.request.POST.get('libreria', 'matplotlib')
        
        # Crear matriz de correlación o datos para el mapa de calor
        try:
            heatmap_data = self.df[self.valid_columns].corr()
        except:
            heatmap_data = self.df[self.valid_columns]
        
        if library == 'plotly':
            fig = px.imshow(
                heatmap_data,
                labels=dict(x="Variables", y="Variables", color="Correlación"),
                x=self.valid_columns,
                y=self.valid_columns,
                title='Mapa de Calor'
            )
            return fig.to_html(full_html=False, include_plotlyjs='cdn')
        
        elif library == 'seaborn':
            plt.figure(figsize=(10, 8))
            sns.set_style("whitegrid")
            sns.heatmap(
                heatmap_data,
                annot=True,
                cmap='coolwarm',
                center=0,
                fmt=".2f",
                linewidths=.5
            )
            plt.title('Mapa de Calor (Seaborn)')
            return self._figure_to_html(plt)
        
        else:  # matplotlib por defecto
            fig, ax = plt.subplots(figsize=(10, 8))
            cax = ax.matshow(heatmap_data, cmap='coolwarm')
            fig.colorbar(cax)
            
            # Configurar ticks
            ax.set_xticks(range(len(self.valid_columns)))
            ax.set_yticks(range(len(self.valid_columns)))
            ax.set_xticklabels(self.valid_columns, rotation=45)
            ax.set_yticklabels(self.valid_columns)
            
            # Añadir valores
            for i in range(len(self.valid_columns)):
                for j in range(len(self.valid_columns)):
                    text = ax.text(j, i, f"{heatmap_data.iloc[i, j]:.2f}",
                                 ha="center", va="center", color="black")
            
            plt.title('Mapa de Calor')
            return self._figure_to_html(fig)

class BasicChartVisualizer(BaseVisualizer):

    def render(self):
        library = self.request.POST.get('libreria', 'matplotlib')
        
        if library == 'plotly':
            return self._render_plotly()
        elif library == 'seaborn':
            return self._render_seaborn()
        elif library == 'ggplot':
            return self._render_ggplot()
        else:
            return self._render_matplotlib()
    
    def _render_plotly(self):
        if len(self.valid_columns) == 1:
            col = self.valid_columns[0]
            if self.graph_type == 'lineas':
                fig = px.line(self.df, x='x', y=col, title=f'Gráfico de Líneas - {col}')
            elif self.graph_type == 'barras':
                fig = px.bar(self.df, x='x', y=col, title=f'Gráfico de Barras - {col}')
            elif self.graph_type == 'bigotes':
                fig = px.box(self.df, y=col, title=f'Gráfico de Bigotes - {col}')
            return fig.to_html(full_html=False, include_plotlyjs='cdn')
        else:
            from plotly.subplots import make_subplots
            import plotly.graph_objects as go
            fig = make_subplots(rows=len(self.valid_columns), cols=1, 
                              subplot_titles=self.valid_columns)
            for i, col in enumerate(self.valid_columns, 1):
                if self.graph_type == 'lineas':
                    trace = go.Scatter(x=self.df['x'], y=self.df[col], name=col)
                elif self.graph_type == 'barras':
                    trace = go.Bar(x=self.df['x'], y=self.df[col], name=col)
                elif self.graph_type == 'bigotes':
                    trace = go.Box(y=self.df[col], name=col)
                fig.add_trace(trace, row=i, col=1)
            fig.update_layout(
                height=300 * len(self.valid_columns),
                showlegend=False,
                title_text="Visualización de Datos (Plotly)"
            )
            return fig.to_html(full_html=False, include_plotlyjs='cdn')
    def _render_seaborn(self):
        import seaborn as sns
        import matplotlib.pyplot as plt
        from io import BytesIO
        import base64
        
        plt.figure(figsize=(10, 6))
        
        if len(self.valid_columns) == 1:
            col = self.valid_columns[0]
            if self.graph_type == 'lineas':
                sns.lineplot(x='x', y=col, data=self.df)
                plt.title(f'Gráfico de Líneas - {col}')
            elif self.graph_type == 'barras':
                sns.barplot(x='x', y=col, data=self.df)
                plt.title(f'Gráfico de Barras - {col}')
            elif self.graph_type == 'bigotes':
                sns.boxplot(y=col, data=self.df)
                plt.title(f'Gráfico de Bigotes - {col}')
        else:
            fig, axes = plt.subplots(len(self.valid_columns), 1, figsize=(10, 5*len(self.valid_columns)))
            if len(self.valid_columns) == 1:
                axes = [axes]
            
            for i, col in enumerate(self.valid_columns):
                if self.graph_type == 'lineas':
                    sns.lineplot(x='x', y=col, data=self.df, ax=axes[i])
                elif self.graph_type == 'barras':
                    sns.barplot(x='x', y=col, data=self.df, ax=axes[i])
                elif self.graph_type == 'bigotes':
                    sns.boxplot(y=col, data=self.df, ax=axes[i])
                axes[i].set_title(col)
            
            plt.tight_layout()
        
        buffer = BytesIO()
        plt.savefig(buffer, format='png')
        plt.close()
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return f'<img src="data:image/png;base64,{image_base64}" class="img-fluid">'

    def _render_ggplot(self):
        from ggplot import ggplot, aes, geom_line, geom_bar, geom_boxplot,ggtitle
        from io import BytesIO
        import base64
        import matplotlib.pyplot as plt
        
        if len(self.valid_columns) == 1:
            col = self.valid_columns[0]
            if self.graph_type == 'lineas':
                plot = ggplot(self.df, aes(x='x', y=col)) + geom_line() + \
                       ggtitle(f'Gráfico de Líneas - {col}')
            elif self.graph_type == 'barras':
                plot = ggplot(self.df, aes(x='x', y=col)) + geom_bar(stat='identity') + \
                       ggtitle(f'Gráfico de Barras - {col}')
            elif self.graph_type == 'bigotes':
                plot = ggplot(self.df, aes(x=1, y=col)) + geom_boxplot() + \
                       ggtitle(f'Gráfico de Bigotes - {col}')
            
            plot.make()
            buffer = BytesIO()
            plt.savefig(buffer, format='png')
            plt.close()
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            return f'<img src="data:image/png;base64,{image_base64}" class="img-fluid">'
        else:
            # Para múltiples columnas con ggplot necesitamos hacer un grid manual
            import matplotlib.gridspec as gridspec
            
            fig = plt.figure(figsize=(10, 5*len(self.valid_columns)))
            gs = gridspec.GridSpec(len(self.valid_columns), 1)
            
            for i, col in enumerate(self.valid_columns):
                ax = fig.add_subplot(gs[i, 0])
                if self.graph_type == 'lineas':
                    plot = ggplot(self.df, aes(x='x', y=col)) + geom_line()
                elif self.graph_type == 'barras':
                    plot = ggplot(self.df, aes(x='x', y=col)) + geom_bar(stat='identity')
                elif self.graph_type == 'bigotes':
                    plot = ggplot(self.df, aes(x=1, y=col)) + geom_boxplot()
                
                plot._make_plot(ax)
                ax.set_title(col)
            
            plt.tight_layout()
            buffer = BytesIO()
            plt.savefig(buffer, format='png')
            plt.close()
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            return f'<img src="data:image/png;base64,{image_base64}" class="img-fluid">'

    def _render_matplotlib(self):
        import matplotlib.pyplot as plt
        from io import BytesIO
        import base64
        
        plt.figure(figsize=(10, 6))
        
        if len(self.valid_columns) == 1:
            col = self.valid_columns[0]
            if self.graph_type == 'lineas':
                plt.plot(self.df['x'], self.df[col])
                plt.title(f'Gráfico de Líneas - {col}')
            elif self.graph_type == 'barras':
                plt.bar(self.df['x'], self.df[col])
                plt.title(f'Gráfico de Barras - {col}')
            elif self.graph_type == 'bigotes':
                plt.boxplot(self.df[col])
                plt.title(f'Gráfico de Bigotes - {col}')
            plt.xlabel('x')
            plt.ylabel(col)
        else:
            fig, axes = plt.subplots(len(self.valid_columns), 1, 
                                    figsize=(10, 5*len(self.valid_columns)))
            if len(self.valid_columns) == 1:
                axes = [axes]
            
            for i, col in enumerate(self.valid_columns):
                if self.graph_type == 'lineas':
                    axes[i].plot(self.df['x'], self.df[col])
                elif self.graph_type == 'barras':
                    axes[i].bar(self.df['x'], self.df[col])
                elif self.graph_type == 'bigotes':
                    axes[i].boxplot(self.df[col])
                axes[i].set_title(col)
                axes[i].set_xlabel('x')
                axes[i].set_ylabel(col)
            
            plt.tight_layout()
        
        buffer = BytesIO()
        plt.savefig(buffer, format='png')
        plt.close()
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return f'<img src="data:image/png;base64,{image_base64}" class="img-fluid">'
    