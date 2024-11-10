import React, { useEffect, useState } from 'react';
import SpeechVisualizer from './SpeechVisualizer';
import './App.css';

interface Metrics {
    speechRate: number;
    fillerPercentage: number;
}

const App = () => {
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [metrics, setMetrics] = useState<Metrics>({ speechRate: 0, fillerPercentage: 0 });

    const toggleAnalysis = () => {
        if (isAnalyzing) {
            chrome.runtime.sendMessage({ type: 'STOP_ANALYSIS' });
            setIsAnalyzing(false);
        } else {
            chrome.runtime.sendMessage({ type: 'START_ANALYSIS' });
            setIsAnalyzing(true);
        }
    };

    useEffect(() => {
        if (isAnalyzing) {
            const intervalId = setInterval(() => {
                chrome.runtime.sendMessage({ type: 'GET_METRICS' }, (response) => {
                    if (response) {
                        setMetrics(response);
                    }
                });
            }, 1000);

            return () => clearInterval(intervalId);
        }
    }, [isAnalyzing]);

    return (
        <div className="app">
            <button onClick={toggleAnalysis} className={`toggle-btn ${isAnalyzing ? 'stop' : 'start'}`}>
                {isAnalyzing ? 'Stop Analysis' : 'Start Analysis'}
            </button>
            <SpeechVisualizer metrics={metrics} />
        </div>
    );
};

export default App;
