import pandas as pd
from geopy.geocoders import Nominatim
import haversine as hs

geolocator = Nominatim(timeout=10, user_agent = "metaEventsGeoLocator")

import plotly.express as px
import plotly.graph_objects as go

import dash
import dash_mantine_components as dmc
import dash_leaflet as dl

from dash import dcc, callback
from dash import html, dash_table
from dash.dependencies import Input, Output

import datetime
from datetime import datetime as dt


# Criação do DataFrame de exemplo

# Tratamento dos dados dos eventos SBC
sbc = pd.read_json('./metaevents/sbc_eventos.json')
sbc.dropna(subset=['location'], inplace=True)

current_location = dcc.Geolocation("geolocation")

# Criando as colunas para georreferenciamento
sbc['gcode'] = sbc.location.apply(geolocator.geocode)

# Removendo linhas que não foram georreferenciadas
sbc.dropna(subset=['gcode'], inplace=True)

# Criando as novas colunas de latitude e longitude e das coordenadas
sbc['lat'] = [g.latitude for g in sbc.gcode]
sbc['long'] = [g.longitude for g in sbc.gcode]
sbc['coor'] = list(zip(sbc.lat, sbc.long))

# sbc['data_inicio'] = sbc['start_at'].apply(pd.Series)
sbc['data_inicio'] = pd.to_datetime(sbc['start_at']).dt.date

sbc.dropna(subset=['finish_at'], inplace=True)
# sbc['data_fim'] = sbc['finish_at'].apply(pd.Series)
sbc['data_fim'] = pd.to_datetime(sbc['finish_at']).dt.date


def distance_from(loc1,loc2): 
    dist=hs.haversine(loc1,loc2)
    return round(dist,2)

actual = {'local': 'distancia', 'coor': [(-7.1153613, -34.8544595)]}
df = pd.DataFrame(data=actual)

for _,row in df.iterrows():
    sbc[row.local]=sbc['coor'].apply(lambda x: distance_from(row.coor,x))


sbc_table_display = sbc[['title', 'qualis', 'data_inicio', 'data_fim', 'location', 'distancia']].copy()



lista_localidade = sbc['location'].dropna().unique()

sbc_groupby = sbc.groupby(['location'])['location'].count().sort_values(ascending=False).reset_index(name='Total')
sbc_groupby_state = sbc.groupby(['state'])['state'].count().sort_values(ascending=False).reset_index(name='Total')
sbc_groupby_qualis = sbc.groupby(['qualis'])['qualis'].count().sort_values(ascending=False).reset_index(name='Total')

sbc_groupby_date = sbc.groupby(['data_inicio'])['data_inicio'].count().sort_values(ascending=False).reset_index(name='Total')

sbc_groupby_dist = sbc[sbc['distancia'] < 500]

by_month = pd.to_datetime(sbc['data_inicio']).dt.to_period('M').value_counts().sort_index()
by_month.index = pd.PeriodIndex(by_month.index)
sbc_by_month = by_month.rename_axis('mes').reset_index(name='Total')


# wikicfp_groupby = dados.groupby(['location'])['location'].count().sort_values(ascending=False).reset_index(name='Total')


# Inicialização do aplicativo Dash
external_stylesheets = [dmc.theme.DEFAULT_COLORS]

app = dash.Dash(__name__)

app.title = "Dashboard EventComp"


# definição dos gráficos básicos

fig = px.bar(sbc_groupby, x="location", y="Total")
state_bar_fig = px.bar(sbc_groupby_state, x="state", y="Total")
qualis_bar_fig = px.bar(sbc_groupby_qualis, x="qualis", y="Total")

line_fig = go.Figure(data=go.Bar(x=sbc_by_month['mes'].astype(dtype=str), 
                        y=sbc_by_month['Total'],
                        marker_color='LightSkyBlue'))

# definição do mapa básico com scatterplot

map_fig = px.scatter_mapbox(sbc, lat="lat", lon="long", hover_name="location", hover_data=["location", "title"],
                        color_discrete_sequence=["fuchsia"], zoom=3, height=300)
map_fig.update_layout(mapbox_style="open-street-map")
map_fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})

# definição dos kpis

kpi_fig = go.Figure()
#kpi_fig2 = go.Figure()

kpi_fig.add_trace(go.Indicator(
    mode = "number",
    value = len(sbc),
    number = {"font.size": 48},
    title = {'text': "Total de Eventos SBC"},
    domain = {'row': 0, 'column': 0}))

