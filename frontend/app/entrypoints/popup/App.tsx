import { useState, useEffect } from 'react';
import { Camera, StopCircle, Eye, Activity, Volume2, Clock, PlayCircle } from 'lucide-react';
import './App.css';

interface Metrics {
    confidence: number;
    nervousness: number;
    speechRate: number;
    eyeContact: number;
    timestamp: number;
}

const MetricBar = ({
                       label,
                       value,
                       color,
                       bgColor,
                       suffix = '%'
                   }: {
    label: string;
    value: number;
    color: string;
    bgColor: string;
    suffix?: string;
}) => (
    <div className="relative">
        <div className="flex justify-between items-center mb-1.5">
            <span className="text-[13px] font-medium text-gray-600">{label}</span>
            <div className={`px-2 py-0.5 rounded-full ${bgColor} ${color} text-[11px] font-semibold tracking-wide`}>
                {value.toFixed(0)}{suffix}
            </div>
        </div>
        <div className="h-[6px] bg-gray-100 rounded-full overflow-hidden">
            <div
                className={`h-full ${color} transition-all duration-300 ease-out`}
                style={{ width: `${Math.min(value, 100)}%` }}
            />
        </div>
    </div>
);

const App = () => {
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [metrics, setMetrics] = useState<Metrics | null>(null);

    useEffect(() => {
        let interval: ReturnType<typeof setInterval>;
        if (isAnalyzing) {
            interval = setInterval(() => {
                setMetrics({
                    confidence: Math.random() * 30 + 70,
                    nervousness: Math.random() * 40 + 20,
                    speechRate: Math.random() * 30 + 140,
                    eyeContact: Math.random() * 30 + 70,
                    timestamp: Date.now()
                });
            }, 1000);
        }
        return () => clearInterval(interval);
    }, [isAnalyzing]);

    return (
        <div className="w-[800px] h-[600px] bg-[#FAFBFC]">
            <div className="grid grid-cols-2 gap-5 h-full p-5">
                {/* Left Column - Video Feed */}
                <div className="space-y-4">
                    {/* Header */}
                    <div className="flex items-center justify-between px-1">
                        <div className="flex items-center gap-3">
                            <div className="w-[18px] h-[18px] border-2 border-gray-300 rounded-sm"></div>
                            <h1 className="text-[15px] font-semibold text-gray-800 tracking-tight">Interview Simulation</h1>
                        </div>
                        <div className="flex items-center gap-2">
                            <div className={`w-1.5 h-1.5 rounded-full transition-colors duration-300 ${isAnalyzing ? 'bg-red-500 animate-pulse' : 'bg-gray-400'}`}></div>
                            <span className="text-[13px] text-gray-500 font-medium">{isAnalyzing ? 'Live' : 'Ready'}</span>
                        </div>
                    </div>

                    {/* Video Container */}
                    <div className="relative aspect-video bg-white rounded-xl border border-gray-200/80 shadow-sm overflow-hidden">
                        <div className="absolute inset-0 flex items-center justify-center text-gray-400 bg-[#F8FAFC]">
                            <Camera className="w-10 h-10 mr-2 opacity-40" />
                            <span className="text-[15px] text-gray-400/90">Waiting for video feed...</span>
                        </div>

                        {/* Overlay Metrics */}
                        {isAnalyzing && metrics && (
                            <div className="absolute top-3 left-3 right-3 space-y-2">
                                <div className="bg-black/40 backdrop-blur-md text-white p-2.5 rounded-lg">
                                    <div className="grid grid-cols-3 gap-3 text-[13px]">
                                        <div className="flex items-center gap-2">
                                            <Activity className="w-3.5 h-3.5" />
                                            <span className="font-medium">{metrics.confidence.toFixed(0)}%</span>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <Eye className="w-3.5 h-3.5" />
                                            <span className="font-medium">{metrics.eyeContact.toFixed(0)}%</span>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <Clock className="w-3.5 h-3.5" />
                                            <span className="font-medium">{metrics.speechRate.toFixed(0)} WPM</span>
                                        </div>
                                    </div>
                                </div>

                                {/* Audio Level */}
                                <div className="bg-black/40 backdrop-blur-md p-2.5 rounded-lg">
                                    <div className="flex items-center gap-2 text-white text-[13px] mb-1.5">
                                        <Volume2 className="w-3.5 h-3.5" />
                                        <span className="font-medium">Audio Level</span>
                                    </div>
                                    <div className="h-1.5 bg-white/10 rounded-full">
                                        <div
                                            className="h-full bg-white rounded-full transition-all duration-200"
                                            style={{ width: `${60 + Math.random() * 40}%` }}
                                        />
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                </div>

                {/* Right Column - Metrics */}
                <div className="space-y-4">
                    {/* Metrics Card */}
                    <div className="bg-white rounded-xl border border-gray-200/80 shadow-sm p-5">
                        <h2 className="text-[15px] font-semibold text-gray-800 tracking-tight mb-5">Real-time Metrics</h2>

                        <div className="space-y-5">
                            <MetricBar
                                label="Confidence"
                                value={metrics?.confidence ?? 0}
                                color="bg-blue-500"
                                bgColor="bg-blue-50"
                            />
                            <MetricBar
                                label="Nervousness"
                                value={metrics?.nervousness ?? 0}
                                color="bg-red-500"
                                bgColor="bg-red-50"
                            />
                            <MetricBar
                                label="Eye Contact"
                                value={metrics?.eyeContact ?? 0}
                                color="bg-emerald-500"
                                bgColor="bg-emerald-50"
                            />
                            <MetricBar
                                label="Speech Rate"
                                value={metrics?.speechRate ?? 0}
                                color="bg-violet-500"
                                bgColor="bg-violet-50"
                                suffix=" WPM"
                            />
                        </div>

                        <button
                            onClick={() => setIsAnalyzing(!isAnalyzing)}
                            className={`
                                w-full mt-5 py-3 rounded-lg flex items-center justify-center gap-2 
                                text-[13px] font-semibold tracking-wide text-white
                                transition-all duration-300 
                                ${isAnalyzing
                                ? 'bg-red-500 hover:bg-red-600 active:bg-red-700'
                                : 'bg-blue-500 hover:bg-blue-600 active:bg-blue-700'}
                            `}
                        >
                            {isAnalyzing ? (
                                <>
                                    <StopCircle className="w-4 h-4" />
                                    Stop Session
                                </>
                            ) : (
                                <>
                                    <PlayCircle className="w-4 h-4" />
                                    Start Session
                                </>
                            )}
                        </button>
                    </div>

                    {/* Trend Card */}
                    <div className="bg-white rounded-xl border border-gray-200/80 shadow-sm p-5">
                        <h2 className="text-[15px] font-semibold text-gray-800 tracking-tight mb-4">Performance Trend</h2>
                        <div className="relative h-[180px] border border-gray-100 rounded-lg p-4">
                            <div className="absolute inset-0 grid grid-cols-8 grid-rows-4 p-4">
                                {[...Array(32)].map((_, i) => (
                                    <div
                                        key={i}
                                        className="border-gray-100"
                                        style={{
                                            borderRight: (i + 1) % 8 !== 0 ? '1px dashed #f1f5f9' : 'none',
                                            borderBottom: i < 24 ? '1px dashed #f1f5f9' : 'none'
                                        }}
                                    />
                                ))}
                            </div>

                            {/* Y-axis labels */}
                            <div className="absolute -left-6 inset-y-0 flex flex-col justify-between text-[11px] text-gray-400 font-medium py-2">
                                {[100, 75, 50, 25, 0].map((value) => (
                                    <span key={value}>{value}</span>
                                ))}
                            </div>

                            {/* X-axis labels */}
                            <div className="absolute -bottom-6 inset-x-0 flex justify-between text-[11px] text-gray-400 font-medium px-2">
                                {[1, 3, 5, 7, 9].map((value) => (
                                    <span key={value}>{value}</span>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default App;