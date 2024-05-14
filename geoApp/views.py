from django.shortcuts import render, redirect
import os
import folium

# Create your views here.
def home(request):
    shp_dir = os.path.join(os.getcwd(),'media','shp')

    # folium
    m = folium.Map(location=[-0.8952018385249169, 37.46995686465638],zoom_start=12)

    ## style
    style_Service_Area = {'fillColor': '#228B22', 'color': '#228B22'}
    style_zones= { 'color': 'blue'}
    style_boreholes= { 'color': 'red'}
    style_Tana= { 'color': 'blue'}

    ## adding to view
    # folium.raster_layers.TileLayer('Stamen Terrain', attr='Map tiles by Stamen Design, under CC BY 3.0. Data by OpenStreetMap, under ODbL.')
    # folium.GeoJson(os.path.join(shp_dir,'Service_Area.geojson'),name='Service_Area',style_function=lambda x:style_Service_Area).add_to(m)
    # folium.GeoJson(os.path.join(shp_dir,'zones.geojson'),name='zones',style_function=lambda x:style_zones).add_to(m)
    # folium.GeoJson(os.path.join(shp_dir,'boreholes.geojson'),name='boreholes',style_function=lambda s:style_boreholes).add_to(m)
    folium.GeoJson(os.path.join(shp_dir,'Tana.geojson'),name='Tana',style_function=lambda x:style_Tana).add_to(m)
    # folium.LayerControl().add_to(m)

    folium.raster_layers.TileLayer('Stamen Terrain', attr='Map tiles by Stamen Design, under CC BY 3.0. Data by OpenStreetMap, under ODbL.').add_to(m)
    # folium.raster_layers.TileLayer('stamen Terrain').add_to(m)
    # folium.raster_layers.TileLayer('stamen Toner').add_to(m)
    # folium.raster_layers.TileLayer('stamen Watercolor').add_to(m)
    # folium.raster_layers.TileLayer('CartoDB Positron').add_to(m)
   
    folium.LayerControl().add_to(m) 

    ## exporting
    m=m._repr_html_()
    context = {'my_map': m}

    ## rendering
    return render(request,'geoApp/home.html',context)




