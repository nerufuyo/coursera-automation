// Content script - runs in the context of Coursera pages
console.log('Coursera Automation Extension loaded');

let autoAnswerEnabled = false;
let questionObserver = null;
let videoObserver = null;

// Enhanced status panel and monitoring
let statusPanel = null;
let questionCount = 0;
let answeredCount = 0;
let currentConfidence = 0;

// Initialize extension
initialize();

async function initialize() {
    // Load settings
    const result = await chrome.storage.sync.get(['autoAnswerEnabled']);
    autoAnswerEnabled = result.autoAnswerEnabled || false;
    
    // Inject our custom script
    injectScript();
    
    // Start monitoring for questions and videos
    if (autoAnswerEnabled) {
        startQuestionMonitoring();
    }
    
    startVideoMonitoring();
    
    // Create status panel
    createStatusPanel();
    updateStatusPanel();
    
    // Listen for messages from popup
    chrome.runtime.onMessage.addListener(handleMessage);
    
    // Update status panel periodically
    setInterval(updateStatusPanel, 1000);
}

function injectScript() {
    const script = document.createElement('script');
    script.src = chrome.runtime.getURL('injected.js');
    script.onload = function() {
        this.remove();
    };
    (document.head || document.documentElement).appendChild(script);
}

function handleMessage(request, sender, sendResponse) {
    switch (request.action) {
        case 'setVideoSpeed':
            setVideoSpeed(request.speed);
            break;
        case 'toggleAutoAnswer':
            autoAnswerEnabled = request.enabled;
            if (autoAnswerEnabled) {
                startQuestionMonitoring();
            } else {
                stopQuestionMonitoring();
            }
            break;
    }
    sendResponse({success: true});
}

function setVideoSpeed(speed) {
    // Send message to injected script
    window.postMessage({
        type: 'COURSERA_AUTOMATION',
        action: 'setVideoSpeed',
        speed: speed
    }, '*');
    
    // Also try direct manipulation as fallback
    const videos = document.querySelectorAll('video');
    videos.forEach(video => {
        try {
            video.playbackRate = speed;
            console.log(`Set video speed to ${speed}x`);
        } catch (error) {
            console.error('Error setting video speed:', error);
        }
    });
}

function startQuestionMonitoring() {
    console.log('Starting question monitoring...');
    
    // Stop existing observer
    stopQuestionMonitoring();
    
    // Create new observer
    questionObserver = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            mutation.addedNodes.forEach(function(node) {
                if (node.nodeType === Node.ELEMENT_NODE) {
                    checkForQuestions(node);
                }
            });
        });
    });
    
    // Start observing
    questionObserver.observe(document.body, {
        childList: true,
        subtree: true
    });
    
    // Check existing questions
    checkForQuestions(document.body);
}

function stopQuestionMonitoring() {
    if (questionObserver) {
        questionObserver.disconnect();
        questionObserver = null;
    }
}

function startVideoMonitoring() {
    videoObserver = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            mutation.addedNodes.forEach(function(node) {
                if (node.nodeType === Node.ELEMENT_NODE) {
                    const videos = node.querySelectorAll ? node.querySelectorAll('video') : [];
                    if (node.tagName === 'VIDEO') {
                        setupVideoControls(node);
                    }
                    videos.forEach(setupVideoControls);
                }
            });
        });
    });
    
    videoObserver.observe(document.body, {
        childList: true,
        subtree: true
    });
    
    // Setup existing videos
    document.querySelectorAll('video').forEach(setupVideoControls);
}

function setupVideoControls(video) {
    // Add event listeners for better speed control
    video.addEventListener('loadeddata', function() {
        // Restore speed setting
        chrome.storage.sync.get(['currentSpeed'], function(result) {
            if (result.currentSpeed) {
                video.playbackRate = result.currentSpeed;
            }
        });
    });
}

async function checkForQuestions(element) {
    if (!autoAnswerEnabled) return;
    
    // Look for different types of questions on Coursera
    const questionSelectors = [
        '[data-testid="quiz-question"]',
        '.rc-FormPartsQuestion',
        '.quiz-question',
        '.question-prompt',
        '[class*="question"]',
        '[class*="quiz"]'
    ];
    
    for (const selector of questionSelectors) {
        const questions = element.querySelectorAll ? element.querySelectorAll(selector) : [];
        if (element.matches && element.matches(selector)) {
            await processQuestion(element);
        }
        
        for (const question of questions) {
            await processQuestion(question);
        }
    }
}

async function processQuestion(questionElement) {
    // Avoid processing the same question multiple times
    if (questionElement.dataset.processed) return;
    questionElement.dataset.processed = 'true';
    
    // Increment question count
    questionCount++;
    updateStatusPanel();
    
    try {
        const questionData = extractQuestionData(questionElement);
        if (questionData) {
            console.log('Found question:', questionData);
            
            // Add visual feedback
            questionElement.classList.add('coursera-question-detected');
            
            const answer = await getAIAnswer(questionData);
            if (answer) {
                await selectAnswer(questionElement, answer);
                questionElement.classList.remove('coursera-question-detected');
                questionElement.classList.add('coursera-question-answered');
            }
        }
    } catch (error) {
        console.error('Error processing question:', error);
    }
}