kpi_fig.add_trace(go.Indicator(
    mode = "number",
    value = len(sbc_groupby_dist),
    number = {"font.size": 48},
    title = {'text': "Eventos SBC Próximos de sua Localidade"},
    domain = {'row': 0, 'column': 1}))

kpi_fig.add_trace(go.Indicator(
    mode = "number",
    value = len(sbc_table_display[sbc_table_display.qualis.notnull()]),
    number = {"font.size": 48},
    title = {'text': "Eventos Qualis"},
    domain = {'row': 0, 'column': 2}))

kpi_fig.update_layout(
    grid = {'rows': 1, 'columns': 3, 'pattern': "independent"},
    height=200,
  )

# definição do gráfico timeline
time_fig = px.timeline(
    sbc, x_start="data_inicio", x_end="data_fim", y="city", 
    hover_data=['title', 'description', 'location'], 
    color='location'
    
)


def description_card():
    """
    :return: A Div containing dashboard title & descriptions.
    """
    return html.Div(
        id="description-card",
        children=[
            
            html.H3("Dashboard Analítico de Eventos Qualis de Computação"),
            html.Div(
                id="intro",
                children="Explore o volume de eventos por período e local de realização, tipo de estrato Qualis e pontuação. Clique nos pontos dos gráficos para mais detalhes.",

            ),
            html.Br(),
        ],
    )

def generate_control_card():
    """
    :return: A Div containing controls for graphs.
    """
    return html.Div(
        id="control-card",
        children=[
            html.P("Selecione Localidade"),
            dcc.Dropdown(
                id="location-select",
                options=[{"label": i, "value": i} for i in list(lista_localidade)],
                value=lista_localidade[0],
            ),
            html.Br(),
            html.P("Selecione o Período"),
            dcc.DatePickerRange(
                id="date-picker-select",
                start_date=dt(2023, 1, 1),
                end_date=dt(2025, 1, 15),
                min_date_allowed=dt(2023, 1, 1),
                max_date_allowed=dt(2028, 12, 31),
                initial_visible_month=dt(2023, 1, 1),
            ),
            html.Br(),
            html.Br(),
            html.P("Selecione a Distância máxima"),
            html.Div([
                dcc.RangeSlider(       # this is the input
                id='range-slider',
                min=sbc['distancia'].min(),
                max=sbc['distancia'].max(),
                #marks={i:str(i) for i in range(0, 5001)},
                value=[100, 500]
                )
                ], style={'width':'100%'}),
            
            html.Br(),
            html.Div(
                id="reset-btn-outer",
                children=html.Button(id="reset-btn", children="Reset", n_clicks=0),
            ),
            html.Div(id="text_position"),
        ],
    )

