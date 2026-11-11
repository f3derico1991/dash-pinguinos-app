import base64
import io
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from dash import Dash, Input, Output, State, dcc, html
import dash_bootstrap_components as dbc

# Inicializar la aplicación Dash con un tema moderno de Bootstrap
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server  # Exponer el servidor para despliegues (Render, Gunicorn, etc.)

COLUMNAS_REQUERIDAS = {"especie", "largo_aleta_mm", "largo_pico_mm", "masa_corporal_g"}


def parse_contents(contents, filename):
    """Parsea el archivo Excel subido mediante dcc.Upload."""
    content_type, content_string = contents.split(",")
    decoded = base64.b64decode(content_string)
    try:
        if "xlsx" in filename or "xls" in filename:
            df = pd.read_excel(io.BytesIO(decoded))
        else:
            return None, "Formato de archivo no soportado. Sube un archivo Excel (.xlsx)."
    except Exception as e:
        return None, f"Error al procesar el archivo: {e}"

    faltantes = COLUMNAS_REQUERIDAS - set(df.columns)
    if faltantes:
        return None, f"Faltan columnas obligatorias: {', '.join(sorted(faltantes))}"

    return df.dropna(subset=list(COLUMNAS_REQUERIDAS)), None


# ---------------------------------------------------------
# Layout de la Aplicación
# ---------------------------------------------------------
app.layout = dbc.Container(
    [
        # Encabezado
        dbc.Row(
            dbc.Col(
                [
                    html.H1("🐧 Guía Interactiva: Plotly & Dash", className="text-primary mt-4 mb-2"),
                    html.P(
                        "Esta aplicación demuestra cómo Dash y Plotly trabajan juntos para crear paneles analíticos interactivos.",
                        className="text-muted",
                    ),
                    html.Hr(),
                ],
                width=12,
            )
        ),
        # Cuerpo principal con barra lateral y área de contenido
        dbc.Row(
            [
                # Barra lateral (Controles y carga)
                dbc.Col(
                    [
                        html.H4("📁 Cargar datos", className="mb-3"),
                        dcc.Upload(
                            id="upload-data",
                            children=html.Div(["Arrastra o ", html.A("busca tu archivo Excel")]),
                            style={
                                "width": "100%",
                                "height": "60px",
                                "lineHeight": "60px",
                                "borderWidth": "1px",
                                "borderStyle": "dashed",
                                "borderRadius": "5px",
                                "textAlign": "center",
                                "marginBottom": "20px",
                                "backgroundColor": "#f8f9fa",
                            },
                            multiple=False,
                        ),
                        html.Div(id="output-data-status"),
                        html.Hr(),
                        html.H5("Navegación de Secciones", className="mt-3"),
                        dbc.Nav(
                            [
                                dbc.NavLink("1. Gráficos básicos", id="nav-1", href="#", active=True),
                                dbc.NavLink("2. Grilla 2x2", id="nav-2", href="#", active=False),
                                dbc.NavLink("3. Formato y anotaciones", id="nav-3", href="#", active=False),
                                dbc.NavLink("4. Análisis avanzado", id="nav-4", href="#", active=False),
                            ],
                            vertical=True,
                            pills=True,
                            id="navegacion-tabs",
                        ),
                    ],
                    width=3,
                    className="bg-light p-4 rounded",
                ),
                # Contenido Dinámico según la pestaña seleccionada
                dbc.Col(
                    [
                        html.Div(id="page-content", children=[
                            html.Div("👈 Sube tu archivo Excel de pingüinos para comenzar.", className="alert alert-info")
                        ])
                    ],
                    width=9,
                ),
            ]
        ),
        # Almacenamiento invisible en el navegador para mantener el DataFrame cargado
        dcc.Store(id="stored-dataframe"),
    ],
    fluid=True,
    className="px-4",
)


