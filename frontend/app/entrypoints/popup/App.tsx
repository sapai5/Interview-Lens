import { useState, useEffect, useRef } from 'react';
import { Camera, StopCircle, Clock, PlayCircle } from 'lucide-react';
import './App.css';

interface Metrics {
    confidence: number;
    nervousness: number;
    speechRate: number;
    eyeContact: number;
    timestamp: number;
}

const MetricBar = ({ label, value, color, bgColor, suffix = '%' }: {
    label: string;
    value: number;
    color: string;
    bgColor: string;
    suffix?: string;
}) => (
    <div className="relative">
        <div className="flex justify-between items-center mb-1">
            <span className="text-[12px] font-medium text-gray-600">{label}</span>
            <div className={`px-1.5 py-0.5 rounded-full ${bgColor} ${color} text-[10px] font-semibold tracking-wide`}>
                {value.toFixed(0)}{suffix}
            </div>
        </div>
        <div className="h-[5px] bg-gray-100 rounded-full overflow-hidden">
            <div
                className={`h-full ${color} transition-all duration-300 ease-out`}
                style={{ width: `${Math.min(value, 100)}%` }}
            />
        </div>
    </div>
);

const formatTime = (seconds: number) => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds < 10 ? '0' : ''}${remainingSeconds}`;
};

const App = () => {
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [metrics, setMetrics] = useState<Metrics | null>(null);
    const [sessionNotes, setSessionNotes] = useState("");
    const [timeElapsed, setTimeElapsed] = useState(0);
    const [cameraError, setCameraError] = useState<string>("");
    const videoRef = useRef<HTMLVideoElement>(null);
    const [stream, setStream] = useState<MediaStream | null>(null);

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
                setTimeElapsed((prevTime) => prevTime + 1);
            }, 1000);
        }

        return () => {
            if (interval) clearInterval(interval);
        };
    }, [isAnalyzing]);

    const startCamera = async () => {
        try {
            const mediaStream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: { ideal: 640 },
                    height: { ideal: 480 },
                    facingMode: "user"
                }
            });

            if (videoRef.current) {
                videoRef.current.srcObject = mediaStream;
            }
            setStream(mediaStream);
            setCameraError("");
            return true;
        } catch (error) {
            console.error("Error accessing the camera:", error);
            setCameraError("Camera access denied. Please enable permissions in site settings.");
            return false;
        }
    };

    const stopCamera = () => {
        if (videoRef.current) {
            videoRef.current.srcObject = null;
        }
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
            setStream(null);
        }
    };

    const handleStartStop = async () => {
        if (!isAnalyzing) {
            setTimeElapsed(0);
            const cameraStarted = await startCamera();
            if (cameraStarted) {
                setIsAnalyzing(true);
            }
        } else {
            stopCamera();
            setIsAnalyzing(false);
        }
    };

    // Cleanup on component unmount
    useEffect(() => {
        return () => {
            stopCamera();
        };
    }, []);

    return (
        <div className="max-w-full h-screen flex justify-center items-center bg-[#FAFBFC]">
            <div className="w-full max-w-[750px] h-[93vh] bg-[#FAFBFC] rounded-lg shadow-lg overflow-hidden">
                <div className="grid grid-cols-2 grid-rows-2 gap-2 p-2 h-full">
                    {/* Top Left - Video Feed with Start/Stop Button */}
                    <div className="bg-white rounded-xl border border-gray-200/80 shadow-sm p-2 flex flex-col items-center justify-center relative">
                        <div className="flex items-center justify-between w-full">
                            <div className="flex items-center gap-2">
                                <div className="w-[16px] h-[16px] border-2 border-gray-300 rounded-sm"></div>
                                <h1 className="text-[14px] font-semibold text-gray-800 tracking-tight">InterviewLens</h1>
                                <span className="text-gray-800 text-[12px] font-medium flex items-center ml-6">
                                    <Clock className="w-4 h-4 mr-1" />
                                    {formatTime(timeElapsed)}
                                </span>
                            </div>
                            <div className="flex items-center gap-2">
                                <div className={`w-1.5 h-1.5 rounded-full transition-colors duration-300 ${isAnalyzing ? 'bg-red-500 animate-pulse' : 'bg-gray-400'}`}></div>
                                <span className="text-[12px] text-gray-500 font-medium">{isAnalyzing ? 'Live' : 'Ready'}</span>
                            </div>
                        </div>

                        {/* Video Container */}
                        <div className="relative flex-1 w-full bg-white rounded-lg border border-gray-200/80 shadow-sm overflow-hidden mt-2">
                            <video
                                ref={videoRef}
                                autoPlay
                                playsInline
                                muted
                                className="absolute inset-0 w-full h-full object-cover bg-[#F8FAFC]"
                            />
                            {(!isAnalyzing || cameraError) && (
                                <div className="absolute inset-0 flex flex-col items-center justify-center text-gray-400 bg-[#F8FAFC]">
                                    <Camera className="w-10 h-10 mr-2 opacity-40" />
                                    <span className="text-[14px] text-gray-400/90 text-center">
                                        {cameraError || "Waiting for video feed..."}
                                    </span>
                                </div>
                            )}
                        </div>

                        <button
                            onClick={handleStartStop}
                            className={`absolute top-2 right-2 px-2 py-1 rounded-md flex items-center gap-1 text-[11px] font-medium text-white 
                                ${isAnalyzing ? 'bg-red-500 hover:bg-red-600' : 'bg-blue-500 hover:bg-blue-600'}`}
                        >
                            {isAnalyzing ? (
                                <>
                                    <StopCircle className="w-3.5 h-3.5" />
                                    Stop
                                </>
                            ) : (
                                <>
                                    <PlayCircle className="w-3.5 h-3.5" />
                                    Start
                                </>
                            )}
                        </button>
                    </div>

                    {/* Rest of your components remain unchanged */}
                    {/* Top Right - Real-time Metrics */}
                    <div className="bg-white rounded-xl border border-gray-200/80 shadow-sm p-3 overflow-auto flex flex-col">
                        <h2 className="text-[14px] font-semibold text-gray-800 tracking-tight mb-4">Real-time Metrics</h2>
                        <div className="space-y-3">
                            <MetricBar label="Confidence" value={metrics?.confidence ?? 0} color="bg-blue-500" bgColor="bg-blue-50" />
                            <MetricBar label="Filler Words" value={metrics?.nervousness ?? 0} color="bg-red-500" bgColor="bg-red-50" />
                            <MetricBar label="Eye Contact" value={metrics?.eyeContact ?? 0} color="bg-emerald-500" bgColor="bg-emerald-50" />
                            <MetricBar label="Speech Rate" value={metrics?.speechRate ?? 0} color="bg-violet-500" bgColor="bg-violet-50" suffix=" WPM" />
                        </div>
                    </div>

                    {/* Bottom Left - Session Notes */}
                    <div className="bg-white rounded-xl border border-gray-200/80 shadow-sm p-3 flex flex-col">
                        <h2 className="text-[14px] font-semibold text-gray-800 tracking-tight mb-2">Session Notes</h2>
                        <textarea
                            className="text-[12px] text-gray-600 flex-1 resize-none rounded-md border border-gray-300 p-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                            placeholder="Type notes here..."
                            value={sessionNotes}
                            onChange={(e) => setSessionNotes(e.target.value)}
                        />
                    </div>

                    {/* Bottom Right - Performance Trend */}
                    <div className="bg-white rounded-xl border border-gray-200/80 shadow-sm p-3 overflow-hidden flex flex-col">
                        <h2 className="text-[14px] font-semibold text-gray-800 tracking-tight mb-2">Performance Trend</h2>
                        <div className="relative h-[85%] border border-gray-100 rounded-lg p-2 trend-grid">
                            <div className="absolute left-0 inset-y-0 flex flex-col justify-between text-[10px] text-gray-400 font-medium py-1 pl-1">
                                {[100, 75, 50, 25, "ㅤ"].map((value) => <span key={value}>{value}</span>)}
                            </div>
                            <div className="absolute bottom-0 inset-x-0 flex justify-between text-[10px] text-gray-400 font-medium px-1">
                                {[0, 3, 5, 7, 9].map((value) => <span key={value}>{value}</span>)}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default App;