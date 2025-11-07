import React, { useEffect, useState } from 'react';
import axios from 'axios';
import MapView from './components/MapView';
import Sidebar from './components/Sidebar';
import StatsPanel from './components/StatsPanel';

function App() {
  const [cities, setCities] = useState([]);
  const [selectedCity, setSelectedCity] = useState('');
  const [geoData, setGeoData] = useState(null);
  const [metric, setMetric] = useState('signal_strength');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Fetch available cities
  useEffect(() => {
    const fetchCities = async () => {
      try {
        const response = await axios.get('http://localhost:5001/api/cities');
        setCities(response.data);
        if (response.data.length > 0) {
          setSelectedCity(response.data[0]); // Set default city
        }
      } catch (err) {
        setError('Failed to load cities');
        console.error('Error fetching cities:', err);
        // Fallback to mock data if API is not available
        const mockCities = ['Bangalore', 'Delhi', 'Mumbai', 'Chennai', 'Hyderabad'];
        setCities(mockCities);
        setSelectedCity(mockCities[0]);
      }
    };

    fetchCities();
  }, []);

  // Fetch map data when city changes
  useEffect(() => {
    if (selectedCity) {
      const fetchCityData = async () => {
        setLoading(true);
        setError(null);
        try {
          const response = await axios.get(`http://localhost:5001/api/map/${selectedCity}`);
          setGeoData(response.data);
        } catch (err) {
          setError('Failed to load city data');
          console.error('Error fetching city data:', err);
          // Fallback to mock data
          setGeoData(generateMockGeoJSON(selectedCity));
        } finally {
          setLoading(false);
        }
      };

      fetchCityData();
    }
  }, [selectedCity]);

  const fetchMapData = async (city) => {
    setLoading(true);
    setError(null);
    
    try {
      // For now, we'll generate mock GeoJSON data
      // In a real implementation, this would call: axios.get(`/api/map/${city}`)
      const mockGeoData = generateMockGeoJSON(city);
      setGeoData(mockGeoData);
    } catch (err) {
      setError('Failed to load map data');
      console.error('Error fetching map data:', err);
    } finally {
      setLoading(false);
    }
  };

  // Generate mock GeoJSON data for demonstration
  const generateMockGeoJSON = (city) => {
    // This is mock data - in a real implementation, this would come from your backend
    const areas = [
      { name: 'Downtown', lat: 12.9716, lng: 77.5946 },
      { name: 'North', lat: 13.1, lng: 77.6 },
      { name: 'South', lat: 12.85, lng: 77.58 },
      { name: 'East', lat: 12.98, lng: 77.7 },
      { name: 'West', lat: 12.95, lng: 77.5 },
      { name: 'Central', lat: 12.97, lng: 77.6 }
    ];

    const features = areas.map((area, index) => {
      // Generate random signal data
      const signal_strength = Math.floor(Math.random() * 60) + 40; // 40-100%
      const avg_download = Math.floor(Math.random() * 40) + 10; // 10-50 Mbps
      const avg_upload = Math.floor(Math.random() * 20) + 5; // 5-25 Mbps
      const latency = Math.floor(Math.random() * 150) + 20; // 20-170 ms

      // Create a simple polygon around each area
      const offset = 0.05;
      return {
        type: 'Feature',
        properties: {
          name: area.name,
          signal_strength,
          avg_download,
          avg_upload,
          latency
        },
        geometry: {
          type: 'Polygon',
          coordinates: [[
            [area.lng - offset, area.lat - offset],
            [area.lng + offset, area.lat - offset],
            [area.lng + offset, area.lat + offset],
            [area.lng - offset, area.lat + offset],
            [area.lng - offset, area.lat - offset]
          ]]
        }
      };
    });

    return {
      type: 'FeatureCollection',
      features
    };
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <h1 className="text-2xl font-bold text-gray-900">
              Signal Coverage Dashboard
            </h1>
            <div className="text-sm text-gray-500">
              {selectedCity && `Viewing: ${selectedCity}`}
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-800">{error}</p>
          </div>
        )}

        <div className="flex flex-col lg:flex-row gap-6">
          {/* Sidebar */}
          <div className="lg:w-64 flex-shrink-0">
            <Sidebar
              cities={cities}
              selectedCity={selectedCity}
              setSelectedCity={setSelectedCity}
              metric={metric}
              setMetric={setMetric}
            />
          </div>

          {/* Main Content Area */}
          <div className="flex-1">
            {/* Map */}
            <div className="mb-6">
              {loading ? (
                <div className="h-96 bg-white rounded-xl shadow-lg flex items-center justify-center">
                  <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
                    <p className="text-gray-500">Loading coverage data...</p>
                  </div>
                </div>
              ) : geoData ? (
                <MapView geoData={geoData} metric={metric} />
              ) : (
                <div className="h-96 bg-white rounded-xl shadow-lg flex items-center justify-center">
                  <p className="text-gray-500">Select a city to view coverage data</p>
                </div>
              )}
            </div>

            {/* Stats Panel */}
            {geoData && <StatsPanel geoData={geoData} />}
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;