import streamlit as st
import folium
from streamlit_folium import st_folium

st.write("oi")

# center on Liberty Bell, add marker
m = folium.Map(location=[-2.532567, -45.123527], zoom_start=16)
folium.Marker(
    [-2.532567, -45.123527], popup="Liberty Bell", tooltip="Liberty Bell"
).add_to(m)

# call to render Folium map in Streamlit
st_data = st_folium(m, width=1025)

botao = st.sidebar.selectbox
valor_slider = st.slider('Defina o valor', min_value=50, max_value=100, step=1)