# Layout do dashboard
app.layout = html.Div(
    id="app-container",
    children=[
       
        # Banner
        html.Div(
            id="banner",
            
            children=[html.Img(src=app.get_asset_url("meta-event-finder-logo2.png"), height='90')],
        ),
        # Left column
        html.Div(
            id="left-column",
            className="four columns",
            children=[description_card(), generate_control_card()]
            + [
                html.Div(
                    ["initial child"], id="output-clientside", style={"display": "none"}
                )
            ],
        ),
        # Right column
        html.Div(
            id="right-column",
            className="eight columns",
            children=[
                # Patient Volume Heatmap
                
                # Patient Wait time by Department
                html.Div(
                    id="kpi_eventos_card",
                    
                    children=[
                        html.B("Indicadores de Eventos"),
                        html.Hr(),
                        dcc.Graph(id="kpi_eventos", figure=kpi_fig, ),
                        #dcc.Graph(id="kpi_eventos", figure=kpi_fig2),
                    ],
                ),
                   
                  html.Div(
                    id="eventos_barras_card",
                    
                    children=[
                       html.Div(
                           
                           children=[
                                
                                dcc.Graph(id="eventos_sbc_por_estado", figure=state_bar_fig),
                           ] 
                        ),
                       
                    ],
                ),

                html.Div(
                    id="qualis_barras_card",
                    
                    children=[
                       html.Div(
                           
                           children=[
                                
                                dcc.Graph(id="eventos_sbc_por_qualis", figure=qualis_bar_fig),
                           ] 
                        ),
                       
                    ],
                ),
                    html.Div(
                    id="eventos_volume_card",
                    
                    children=[
                       html.Div(
                           className="four columns",
                           children=[
                                
                                dcc.Graph(id="eventos_sbc_por_localidade", figure=fig),
                           ] 
                        ),
                       html.Div( 
                           className="eight columns",
                           children=[
                               
                                dcc.Graph(id="eventos_sbc_por_data", figure=line_fig),
                                # dash_table.DataTable(id="table-eventos-localidade", data=sbc_groupby.to_dict('records'), page_size=10)
                           ]
                        ),
                    ],
                ),

                html.Div(
                    id="tabela-eventos-por-localidade",
                    
                    children=[
                        html.B("Linha do Tempo dos Eventos"),
                        html.Hr(),
                        dcc.Graph(id="eventos_sbc_timeline", figure=time_fig),
                    ],
                ),

                 html.Div(
                    id="timeline-eventos",
                    
                    children=[
                        html.B("Tabela de Eventos"),
                        html.Hr(),
                       dash_table.DataTable(id="table-eventos-localidade", data=sbc_table_display.to_dict('records'), page_size=10)
                    ],
                ),

                
                 html.Div(
                    id="mapa-eventos",
                    children=[
                        html.B("Mapa dos eventos"),
                        html.Hr(),
                        #dcc.Graph(id="eventos_sbc_timeline", figure=time_fig),
                        html.Div([
                                dl.Map([
                                    dl.TileLayer(),
                                    dl.GeoJSON(
                                        id='marker-cluster',
                                        children=[
                                            dl.Marker(position=[row['lat'], row['long']], children=[
                                                dl.Popup(row['title'])
                                                
                                            ]) for _, row in sbc.iterrows()
                                        ]
                                    )
                                ], 
                                zoom=4,
                                center=(-15.7934036, -47.8823172),
                                style={'width': '100%', 'height': '500px'}),
                                
                            ])

                    ],
                ),
            ],
        ),
    ],

    )


# Atualização dos gráficos de barra com base na seleção do filtro
@app.callback(
    Output('eventos_sbc_por_localidade', 'figure'),
    Input('location-select', 'value')
)
def update_graphs(location):
    filtered_df = sbc_groupby.apply(lambda row: row[sbc_groupby['location'].isin([location])])
    
    fig = px.bar(filtered_df, x="location", y="Total")

    return fig

@app.callback(
    Output('eventos_sbc_por_estado', 'figure'),
    Input('range-slider', 'value')
)
def update_views(distance):
    filtered_df = sbc[(sbc['distancia'] >= distance[0]) & (sbc['distancia'] <= distance[1])]
    filtered_sbc_groupby_state = filtered_df.groupby(['state'])['state'].count().sort_values(ascending=False).reset_index(name='Total')
    
    #fig = px.bar(filtered_df, x="location", y="Total")
    state_bar_fig = px.bar(filtered_sbc_groupby_state, x="state", y="Total")

    return state_bar_fig

@app.callback(
    Output('eventos_sbc_por_data', 'figure'),
    #Output('table-eventos-localidade', 'data'),
    Input('date-picker-select', 'start_date'),
    Input('date-picker-select', 'end_date')
)
def update_date_graph(start_date, end_date):
    if start_date and end_date:
        sbc['data_inicio'] = pd.to_datetime(sbc['data_inicio'])
        sbc['data_fim'] = pd.to_datetime(sbc['data_fim'])
        dff = sbc[(sbc['data_inicio'] >= start_date) & (sbc['data_fim'] <= end_date) ]

        dff_by_month = pd.to_datetime(dff['data_inicio']).dt.to_period('M').value_counts().sort_index()
        dff_by_month.index = pd.PeriodIndex(dff_by_month.index)
        dff_sbc_by_month = dff_by_month.rename_axis('mes').reset_index(name='Total')

        line_fig = go.Figure(data=go.Bar(x=dff_sbc_by_month['mes'].astype(dtype=str), 
                        y=dff_sbc_by_month['Total'],
                        marker_color='LightSkyBlue'))

        #filtered_sbc_table_display = dff[['title', 'qualis', 'data_inicio', 'data_fim', 'location', 'distancia']].copy()
        #dash_table.DataTable(id="filtered-table-eventos-localidade", data=sbc_table_display.to_dict('records'), page_size=10)
        
        
        return line_fig



# Execução do aplicativo
if __name__ == '__main__':
    app.run_server(debug=True)
