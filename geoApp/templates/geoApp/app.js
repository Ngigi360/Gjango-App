// Initialize Map (Leaflet.js)
var map = L.map('map').setView([-13.9631, 33.7741], 7); // Centered over Malawi

// Use OpenStreetMap as the base map layer
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

// Optional: You can add layers for water levels and rainfall data
var waterLevelLayer = L.layerGroup().addTo(map);
var rainfallLayer = L.layerGroup().addTo(map);

// Event listeners for toggling map layers
document.getElementById('waterLevelLayer').addEventListener('change', function(e) {
    if (e.target.checked) {
        // Add water levels data (Replace with actual layer data)
        L.marker([-13.9631, 33.7741]).addTo(waterLevelLayer).bindPopup('Water Level Point');
    } else {
        waterLevelLayer.clearLayers();
    }
});

document.getElementById('rainfallLayer').addEventListener('change', function(e) {
    if (e.target.checked) {
        // Add rainfall data (Replace with actual layer data)
        L.circle([-13.9631, 33.7741], {radius: 50000, color: 'blue'}).addTo(rainfallLayer).bindPopup('Rainfall Area');
    } else {
        rainfallLayer.clearLayers();
    }
});
