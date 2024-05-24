from django.shortcuts import render, redirect
from django.http import HttpRequest
import os
import ee
import folium

from .private import ENGINE_PROJECT


# Create your views here.
def home(request: HttpRequest):
    shp_dir = os.path.join(os.getcwd(), "media", "shp")

    m = folium.Map(location=[-0.8952018385249169, 37.46995686465638], zoom_start=12)

    # Style for GeoJson
    style_Tana = {"color": "blue"}

    # Add the GeoJson layer
    folium.GeoJson(
        os.path.join(shp_dir, "Tana.geojson"),
        name="Tana",
        style_function=lambda x: style_Tana,
    ).add_to(m)

    # List of points with their coordinates and water levels around the zoom location
    points = [
        {
            "location": [-0.846078, 37.350598],
            "station_name": "Station 1",
            "current_level": "4.0 m",
            "warning_level": "4.0 m",
            "danger_level": "5.0 m",
        },
        {
            "location": [-0.920983, 37.451745],
            "station_name": "Station 2",
            "current_level": "3.0 m",
            "warning_level": "4.0 m",
            "danger_level": "5.0 m",
        },
        {
            "location": [-0.884660, 37.564385],
            "station_name": "Station 3",
            "current_level": "7.0 m",
            "warning_level": "4.0 m",
            "danger_level": "5.0 m",
        },
    ]

    # Add points with popups
    for point in points:
        popup_text = (
            f"Station name: {point['station_name']}<br>"
            f"Current Water Level: {point['current_level']}<br>"
            f"Warning Water Level: {point['warning_level']}<br>"
            f"Danger Water Level: {point['danger_level']}"
        )
        folium.Marker(
            location=point["location"],
            popup=folium.Popup(popup_text, max_width=300),
            icon=folium.Icon(color="red", icon="info-sign"),
        ).add_to(m)

    # Add Google Maps layer
    folium.raster_layers.TileLayer(
        tiles="https://mt1.google.com/vt/lyrs=r&x={x}&y={y}&z={z}",
        attr="Map data © Google",
        name="Google Maps",
    ).add_to(m)

    # Add ESRI Satellite layer
    folium.raster_layers.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles © Esri — Source: Esri, DeLorme, NAVTEQ, USGS, Intermap, iPC, NRCAN, Esri Japan, METI, Esri China (Hong Kong), Esri (Thailand), TomTom, 2012",
        name="Satellite",
    ).add_to(m)

    # Add layer control
    folium.LayerControl().add_to(m)

    # Add custom legend
    legend_html = """
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
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    # Export map to HTML representation
    m = m._repr_html_()
    context = {"my_map": m}
    return render(request, "geoApp/home.html", context)


def home_engine(request: HttpRequest):
    # Authenticate and initialize the Earth Engine API
    ee.Authenticate()
    ee.Initialize(project=ENGINE_PROJECT)  # TODO: use your project name

    aoi = ee.Geometry.Polygon(
        [
            [37.27053144574261, -0.9875559427165509],
            [37.65917280316449, -0.9875559427165509],
            [37.65917280316449, -0.774721128627668],
            [37.27053144574261, -0.774721128627668],
            [37.27053144574261, -0.9875559427165509],
        ]
    )

    s2 = ee.ImageCollection("COPERNICUS/S2_HARMONIZED")
    rgb_vis = {
        "opacity": 1,
        "bands": ["B4", "B3", "B2"],
        "min": 392.63,
        "max": 1694.87,
        "gamma": 1,
    }

    def maskS2clouds(image):
        qa = image.select("QA60")
        cloudBitMask = 1 << 10
        cirrusBitMask = 1 << 11
        mask = qa.bitwiseAnd(cloudBitMask).eq(0).And(qa.bitwiseAnd(cirrusBitMask).eq(0))
        return image.updateMask(mask)

    dataset = (
        s2.filterDate("2024-02-01", "2024-05-15")
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 23))
        .filterBounds(aoi)
        .map(lambda img: img.clip(aoi))
        .map(maskS2clouds)
    )

    print(dataset.getInfo())

    required_bands = ["B4", "B3", "B2", "B8"]
    dataset = dataset.median().select(required_bands)

    ndwi = dataset.normalizedDifference(["B3", "B8"]).rename("NDWI")

    waterThreshold = 0.3
    waterMask = ndwi.gt(waterThreshold).selfMask()

    floodArea = waterMask.multiply(ee.Image.pixelArea()).divide(
        1e6
    )  # in square kilometers
    floodStats = floodArea.reduceRegion(
        reducer=ee.Reducer.sum(), geometry=aoi, scale=10, maxPixels=1e9
    )
    print("Flooded Area (sq km):", floodStats.getInfo())

    population = (
        ee.ImageCollection("WorldPop/GP/100m/pop")
        .filterDate("2020-01-01", "2024-05-20")
        .median()
        .clip(aoi)
    )

    exposedPopulation = population.updateMask(waterMask)
    exposedPopStats = exposedPopulation.reduceRegion(
        reducer=ee.Reducer.sum(), geometry=aoi, scale=100, maxPixels=1e9
    )
    print("Exposed Population:", exposedPopStats.getInfo())

    def add_ee_layer(self, ee_image_object, vis_params, name):
        map_id_dict = ee.Image(ee_image_object).getMapId(vis_params)
        folium.raster_layers.TileLayer(
            tiles=map_id_dict["tile_fetcher"].url_format,
            attr="Google Earth Engine",
            name=name,
            overlay=True,
            control=True,
        ).add_to(self)

    folium.Map.add_ee_layer = add_ee_layer

    map = folium.Map(location=[-0.881, 37.464], zoom_start=10)

    aoi_geojson = aoi.getInfo()
    folium.GeoJson(aoi_geojson, name="AOI").add_to(map)

    map.add_ee_layer(dataset, rgb_vis, "Dataset (without cloud)")
    map.add_ee_layer(
        ndwi, {"min": -1, "max": 1, "palette": ["00FFFF", "0000FF"]}, "NDWI"
    )
    map.add_ee_layer(waterMask, {"palette": "blue"}, "Water Mask")
    map.add_ee_layer(
        exposedPopulation,
        {"min": 0, "max": 500, "palette": ["red", "yellow"]},
        "Exposed Population",
    )

    map.add_child(folium.LayerControl())

    map.save("pages/home-engine.html")

    # TODO: extract the html relevant portion of the saved html and populate the custom template
    return render(request, "home-engine.html")
