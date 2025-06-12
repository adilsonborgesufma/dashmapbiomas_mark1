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
    ee.Initialize(project='ee-adilsonborges')
except:
    st.warning("Falha na autenticação do Earth Engine. Por favor, verifique suas credenciais.")

st.set_page_config(layout='wide')

# Título e descrição
st.title("APP MAPBIOMAS GLOBE - Alcântara/MA")
st.write("""Dashboard interativo de uso e cobertura da terra no município de Alcântara/MA""")

# Carregar o shapefile do município diretamente do seu Asset
try:
    alcantara_shape = ee.FeatureCollection("projects/ee-adilsonborges/assets/Municipio_Alcantara_WGS84")
    geometry = alcantara_shape.geometry()
    st.success("Shapefile de Alcântara carregado com sucesso do seu GEE Asset!")
except Exception as e:
    st.error(f"Erro ao carregar o shapefile: {str(e)}")
    geometry = None

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

# Recortar a imagem para o município de Alcântara
if geometry:
    remapped_image = remapped_image.clip(geometry)

# Seleção de anos
years = list(range(1985, 2024))
selected_years = st.multiselect('Selecione o(s) ano(s)', years, default=[2023])

# Criar mapa
m = geemap.Map(center=[-2.4, -44.4], zoom=10)  # Coordenadas aproximadas de Alcântara

# Adicionar o shapefile de Alcântara ao mapa
if geometry:
    m.addLayer(geometry, {'color': 'red', 'width': 2}, 'Alcântara/MA')

# Adicionar as bandas selecionadas ao mapa
for year in selected_years:
    selected_band = f"classification_{year}"
    m.addLayer(
        remapped_image.select(selected_band),
        {
            'palette': palette,
            'min': 1,
            'max': 6
        },
        f"Classificação {year}"
    )

# Exibir o mapa
m.to_streamlit(height=600)

# Calcular e exibir estatísticas
if geometry:
    st.subheader(f"Estatísticas de Área por Classe - Alcântara/MA")
    areas = []
    for year in selected_years:
        band = remapped_image.select(f"classification_{year}")
        for class_value in range(1, 7):
            class_area = band.eq(class_value).multiply(ee.Image.pixelArea()).reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=geometry,
                scale=30,
                maxPixels=1e13
            ).getInfo()
            area_km2 = class_area.get(f"classification_{year}", 0) / 1e6
            areas.append({
                "Ano": year,
                "Classe": class_value,
                "Nome da Classe": class_names.get(class_value, "Desconhecido"),
                "Área (km²)": round(area_km2, 2)
            })
    
    df = pd.DataFrame(areas)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.dataframe(df)
    
    if len(selected_years) > 1:
        with col2:
            fig = px.bar(
                df,
                x="Ano",
                y="Área (km²)",
                color="Nome da Classe",
                title=f"Evolução do Uso do Solo em Alcântara/MA",
                color_discrete_sequence=palette,
                category_orders={"Ano": sorted(df["Ano"].unique())},
                barmode='stack'  # Barras empilhadas
            )
            fig.update_layout(
                yaxis_title="Área (km²)",
                xaxis_title="Ano",
                hovermode="x unified",
                legend_title="Classes de Uso do Solo"
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Selecione mais de um ano para visualizar o gráfico de evolução temporal.")