function extractQuestionData(questionElement) {
    const questionText = questionElement.textContent || '';
    
    // Extract question prompt
    let prompt = '';
    const promptSelectors = [
        '.question-prompt',
        '.rc-FormPartsQuestion__contentCell',
        '[class*="prompt"]',
        'h3', 'h4', 'p'
    ];
    
    for (const selector of promptSelectors) {
        const promptElement = questionElement.querySelector(selector);
        if (promptElement && promptElement.textContent.trim()) {
            prompt = promptElement.textContent.trim();
            break;
        }
    }
    
    if (!prompt && questionText.length > 10) {
        prompt = questionText.substring(0, 500); // First 500 chars as fallback
    }
    
    // Extract options
    const options = [];
    const optionSelectors = [
        'input[type="radio"]',
        'input[type="checkbox"]',
        '.rc-Option',
        '[class*="option"]',
        'label'
    ];
    
    for (const selector of optionSelectors) {
        const optionElements = questionElement.querySelectorAll(selector);
        optionElements.forEach((option, index) => {
            const text = option.textContent || option.value || option.getAttribute('aria-label') || '';
            if (text.trim()) {
                options.push({
                    text: text.trim(),
                    element: option,
                    index: index
                });
            }
        });
        if (options.length > 0) break;
    }
    
    if (prompt && options.length > 0) {
        return {
            prompt: prompt,
            options: options,
            type: questionElement.querySelector('input[type="radio"]') ? 'multiple-choice' : 
                  questionElement.querySelector('input[type="checkbox"]') ? 'multiple-select' : 'unknown'
        };
    }
    
    return null;
}

async function getAIAnswer(questionData) {
    try {
        const response = await fetch('http://localhost:8000/answer', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                question: questionData.prompt,
                options: questionData.options.map(opt => opt.text),
                type: questionData.type
            })
        });
        
        if (response.ok) {
            const result = await response.json();
            // Update confidence for status panel
            currentConfidence = result.confidence || 0;
            console.log(`AI Answer: ${result.answer} (confidence: ${Math.round(currentConfidence * 100)}%)`);
            return result.answer;
        } else {
            console.error('Error getting AI answer:', response.statusText);
        }
    } catch (error) {
        console.error('Error connecting to AI service:', error);
        // Fallback to simple heuristics
        return getHeuristicAnswer(questionData);
    }
    
    return null;
}

function getHeuristicAnswer(questionData) {
    // Simple heuristic fallback - usually the longest option or one with specific keywords
    const options = questionData.options;
    
    // Look for obvious correct answers
    const positiveKeywords = ['correct', 'true', 'yes', 'always', 'all', 'both'];
    const negativeKeywords = ['incorrect', 'false', 'no', 'never', 'none'];
    
    for (const option of options) {
        const text = option.text.toLowerCase();
        if (positiveKeywords.some(keyword => text.includes(keyword))) {
            return option.text;
        }
    }
    
    // If no obvious answer, return the longest option (often more detailed/correct)
    const longestOption = options.reduce((prev, current) => 
        (current.text.length > prev.text.length) ? current : prev
    );
    
    return longestOption.text;
}

async function selectAnswer(questionElement, answerText) {
    // Find the option that matches the answer
    const options = questionElement.querySelectorAll('input[type="radio"], input[type="checkbox"], label');
    
    for (const option of options) {
        const optionText = option.textContent || option.value || option.getAttribute('aria-label') || '';
        
        if (optionText.trim().toLowerCase().includes(answerText.toLowerCase()) ||
            answerText.toLowerCase().includes(optionText.trim().toLowerCase())) {
            
            // Click the option
            try {
                option.click();
                console.log('Selected answer:', optionText);
                
                // Add visual feedback
                option.style.outline = '2px solid #22c55e';
                setTimeout(() => {
                    option.style.outline = '';
                }, 2000);
                
                // Update status panel
                answeredCount++;
                updateStatusPanel();
                
                break;
            } catch (error) {
                console.error('Error clicking option:', error);
            }
        }
    }
}

// Enhanced status panel functionality
function createStatusPanel() {
    if (statusPanel) return statusPanel;
    
    statusPanel = document.createElement('div');
    statusPanel.className = 'coursera-status-panel';
    statusPanel.innerHTML = `
        <div class="coursera-status-title">
            🤖 Coursera AI Assistant
        </div>
        <div class="coursera-status-item">
            <span>Auto Answer:</span>
            <span class="coursera-status-value" id="autoAnswerStatus">OFF</span>
        </div>
        <div class="coursera-status-item">
            <span>Questions Found:</span>
            <span class="coursera-status-value" id="questionCount">0</span>
        </div>
        <div class="coursera-status-item">
            <span>Answered:</span>
            <span class="coursera-status-value" id="answeredCount">0</span>
        </div>
        <div class="coursera-status-item">
            <span>Last Confidence:</span>
            <div>
                <span class="coursera-status-value" id="confidenceValue">--</span>
                <div class="coursera-confidence-bar">
                    <div class="coursera-confidence-fill" id="confidenceFill" style="width: 0%"></div>
                </div>
            </div>
        </div>
        <div class="coursera-status-item">
            <span>Video Speed:</span>
            <span class="coursera-status-value" id="videoSpeed">1x</span>
        </div>
    `;
    
    document.body.appendChild(statusPanel);
    
    // Add click to toggle
    statusPanel.addEventListener('click', function() {
        statusPanel.classList.toggle('hidden');
    });
    
    return statusPanel;
}

function updateStatusPanel() {
    if (!statusPanel) return;
    
    document.getElementById('autoAnswerStatus').textContent = autoAnswerEnabled ? 'ON' : 'OFF';
    document.getElementById('questionCount').textContent = questionCount;
    document.getElementById('answeredCount').textContent = answeredCount;
    
    if (currentConfidence > 0) {
        document.getElementById('confidenceValue').textContent = Math.round(currentConfidence * 100) + '%';
        document.getElementById('confidenceFill').style.width = (currentConfidence * 100) + '%';
    }
    
    // Update video speed
    const videos = document.querySelectorAll('video');
    if (videos.length > 0) {
        document.getElementById('videoSpeed').textContent = videos[0].playbackRate + 'x';
    }
}
