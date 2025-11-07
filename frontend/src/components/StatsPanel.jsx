import React from 'react';

const StatsPanel = ({ geoData }) => {
  if (!geoData || !geoData.features) return null;

  const calculateStats = () => {
    const features = geoData.features;
    
    const signalStrengths = features.map(f => f.properties.signal_strength).filter(v => v != null);
    const downloadSpeeds = features.map(f => f.properties.avg_download).filter(v => v != null);
    const uploadSpeeds = features.map(f => f.properties.avg_upload).filter(v => v != null);
    const latencies = features.map(f => f.properties.latency).filter(v => v != null);

    const avg = (arr) => arr.reduce((a, b) => a + b, 0) / arr.length;
    const max = (arr) => Math.max(...arr);
    const min = (arr) => Math.min(...arr);

    return {
      signal: {
        avg: signalStrengths.length > 0 ? avg(signalStrengths).toFixed(1) : 0,
        max: signalStrengths.length > 0 ? max(signalStrengths) : 0,
        min: signalStrengths.length > 0 ? min(signalStrengths) : 0,
        count: signalStrengths.length
      },
      download: {
        avg: downloadSpeeds.length > 0 ? avg(downloadSpeeds).toFixed(1) : 0,
        max: downloadSpeeds.length > 0 ? max(downloadSpeeds) : 0,
        min: downloadSpeeds.length > 0 ? min(downloadSpeeds) : 0,
        count: downloadSpeeds.length
      },
      upload: {
        avg: uploadSpeeds.length > 0 ? avg(uploadSpeeds).toFixed(1) : 0,
        max: uploadSpeeds.length > 0 ? max(uploadSpeeds) : 0,
        min: uploadSpeeds.length > 0 ? min(uploadSpeeds) : 0,
        count: uploadSpeeds.length
      },
      latency: {
        avg: latencies.length > 0 ? avg(latencies).toFixed(1) : 0,
        max: latencies.length > 0 ? max(latencies) : 0,
        min: latencies.length > 0 ? min(latencies) : 0,
        count: latencies.length
      },
      totalAreas: features.length
    };
  };

  const stats = calculateStats();

  const StatCard = ({ title, value, unit, color = 'blue' }) => {
    const colorClasses = {
      blue: 'bg-blue-50 border-blue-200',
      green: 'bg-green-50 border-green-200',
      yellow: 'bg-yellow-50 border-yellow-200',
      red: 'bg-red-50 border-red-200'
    };

    return (
      <div className={`p-4 rounded-lg border ${colorClasses[color]}`}>
        <h3 className="text-sm font-medium text-gray-600">{title}</h3>
        <p className="text-2xl font-bold text-gray-900">
          {value} <span className="text-sm font-normal text-gray-500">{unit}</span>
        </p>
      </div>
    );
  };

  return (
    <div className="bg-white rounded-xl shadow-lg p-6 mt-4">
      <h2 className="text-lg font-bold text-gray-800 mb-4">Coverage Statistics</h2>
      
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <StatCard 
          title="Signal Strength" 
          value={stats.signal.avg} 
          unit="%" 
          color="green" 
        />
        <StatCard 
          title="Download Speed" 
          value={stats.download.avg} 
          unit="Mbps" 
          color="blue" 
        />
        <StatCard 
          title="Upload Speed" 
          value={stats.upload.avg} 
          unit="Mbps" 
          color="yellow" 
        />
        <StatCard 
          title="Latency" 
          value={stats.latency.avg} 
          unit="ms" 
          color="red" 
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-gray-50 rounded-lg p-4">
          <h3 className="text-sm font-medium text-gray-600 mb-2">Signal Strength Range</h3>
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-500">Min: {stats.signal.min}%</span>
            <span className="text-sm text-gray-500">Max: {stats.signal.max}%</span>
          </div>
        </div>
        
        <div className="bg-gray-50 rounded-lg p-4">
          <h3 className="text-sm font-medium text-gray-600 mb-2">Download Speed Range</h3>
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-500">Min: {stats.download.min} Mbps</span>
            <span className="text-sm text-gray-500">Max: {stats.download.max} Mbps</span>
          </div>
        </div>

        <div className="bg-gray-50 rounded-lg p-4">
          <h3 className="text-sm font-medium text-gray-600 mb-2">Upload Speed Range</h3>
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-500">Min: {stats.upload.min} Mbps</span>
            <span className="text-sm text-gray-500">Max: {stats.upload.max} Mbps</span>
          </div>
        </div>

        <div className="bg-gray-50 rounded-lg p-4">
          <h3 className="text-sm font-medium text-gray-600 mb-2">Latency Range</h3>
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-500">Min: {stats.latency.min} ms</span>
            <span className="text-sm text-gray-500">Max: {stats.latency.max} ms</span>
          </div>
        </div>
      </div>

      <div className="mt-4 text-center">
        <p className="text-sm text-gray-500">
          Data from {stats.totalAreas} coverage areas
        </p>
      </div>
    </div>
  );
};

export default StatsPanel;