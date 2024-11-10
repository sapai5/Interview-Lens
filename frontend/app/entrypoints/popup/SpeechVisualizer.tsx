import React, { useEffect, useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';

interface MetricsData {
  timestamp: number;
  speechRate: number;
  fillerPercentage: number;
}

interface SpeechVisualizerProps {
  metrics: { speechRate: number; fillerPercentage: number };
}

const SpeechVisualizer: React.FC<SpeechVisualizerProps> = ({ metrics }) => {
  const [metricsData, setMetricsData] = useState<MetricsData[]>([]);

  useEffect(() => {
    const timestamp = Date.now() / 1000;
    const newMetricData = {
      timestamp,
      speechRate: metrics.speechRate,
      fillerPercentage: metrics.fillerPercentage,
    };

    // Update metrics data with new values, keeping a limited number of entries
    setMetricsData((prevData) => [...prevData, newMetricData].slice(-30));
  }, [metrics]);

  return (
    <div className="p-4">
      <div className="mb-4">
        <div className="text-lg">
          Current Speech Rate: {metrics.speechRate.toFixed(2)} words/min
        </div>
        <div className="text-lg">
          Current Filler Word Usage: {metrics.fillerPercentage.toFixed(2)}%
        </div>
      </div>

      <div className="grid gap-4">
        {/* Speech Rate Chart */}
        <LineChart width={800} height={300} data={metricsData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="timestamp" label={{ value: 'Time (s)', position: 'insideBottom' }} />
          <YAxis label={{ value: 'Speech Rate (words/min)', angle: -90, position: 'insideLeft' }} />
          <Tooltip />
          <Legend />
          <Line type="monotone" dataKey="speechRate" stroke="#8884d8" />
        </LineChart>

        {/* Filler Word Percentage Chart */}
        <LineChart width={800} height={300} data={metricsData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="timestamp" label={{ value: 'Time (s)', position: 'insideBottom' }} />
          <YAxis label={{ value: 'Filler Word %', angle: -90, position: 'insideLeft' }} />
          <Tooltip />
          <Legend />
          <Line type="monotone" dataKey="fillerPercentage" stroke="#82ca9d" />
        </LineChart>
      </div>
    </div>
  );
};

export default SpeechVisualizer;
