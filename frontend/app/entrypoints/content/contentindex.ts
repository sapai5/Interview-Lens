// Types for our messages
interface AnalysisMessage {
    type: 'START_ANALYSIS' | 'STOP_ANALYSIS' | 'ANALYSIS_UPDATE';
    data?: any;
}

// Flags to track state
let isAnalyzing = false;
let ws: WebSocket | null = null;

// Listen for messages from the extension
chrome.runtime.onMessage.addListener((message: AnalysisMessage, _sender, sendResponse) => {
    switch (message.type) {
        case 'START_ANALYSIS':
            if (!isAnalyzing) {
                startAnalysis();
                sendResponse({ success: true });
            }
            break;

        case 'STOP_ANALYSIS':
            if (isAnalyzing) {
                stopAnalysis();
                sendResponse({ success: true });
            }
            break;
    }

    return true; // Keep message channel open for async response
});

// Start analysis and WebSocket connection
function startAnalysis() {
    // Connect to backend WebSocket
    ws = new WebSocket('wss://your-backend-url/analysis');

    ws.onopen = () => {
        isAnalyzing = true;
        console.log('Analysis connection established');
    };

    ws.onmessage = (event) => {
        try {
            const analysisData = JSON.parse(event.data);

            // Forward analysis data to extension
            chrome.runtime.sendMessage({
                type: 'ANALYSIS_UPDATE',
                data: analysisData
            });
        } catch (error) {
            console.error('Error processing analysis data:', error);
        }
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        stopAnalysis();
    };

    ws.onclose = () => {
        isAnalyzing = false;
        console.log('Analysis connection closed');
    };
}

// Stop analysis and clean up
function stopAnalysis() {
    if (ws) {
        ws.close();
        ws = null;
    }
    isAnalyzing = false;
}

export default {};