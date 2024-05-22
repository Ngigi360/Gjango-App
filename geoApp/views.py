from django.shortcuts import render, redirect
import os
import folium

# Create your views here.
def home(request):
    shp_dir = os.path.join(os.getcwd(), 'media', 'shp')
    

    m = folium.Map(location=[-0.8952018385249169, 37.46995686465638], zoom_start=12)

    # Style for GeoJson
    style_Tana = {'color': 'blue'}

    # Add the GeoJson layer
    folium.GeoJson(os.path.join(shp_dir, 'Tana.geojson'), name='Tana', style_function=lambda x: style_Tana).add_to(m)

    # List of points with their coordinates and water levels around the zoom location
    points = [
        {'location': [-0.846078, 37.350598], 'station_name': 'Station 1', 'current_level': '4.0 m', 'warning_level': '4.0 m', 'danger_level': '5.0 m'},
        {'location': [-0.920983, 37.451745], 'station_name': 'Station 2', 'current_level': '3.0 m', 'warning_level': '4.0 m', 'danger_level': '5.0 m'},
        {'location': [-0.884660, 37.564385], 'station_name': 'Station 3', 'current_level': '7.0 m', 'warning_level': '4.0 m', 'danger_level': '5.0 m'}
    ]

    # Add points with popups
    for point in points:
        popup_text = (f"Station name: {point['station_name']}<br>"
                      f"Current Water Level: {point['current_level']}<br>"
                      f"Warning Water Level: {point['warning_level']}<br>"
                      f"Danger Water Level: {point['danger_level']}")
        folium.Marker(
            location=point['location'],
            popup=folium.Popup(popup_text, max_width=300), 
            icon=folium.Icon(color='red', icon='info-sign') 
        ).add_to(m)

    # Add Google Maps layer
    folium.raster_layers.TileLayer(
        tiles='https://mt1.google.com/vt/lyrs=r&x={x}&y={y}&z={z}',
        attr='Map data © Google',
        name='Google Maps'
    ).add_to(m)

    # Add ESRI Satellite layer
    folium.raster_layers.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Tiles © Esri — Source: Esri, DeLorme, NAVTEQ, USGS, Intermap, iPC, NRCAN, Esri Japan, METI, Esri China (Hong Kong), Esri (Thailand), TomTom, 2012',
        name='Satellite'
    ).add_to(m)

    # Add layer control
    folium.LayerControl().add_to(m)

    # Add custom legend
    legend_html = '''
     <div style="position: absolute; 
                 bottom: 10px; 
                 right: 10px; 
                 width: 250px; 
                 height: 150px; 
                 border: 2px solid grey; 
                 z-index: 9999; 
                 font-size: 14px;
                 background-color: white; 
                 padding: 10px;">
     &nbsp; <b>LEGEND</b><br>
     &nbsp; <i class="fa fa-map-marker fa-2x" style="color:blue"></i>&nbsp;Water Bodies<br>
     &nbsp; <i class="fa fa-map-marker fa-2x" style="color:red"></i>&nbsp;Danger Level<br>
     &nbsp; <i class="fa fa-map-marker fa-2x" style="color:orange"></i>&nbsp;Warning Level<br>
     &nbsp; <i class="fa fa-map-marker fa-2x" style="color:green"></i>&nbsp;Normal Level<br>
     </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))

    # Export map to HTML representation
    m = m._repr_html_()
    context = {'my_map': m}
    return render(request, 'geoApp/home.html', context)
