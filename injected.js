// Injected script - runs in the page context for enhanced video control
(function() {
    'use strict';
    
    console.log('Coursera Automation injected script loaded');
    
    // Listen for messages from content script
    window.addEventListener('message', function(event) {
        if (event.data.type === 'COURSERA_AUTOMATION') {
            handleAction(event.data);
        }
    });
    
    function handleAction(data) {
        switch (data.action) {
            case 'setVideoSpeed':
                setAllVideoSpeeds(data.speed);
                break;
        }
    }
    
    function setAllVideoSpeeds(speed) {
        // Find all video elements
        const videos = document.querySelectorAll('video');
        
        videos.forEach(video => {
            try {
                // Override playbackRate property
                Object.defineProperty(video, 'playbackRate', {
                    set: function(value) {
                        this._playbackRate = speed;
                        this.defaultPlaybackRate = speed;
                        
                        // Trigger speed change event
                        const event = new Event('ratechange');
                        this.dispatchEvent(event);
                    },
                    get: function() {
                        return this._playbackRate || speed;
                    },
                    configurable: true
                });
                
                video.playbackRate = speed;
                video.defaultPlaybackRate = speed;
                
                console.log(`Video speed set to ${speed}x`);
            } catch (error) {
                console.error('Error setting video speed:', error);
            }
        });
        
        // Also override any rate limiting
        overrideRateLimiting();
    }
    
    function overrideRateLimiting() {
        // Override common rate limiting methods
        const originalCreateElement = document.createElement;
        document.createElement = function(tagName) {
            const element = originalCreateElement.call(this, tagName);
            
            if (tagName.toLowerCase() === 'video') {
                // Remove rate limitations on new video elements
                const originalSetAttribute = element.setAttribute;
                element.setAttribute = function(name, value) {
                    if (name === 'playbackrate' || name === 'data-max-rate') {
                        return; // Ignore rate limiting attributes
                    }
                    return originalSetAttribute.call(this, name, value);
                };
            }
            
            return element;
        };
        
        // Override HTMLVideoElement prototype
        if (window.HTMLVideoElement) {
            const originalPlaybackRateDescriptor = Object.getOwnPropertyDescriptor(
                HTMLVideoElement.prototype, 'playbackRate'
            );
            
            if (originalPlaybackRateDescriptor) {
                Object.defineProperty(HTMLVideoElement.prototype, 'playbackRate', {
                    set: function(value) {
                        // Allow any playback rate
                        originalPlaybackRateDescriptor.set.call(this, value);
                    },
                    get: originalPlaybackRateDescriptor.get,
                    configurable: true
                });
            }
        }
    }
    
    // Initialize on page load
    document.addEventListener('DOMContentLoaded', function() {
        overrideRateLimiting();
    });
    
    // Also run immediately in case DOM is already loaded
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', overrideRateLimiting);
    } else {
        overrideRateLimiting();
    }
    
})();
