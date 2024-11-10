console.log('Background script loaded');

// Listen for messages from content script and forward to popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === 'ANALYSIS_UPDATE' && sender.tab) {
        // Forward analysis data to popup
        chrome.runtime.sendMessage(message).catch(() => {
            // Popup might be closed, ignore error
        });
    }
    return true;
});

// Handle extension installation
chrome.runtime.onInstalled.addListener(() => {
    console.log('Extension installed');
});

export default {};