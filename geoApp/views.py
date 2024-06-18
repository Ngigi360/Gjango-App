from django.shortcuts import render, redirect
from django.http import HttpRequest
import os
import ee
import folium

from .private import ENGINE_PROJECT

ee.Authenticate()
# ee.Initialize('francisngigi433')
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

from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
import ee
import json

@csrf_exempt
def home_engine(request):
    return render(request, 'home-engine.html')

@csrf_exempt
def analyze_roi(request):
    if request.method == "POST":
        ee.Authenticate()
        ee.Initialize(project='ee-francisngigi433')

        # Extract ROI GeoJSON from POST request
        aoi_geojson = request.POST.get('aoi')
        try:
            # Parse GeoJSON string into a Python dictionary
            aoi_dict = json.loads(aoi_geojson)
            # Convert the dictionary to Earth Engine Geometry
            aoi = ee.Geometry(aoi_dict)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid GeoJSON format"}, status=400)

        # Load and process the Sentinel-2 data
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

        # Extract the required bands
        required_bands = ["B4", "B3", "B2", "B8"]
        dataset = dataset.median().select(required_bands)

        # Calculate NDWI (Normalized Difference Water Index)
        ndwi = dataset.normalizedDifference(["B3", "B8"]).rename("NDWI")

        # Threshold NDWI to create a binary water mask
        waterThreshold = 0.3
        waterMask = ndwi.gt(waterThreshold).selfMask()

        # Calculate flood extent
        floodArea = waterMask.multiply(ee.Image.pixelArea()).divide(1e6)  # in square kilometers
        floodStats = floodArea.reduceRegion(
            reducer=ee.Reducer.sum(), geometry=aoi, scale=10, maxPixels=1e9
        )
        flood_area_sq_km = floodStats.getInfo().get("NDWI", 0)

        # Load population data
        population = (
            ee.ImageCollection("WorldPop/GP/100m/pop")
            .filterDate("2020-01-01", "2024-05-20")
            .median()
            .clip(aoi)
        )

        # Calculate the number of exposed people
        exposedPopulation = population.updateMask(waterMask)
        exposedPopStats = exposedPopulation.reduceRegion(
            reducer=ee.Reducer.sum(), geometry=aoi, scale=100, maxPixels=1e9
        )
        exposed_population = exposedPopStats.getInfo().get("population", 0)

        # Load Global Surface Water dataset for water level monitoring
        gsw = ee.ImageCollection("JRC/GSW1_4/MonthlyHistory").filterBounds(aoi).filterDate("2021-01-01", "2024-06-01")
        waterOccurrence = gsw.select("water").mean().clip(aoi)

        # Check if the water occurrence dataset is empty
        waterOccurrenceStats = waterOccurrence.reduceRegion(
            reducer=ee.Reducer.count(), geometry=aoi, scale=30, maxPixels=1e9
        ).getInfo()
        water_occurrence_count = waterOccurrenceStats.get("water", 0)

        # Calculate and display water level statistics
        waterOccurrenceMeanStats = waterOccurrence.reduceRegion(
            reducer=ee.Reducer.mean(), geometry=aoi, scale=30, maxPixels=1e9
        ).getInfo()
        mean_water_level = waterOccurrenceMeanStats.get("water", None)

        # Prepare the layers to be sent to the frontend
        analysis_layers = {
            "aoi": aoi_dict,
            "water_occurrence": waterOccurrence.getMapId({'min': 0, 'max': 100, 'palette': ['white', 'blue']})['tile_fetcher'].url_format,
            "ndwi": ndwi.getMapId({'min': -1, 'max': 1, 'palette': ['00FFFF', '0000FF']})['tile_fetcher'].url_format,
            "water_mask": waterMask.getMapId({'palette': 'blue'})['tile_fetcher'].url_format,
            "exposed_population": exposedPopulation.getMapId({'min': 0, 'max': 500, 'palette': ['red', 'yellow']})['tile_fetcher'].url_format,
            "dataset_without_cloud": dataset.getMapId(rgb_vis)['tile_fetcher'].url_format,
        }

        # Return the analysis results
        return JsonResponse({
            "flood_area_sq_km": flood_area_sq_km,
            "exposed_population": exposed_population,
            "mean_water_level": mean_water_level,
            "water_occurrence_count": water_occurrence_count,
            "analysis_layers": analysis_layers,
        })

    return JsonResponse({"error": "Invalid request method"}, status=400)
