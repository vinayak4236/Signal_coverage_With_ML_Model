import React from 'react';
import { MapContainer, TileLayer, GeoJSON } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

const getColor = (value, metric) => {
  // Color scale based on metric type
  if (metric === 'signal_strength') {
    return value > 80 ? '#006400' : // Dark green
           value > 60 ? '#228B22' : // Forest green
           value > 40 ? '#32CD32' : // Lime green
           value > 20 ? '#FFD700' : // Gold
           '#FF4500'; // Orange red
  } else if (metric === 'avg_download' || metric === 'avg_upload') {
    return value > 50 ? '#006400' :
           value > 30 ? '#228B22' :
           value > 20 ? '#32CD32' :
           value > 10 ? '#FFD700' :
           '#FF4500';
  } else if (metric === 'latency') {
    return value < 20 ? '#006400' :
           value < 50 ? '#228B22' :
           value < 100 ? '#32CD32' :
           value < 200 ? '#FFD700' :
           '#FF4500';
  }
  return '#3388ff';
};

const style = (feature, metric) => {
  const value = feature.properties[metric];
  return {
    fillColor: getColor(value, metric),
    weight: 2,
    opacity: 1,
    color: 'white',
    dashArray: '3',
    fillOpacity: 0.7
  };
};

const MapView = ({ geoData, metric }) => {
  if (!geoData) return null;

  // Calculate bounds from GeoJSON data
  const getBounds = (geojson) => {
    let minLat = Infinity, maxLat = -Infinity;
    let minLng = Infinity, maxLng = -Infinity;

    const processCoordinates = (coords) => {
      if (Array.isArray(coords[0])) {
        coords.forEach(processCoordinates);
      } else {
        minLng = Math.min(minLng, coords[0]);
        maxLng = Math.max(maxLng, coords[0]);
        minLat = Math.min(minLat, coords[1]);
        maxLat = Math.max(maxLat, coords[1]);
      }
    };

    geojson.features.forEach(feature => {
      if (feature.geometry.type === 'Polygon') {
        processCoordinates(feature.geometry.coordinates);
      }
    });

    return [[minLat, minLng], [maxLat, maxLng]];
  };

  const bounds = getBounds(geoData);

  return (
    <div className="h-96 w-full rounded-lg overflow-hidden shadow-lg">
      <MapContainer
        bounds={bounds}
        style={{ height: '100%', width: '100%' }}
        zoomControl={true}
        scrollWheelZoom={true}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <GeoJSON
          data={geoData}
          style={(feature) => style(feature, metric)}
          onEachFeature={(feature, layer) => {
            const props = feature.properties;
            const popupContent = `
              <div class="p-2">
                <h3 class="font-bold text-lg mb-2">${props.name || 'Area'}</h3>
                <div class="space-y-1">
                  <p><span class="font-medium">Signal:</span> ${props.signal_strength || 'N/A'}%</p>
                  <p><span class="font-medium">Download:</span> ${props.avg_download || 'N/A'} Mbps</p>
                  <p><span class="font-medium">Upload:</span> ${props.avg_upload || 'N/A'} Mbps</p>
                  <p><span class="font-medium">Latency:</span> ${props.latency || 'N/A'} ms</p>
                </div>
              </div>
            `;
            layer.bindPopup(popupContent);
          }}
        />
      </MapContainer>
    </div>
  );
};

export default MapView;