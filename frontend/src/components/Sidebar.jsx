import React from 'react';

const Sidebar = ({ cities, selectedCity, setSelectedCity, metric, setMetric }) => {
  const metrics = [
    { key: 'signal_strength', label: 'Signal Strength', unit: '%' },
    { key: 'avg_download', label: 'Download Speed', unit: 'Mbps' },
    { key: 'avg_upload', label: 'Upload Speed', unit: 'Mbps' },
    { key: 'latency', label: 'Latency', unit: 'ms' }
  ];

  return (
    <div className="w-64 bg-white rounded-xl shadow-lg p-6">
      <h2 className="text-xl font-bold text-gray-800 mb-6">Signal Coverage</h2>
      
      {/* City Selection */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Select City
        </label>
        <select
          className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          value={selectedCity}
          onChange={(e) => setSelectedCity(e.target.value)}
        >
          {cities.map((city) => (
            <option key={city} value={city}>
              {city}
            </option>
          ))}
        </select>
      </div>

      {/* Metric Selection */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-3">
          Data Type
        </label>
        <div className="space-y-2">
          {metrics.map((metricOption) => (
            <label key={metricOption.key} className="flex items-center">
              <input
                type="radio"
                name="metric"
                value={metricOption.key}
                checked={metric === metricOption.key}
                onChange={(e) => setMetric(e.target.value)}
                className="mr-3 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700">
                {metricOption.label} ({metricOption.unit})
              </span>
            </label>
          ))}
        </div>
      </div>

      {/* Legend */}
      <div className="mt-8">
        <h3 className="text-sm font-medium text-gray-700 mb-3">Coverage Legend</h3>
        <div className="space-y-2 text-xs">
          <div className="flex items-center">
            <div className="w-4 h-4 bg-green-700 rounded mr-2"></div>
            <span>Excellent</span>
          </div>
          <div className="flex items-center">
            <div className="w-4 h-4 bg-green-500 rounded mr-2"></div>
            <span>Good</span>
          </div>
          <div className="flex items-center">
            <div className="w-4 h-4 bg-lime-500 rounded mr-2"></div>
            <span>Fair</span>
          </div>
          <div className="flex items-center">
            <div className="w-4 h-4 bg-yellow-500 rounded mr-2"></div>
            <span>Poor</span>
          </div>
          <div className="flex items-center">
            <div className="w-4 h-4 bg-red-500 rounded mr-2"></div>
            <span>Very Poor</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Sidebar;