import streamlit as st
import geemap
import folium
import geemap.foliumap as geemap
import ee
import json
import pandas as pd
import plotly.express as px

# Autenticar e inicializar o Earth Engine
try:
    ee.Authenticate()
    ee.Initialize(project='ee-adilsonborges')
except:
    st.warning("Falha na autenticação do Earth Engine. Por favor, verifique suas credenciais.")

st.set_page_config(layout='wide')

# Título e descrição
st.title("APP MAPBIOMAS GLOBE")
st.write("""Texto descritivo sobre a aplicação""")

### PROCESSAMENTO DAS IMAGENS
mapbiomas_image = ee.Image('projects/mapbiomas-public/assets/brazil/lulc/collection9/mapbiomas_collection90_integration_v1')

# Códigos das classes originais
codes = [
    1, 3, 4, 5, 6, 49,    # Floresta e subcategorias
    10, 11, 12, 32, 29, 50,    # Vegetação Herbácea e Arbustiva e subcategorias
    14, 15, 18, 19, 39, 20, 40, 62, 41, 36, 46, 47, 35, 48, 9, 21,    # Agropecuária e subcategorias
    22, 23, 24, 30, 25,    # Área não Vegetada e subcategorias
    26, 33, 31,    # Corpo D'água e subcategorias
    27    # Não Observado
]

# Novas classes agrupadas
new_classes = [
    1, 1, 1, 1, 1, 1,    # Floresta e subcategorias
    2, 2, 2, 2, 2, 2,    # Vegetação Herbácea e Arbustiva e subcategorias
    3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3,    # Agropecuária e subcategorias
    4, 4, 4, 4, 4,    # Área não Vegetada e subcategorias
    5, 5, 5,    # Corpo D'água e subcategorias
    6    # Não Observado
]

# Paleta de cores para visualização
palette = [
    "#1f8d49", #1 floresta
    "#d6bc74", #2 Vegetacao_Herbacea
    "#ffefc3", #3 Agropecuaria
    "#d4271e", #4 Area_Nao_Vegetada
    "#2532e4", #5 Corpo de Agua
    "#ffffff", #6 Nao observado
]

# Nomes das classes
class_names = {
    1: "Floresta",
    2: "Vegetação Herbácea",
    3: "Agropecuária",
    4: "Área não Vegetada",
    5: "Corpo D'água",
    6: "Não observado"
}

# Reclassificar as bandas
remapped_bands = []
for year in range(1985, 2024):
    original_band = f'classification_{year}'
    remapped_band = mapbiomas_image.select(original_band).remap(codes, new_classes).rename(original_band)
    remapped_bands.append(remapped_band)
    
remapped_image = ee.Image.cat(remapped_bands)

# Seleção de anos
years = list(range(1985, 2024))
selected_years = st.multiselect('Selecione o(s) ano(s)', years, default=[2023])

# Entrada da geometria
with st.expander('Defina a área de estudo (opcional)'):
    geometry_input = st.text_area("Insira as coordenadas de área em formato GeoJSON")

# Verificar geometria
geometry = None
if geometry_input:
    try:
        geometry = ee.Geometry(json.loads(geometry_input)['geometry'])
    except Exception as e:
        st.error(f'Erro no formato de Coordenadas. Verifique o GeoJson inserido: {str(e)}')

# Criar mapa
m = geemap.Map(center=[-15, -55], zoom=6)

# Se houver geometria, aplicar recorte e centralizar o mapa
if geometry:
    # Criar coleção de feições com a geometria
    study_area = ee.FeatureCollection([ee.Feature(geometry)])
    
    # Centralizar o mapa na área de estudo com zoom adequado
    m.centerObject(study_area, zoom=10)  # Ajustar o zoom conforme necessário
    
    # Adicionar camada da área de estudo com estilo
    m.addLayer(study_area, {'color': 'red', 'width': 2}, 'Área de estudo')
    
    # Recortar a imagem reclassificada pela geometria
    remapped_image = remapped_image.clip(geometry)

# Adicionar as bandas selecionadas ao mapa
for year in selected_years:
    # Selecionar a banda correspondente ao ano
    selected_band = f"classification_{year}"
    
    # Adicionar a camada ao mapa com a paleta de cores
    m.addLayer(
        remapped_image.select(selected_band),
        {
            'palette': palette,  # Paleta de cores definida anteriormente
            'min': 1,            # Valor mínimo da classificação
            'max': 6             # Valor máximo da classificação
        },
        f"Classificação Remapeada {year}"  # Nome da camada com o ano
    )

# Exibir o mapa
m.to_streamlit(height=600)

# Calcular e exibir estatísticas se houver geometria
if geometry:
    st.subheader("Estatísticas de Área por Classe")
    areas = []
    for year in selected_years:
        band = remapped_image.select(f"classification_{year}")
        for class_value in range(1, 7):  # Classes de 1 a 6
            class_area = band.eq(class_value).multiply(ee.Image.pixelArea()).reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=geometry,
                scale=30,
                maxPixels=1e13
            ).getInfo()
            area_km2 = class_area.get(f"classification_{year}", 0) / 1e6  # Converter para km²
            areas.append({
                "Ano": year,
                "Classe": class_value,
                "Nome da Classe": class_names.get(class_value, "Desconhecido"),
                "Área (km²)": area_km2
            })
    
    # Converter dados de área para um DataFrame
    df = pd.DataFrame(areas)
    
    # Layout de colunas
    col1, col2 = st.columns(2)
    
    # Exibir DataFrame e gráfico lado a lado
    with col1:
        st.dataframe(df)
    
    # Exibir gráfico apenas se houver mais de um ano selecionado
    if len(selected_years) > 1:
        with col2:
            # Criar gráfico de área com Plotly
            fig = px.area(
                df,
                x="Ano",
                y="Área (km²)",
                color="Nome da Classe",
                title="Evolução da Área por Classe ao Longo do Tempo",
                color_discrete_sequence=palette,
                category_orders={"Ano": sorted(df["Ano"].unique())}  # Garantir ordem cronológica
            )
            # Melhorar layout do gráfico
            fig.update_layout(
                yaxis_title="Área (km²)",
                xaxis_title="Ano",
                hovermode="x unified"
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Selecione mais de um ano para visualizar o gráfico de evolução temporal.")