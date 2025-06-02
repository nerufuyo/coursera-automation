// Background service worker
chrome.runtime.onInstalled.addListener(function() {
    console.log('Coursera Automation Extension installed');
    
    // Set default settings
    chrome.storage.sync.set({
        autoAnswerEnabled: false,
        currentSpeed: 1
    });
});

// Handle extension icon click
chrome.action.onClicked.addListener(function(tab) {
    if (tab.url.includes('coursera.org')) {
        // Open popup or inject content script
        chrome.scripting.executeScript({
            target: { tabId: tab.id },
            files: ['content.js']
        });
    }
});

// Listen for tab updates to re-inject content script
chrome.tabs.onUpdated.addListener(function(tabId, changeInfo, tab) {
    if (changeInfo.status === 'complete' && tab.url && tab.url.includes('coursera.org')) {
        chrome.scripting.executeScript({
            target: { tabId: tabId },
            files: ['content.js']
        }).catch(err => {
            // Script might already be injected
            console.log('Content script already exists or failed to inject:', err);
        });
    }
});
