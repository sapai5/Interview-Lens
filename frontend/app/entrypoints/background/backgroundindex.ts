import SpeechMetrics from './path/to/SpeechMetrics';
import TranscriptionHandler from './path/to/TranscriptionHandler';
import AudioCapture from './path/to/AudioCapture';

const transcriptionHandler = new TranscriptionHandler();
const audioCapture = new AudioCapture();

// Start capture when requested
chrome.runtime.onMessage.addListener(async (message, sender, sendResponse) => {
    if (message.type === 'START_ANALYSIS') {
        await audioCapture.initialize();
        audioCapture.startCapture((audioData) => {
            // Process audio data and send to transcription
            transcriptionHandler.handleTranscriptEvent(audioData);
        });
        sendResponse({ status: 'Analysis started' });
    } else if (message.type === 'STOP_ANALYSIS') {
        audioCapture.stop();
        sendResponse({ status: 'Analysis stopped' });
    } else if (message.type === 'GET_METRICS') {
        const metrics = transcriptionHandler.getMetrics();
        sendResponse(metrics);
    }
    return true;
});

console.log('Background script loaded');
