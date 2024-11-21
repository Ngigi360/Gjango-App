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
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import ee
import json

@csrf_exempt
def home_engine(request):
    return render(request, 'home-engine.html',{
        "Senser1_Lat":-0.9353436795002926,
        "Senser1_Long" :37.54556440748164,
        "senser1Geofence": {"type":"Polygon","coordinates":[[[37.532464,-0.932339],[37.533579,-0.94607],[37.554599,-0.945812],[37.553659,-0.929163],[37.532464,-0.932339]]]},
        "Senser2_Lat":-0.8429139763534353,
        "Senser2_Long": 37.44225988243562,
        "senser2Geofence": {"type":"Polygon","coordinates":[[[37.433852,-0.836992],[37.434882,-0.848321],[37.446807,-0.847634],[37.446807,-0.834933],[37.433852,-0.836992]]]},

        })

@csrf_exempt
def analyze_roi(request):
    if request.method == "POST":
        ee.Authenticate()
        ee.Initialize(project='ee-francisngigi433')

        # Extract ROI GeoJSON from POST request
        aoi_geojson = request.POST.get('aoi')
        try:
            # Parse GeoJSON string into a Python dictionary
            print(f"GeoGSON: {aoi_geojson}")
            aoi_dict = json.loads(aoi_geojson)
            print(f"AOI Dict: {aoi_dict}")
            # Convert the dictionary to Earth Engine Geometry
            aoi = ee.Geometry(aoi_dict)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid GeoJSON format"}, status=400)

        # Load and process Sentinel-2 data
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
            s2.filterDate("2024-03-01", "2024-05-30")
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 23))
            .filterBounds(aoi)
            .map(lambda img: img.clip(aoi))
            .map(maskS2clouds)
        )


        required_bands = ["B4", "B3", "B2", "B8"]
        dataset = dataset.median().select(required_bands)

        ndwi = dataset.normalizedDifference(["B3", "B8"]).rename("NDWI")

        waterThreshold = 0.3
        waterMask = ndwi.gt(waterThreshold).selfMask()

        # Calculate flood extent
        floodArea = waterMask.multiply(ee.Image.pixelArea()).divide(1e6)  # in square kilometers
        floodStats = floodArea.reduceRegion(
            reducer=ee.Reducer.sum(), geometry=aoi, scale=10, maxPixels=1e9
        )
        flood_area_sq_km = floodStats.getInfo().get("NDWI", 0)
        flood_area_sq_km = round(flood_area_sq_km, 2)

     
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
        exposed_population = int(exposed_population)

        # Load Global Surface Water dataset for water level monitoring
        gsw = ee.Image("JRC/GSW1_4/GlobalSurfaceWater")
        waterOccurrence = gsw.select('occurrence').clip(aoi)

        # Calculate permanent water bodies
        permanent_water = waterOccurrence.gt(80).selfMask()

        # Compute distance to permanent water
        distance = permanent_water.fastDistanceTransform().divide(30).clip(aoi).reproject('EPSG:4326', None, 30)

        # Load elevation data (SRTM DEM)
        srtm = ee.Image("USGS/SRTMGL1_003").clip(aoi).reproject('EPSG:4326', None, 30)
        slope = ee.Terrain.slope(srtm)
        velocity = slope.divide(10)
        flow_time = distance.divide(velocity).mask(velocity.gt(0)).rename('FlowTime')

        # Convert flow time to minutes
        flow_time_minutes = flow_time.divide(60)

        # Add layers to the analysis with correct scaling for DEM and Flow Time
        analysis_layers = {
            "aoi": aoi_dict,
            "water_occurrence": waterOccurrence.getMapId({'min': 0, 'max': 100, 'palette': ['white', 'blue']})['tile_fetcher'].url_format,
            "ndwi": ndwi.getMapId({'min': -1, 'max': 1, 'palette': ['00FFFF', '0000FF']})['tile_fetcher'].url_format,
            "population": population.getMapId({'min': 0.0016165449051186442, 'max': 10.273528099060059, 'palette': ['white', 'yellow', 'orange', 'red']})['tile_fetcher'].url_format,
            "dataset_without_cloud": dataset.getMapId(rgb_vis)['tile_fetcher'].url_format,
            "permanent_water": permanent_water.getMapId({'palette': 'blue'})['tile_fetcher'].url_format,
            "distance": distance.getMapId({'max': 500, 'min': 0, 'palette': ['blue', 'cyan', 'green', 'yellow', 'red']})['tile_fetcher'].url_format,
            "elevation": srtm.getMapId({'min': 1000, 'max': 1500, 'palette': ['green', 'yellow', 'red']})['tile_fetcher'].url_format,
            "slope": slope.getMapId({'min': 0, 'max': 22, 'palette': ['white', 'green', 'yellow', 'red']})['tile_fetcher'].url_format,
            "flow_velocity": flow_time.getMapId({'min': 0, 'max': 6, 'palette': ['blue', 'cyan', 'yellow', 'red']})['tile_fetcher'].url_format,
            "flow_time_minutes": flow_time_minutes.getMapId({'min': 0, 'max': 500, 'palette': ['blue', 'cyan', 'yellow', 'red']})['tile_fetcher'].url_format,
        }

        # Return the analysis results
        return JsonResponse({
            "flood_area_sq_km": flood_area_sq_km,
            "exposed_population": exposed_population,
            "analysis_layers": analysis_layers,
        })

    return JsonResponse({"error": "Invalid request method"}, status=400)