# ---------------------------------------------------------
# Callback para procesar el archivo y actualizar el Store
# ---------------------------------------------------------
@app.callback(
    [Output("stored-dataframe", "data"), Output("output-data-status", "children")],
    Input("upload-data", "contents"),
    State("upload-data", "filename"),
)
def actualizar_datos(contents, filename):
    if contents is None:
        return None, ""
    
    df, error = parse_contents(contents, filename)
    if error:
        return None, dbc.Alert(error, color="danger")
    
    return df.to_dict("records"), dbc.Alert(f"¡Archivo '{filename}' cargado con éxito!", color="success")


# ---------------------------------------------------------
# Callback para cambiar las pestañas activas
# ---------------------------------------------------------
@app.callback(
    [
        Output("nav-1", "active"),
        Output("nav-2", "active"),
        Output("nav-3", "active"),
        Output("nav-4", "active"),
        Output("page-content", "children"),
    ],
    [
        Input("nav-1", "n_clicks"),
        Input("nav-2", "n_clicks"),
        Input("nav-3", "n_clicks"),
        Input("nav-4", "n_clicks"),
    ],
    State("stored-dataframe", "data"),
)
def render_seccion(n1, n2, n3, n4, data_json):
    from dash import callback_context

    ctx = callback_context
    button_id = "nav-1"
    if ctx.triggered:
        button_id = ctx.triggered[0]["prop_id"].split(".")[0]

    # Activar estado visual de las pestañas
    active_state = [button_id == f"nav-{i}" for i in range(1, 5)]

    if data_json is None:
        return *active_state, dbc.Alert("⚠️ Por favor, sube tu archivo Excel en la barra lateral izquierda.", color="warning")

    pinguinos = pd.DataFrame(data_json)
    especies = sorted(pinguinos["especie"].unique())

    # SECCIÓN 1: Gráficos individuales básicos
    if button_id == "nav-1":
        fig_scatter = px.scatter(
            pinguinos, x="largo_aleta_mm", y="largo_pico_mm", color="especie",
            labels={"largo_aleta_mm": "Largo de aleta (mm)", "largo_pico_mm": "Largo de pico (mm)"},
            title="Largo de pico vs. largo de aleta",
        )
        fig_box = px.box(
            pinguinos, x="especie", y="masa_corporal_g", color="especie",
            labels={"masa_corporal_g": "Masa corporal (g)"},
            title="Masa corporal por especie",
        )
        fig_violin = px.violin(
            pinguinos, x="especie", y="masa_corporal_g", color="especie",
            box=True, points="all",
            labels={"masa_corporal_g": "Masa corporal (g)"},
            title="Distribución de masa corporal (violín)",
        )
        fig_hist = px.histogram(
            pinguinos, x="masa_corporal_g", color="especie",
            marginal="violin", histnorm="probability density", barmode="overlay",
            opacity=0.6,
            labels={"masa_corporal_g": "Masa corporal (g)"},
            title="Densidad de masa corporal",
        )

        return *active_state, dbc.Container([
            html.H3("1. Gráficos individuales con Plotly Express"),
            dbc.Row([
                dbc.Col(dcc.Graph(figure=fig_scatter), width=6),
                dbc.Col(dcc.Graph(figure=fig_box), width=6),
            ], className="mb-4"),
            dbc.Row([
                dbc.Col(dcc.Graph(figure=fig_violin), width=6),
                dbc.Col(dcc.Graph(figure=fig_hist), width=6),
            ]),
        ])

    # SECCIÓN 2: Grilla 2x2
    elif button_id == "nav-2":
        fig_grid = make_subplots(
            rows=2, cols=2,
            subplot_titles=("Dispersión: aleta vs. pico", "Boxplot: aleta", "Histograma: aleta", "Violín: pico"),
        )
        paleta = px.colors.qualitative.Plotly
        color_de = {esp: paleta[i % len(paleta)] for i, esp in enumerate(especies)}

        for esp in especies:
            df_esp = pinguinos[pinguinos["especie"] == esp]
            color = color_de[esp]
            fig_grid.add_trace(go.Scatter(x=df_esp["largo_aleta_mm"], y=df_esp["largo_pico_mm"], mode="markers", name=str(esp), marker=dict(color=color), legendgroup=str(esp)), row=1, col=1)
            fig_grid.add_trace(go.Box(y=df_esp["largo_aleta_mm"], name=str(esp), marker_color=color, legendgroup=str(esp), showlegend=False), row=1, col=2)
            fig_grid.add_trace(go.Histogram(x=df_esp["largo_aleta_mm"], name=str(esp), marker_color=color, legendgroup=str(esp), showlegend=False, opacity=0.7), row=2, col=1)
            fig_grid.add_trace(go.Violin(y=df_esp["largo_pico_mm"], name=str(esp), line_color=color, legendgroup=str(esp), showlegend=False), row=2, col=2)

        fig_grid.update_layout(height=750, title_text="Panel de gráficos combinados", barmode="overlay")

        return *active_state, dbc.Container([
            html.H3("2. Paneles múltiples (grilla 2x2)"),
            dcc.Graph(figure=fig_grid),
        ])

    # SECCIÓN 3: Formato y anotaciones
    elif button_id == "nav-3":
        media_pico = pinguinos["largo_pico_mm"].mean()
        media_aleta = pinguinos["largo_aleta_mm"].mean()

        fig_custom = px.scatter(
            pinguinos, x="largo_aleta_mm", y="largo_pico_mm", color="especie",
            title="Largo de pico vs. aleta (con referencias)",
            labels={"largo_aleta_mm": "Largo de aleta (mm)", "largo_pico_mm": "Largo de pico (mm)"},
            template="plotly_white",
        )
        fig_custom.add_hline(y=media_pico, line_dash="dash", line_color="green", opacity=0.5, annotation_text=f"Media pico: {media_pico:.1f} mm", annotation_position="top left")
        fig_custom.add_vline(x=media_aleta, line_dash="dash", line_color="green", opacity=0.5, annotation_text=f"Media aleta: {media_aleta:.1f} mm", annotation_position="top right")

        idx_max = pinguinos["largo_aleta_mm"].idxmax()
        fila = pinguinos.loc[idx_max]
        fig_custom.add_annotation(x=fila["largo_aleta_mm"], y=fila["largo_pico_mm"], text="Valor máximo de aleta", showarrow=True, arrowhead=2, font=dict(color="red", size=12))

        return *active_state, dbc.Container([
            html.H3("3. Personalización avanzada y anotaciones"),
            dcc.Graph(figure=fig_custom),
        ])

    # SECCIÓN 4: Análisis avanzado
    elif button_id == "nav-4":
        fig_reg = px.scatter(pinguinos, x="largo_aleta_mm", y="largo_pico_mm", color="especie", trendline="ols", title="Tendencia lineal (OLS) por especie")
        
        muestra = pinguinos.sample(n=min(len(pinguinos), 300), random_state=42)
        fig_pair = px.scatter_matrix(muestra, dimensions=["largo_aleta_mm", "largo_pico_mm", "masa_corporal_g"], color="especie")
        fig_pair.update_traces(diagonal_visible=False, showupperhalf=False)
        fig_pair.update_layout(height=700)

        conteo = pinguinos["especie"].value_counts().reset_index()
        conteo.columns = ["especie", "cantidad"]
        fig_count = px.bar(conteo, x="especie", y="cantidad", color="especie", title="Conteo de pingüinos por especie")

        return *active_state, dbc.Container([
            html.H3("4. Análisis estadístico y matrices"),
            dbc.Tabs([
                dbc.Tab(dcc.Graph(figure=fig_reg), label="Regresión lineal"),
                dbc.Tab(dcc.Graph(figure=fig_pair), label="Matriz de dispersión"),
                dbc.Tab(dcc.Graph(figure=fig_count), label="Conteo por categoría"),
            ], className="mt-3")
        ])

    return *active_state, html.Div()


if __name__ == "__main__":
    app.run(debug=True)