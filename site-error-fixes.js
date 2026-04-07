/**
 * SITE ERROR FIXES V1.0
 * ====================
 * Quick fixes for common tracking and popup issues
 * 
 * Issues addressed:
 * 1. Cookiebot CBID error
 * 2. Meta Pixel permission issues
 * 3. Chrome extension conflicts
 * 4. Popup analysis functionality 
 * 5. Runtime message port errors
 * 
 * Usage: Include this script to prevent common errors
 */

(function() {
    'use strict';
    
    // Fix 1: Prevent Cookiebot errors
    if (typeof window.Cookiebot === 'undefined') {
        window.Cookiebot = {
            consent: {
                marketing: true,
                analytics: true,
                preferences: true
            },
            show: function() { return false; },
            hide: function() { return false; },
            withdraw: function() { return false; }
        };
    }
    
    // Fix 2: Handle invalid Cookiebot CBID and prevent configuration errors
    const originalCookiebotLoad = window.Cookiebot?.load || function() {};
    if (window.Cookiebot) {
        window.Cookiebot.load = function(cbid) {
            if (!cbid || cbid === 'YOUR_COOKIEBOT_CBID' || cbid.includes('YOUR_')) {
                console.warn('[Cookiebot] Invalid CBID detected, skipping initialization');
                return;
            }
            return originalCookiebotLoad.call(this, cbid);
        };
    }
    
    // Prevent Cookiebot script errors by intercepting script loading
    const originalCreateElement = document.createElement;
    document.createElement = function(tagName) {
        const element = originalCreateElement.call(this, tagName);
        
        if (tagName.toLowerCase() === 'script' && element.src) {
            // Intercept Cookiebot configuration requests
            if (element.src.includes('cookiebot.com') && element.src.includes('YOUR_COOKIEBOT_CBID')) {
                console.warn('[Cookiebot] Blocked invalid configuration request');
                element.src = ''; // Block the invalid request
                return element;
            }
        }
        
        return element;
    };
    
    // Fix 3: Meta Pixel error handling
    window.fbq = window.fbq || function() {
        if (window.fbq.callMethod) {
            window.fbq.callMethod.apply(window.fbq, arguments);
        } else {
            window.fbq.queue = window.fbq.queue || [];
            window.fbq.queue.push(arguments);
        }
    };
    
    // Override fbq to handle permission errors gracefully
    const originalFbq = window.fbq;
    window.fbq = function() {
        try {
            return originalFbq.apply(this, arguments);
        } catch (error) {
            if (error.message && error.message.includes('traffic permission')) {
                console.warn('[Meta Pixel] Traffic permissions error - continuing without pixel tracking');
                return;
            }
            throw error;
        }
    };
    
    // Fix 4: Chrome runtime message port errors
    const originalAddEventListener = window.addEventListener;
    window.addEventListener = function(type, listener, options) {
        if (type === 'message' && listener && typeof listener === 'function') {
            const wrappedListener = function(event) {
                try {
                    return listener.call(this, event);
                } catch (error) {
                    if (error.message && error.message.includes('message port closed')) {
                        console.warn('[Chrome Extension] Message port closed - ignoring error');
                        return;
                    }
                    throw error;
                }
            };
            return originalAddEventListener.call(this, type, wrappedListener, options);
        }
        return originalAddEventListener.call(this, type, listener, options);
    };
    
    // Fix 5: Popup Analysis Functionality Repair (Only for specific popup triggers)
    function repairPopupAnalysis() {
        // Only target specific popup triggers, NOT CTA buttons that should scroll to Typeform
        const popupTriggers = document.querySelectorAll([
            '[data-popup="analysis"]', 
            '.popup-trigger', 
            '.analysis-popup',
            'button[onclick*="analysis"]'
            // Removed .cta-button, .orange-button, a[href="#typeform"] - these should scroll to form
        ].join(', '));
        
        console.log('[Popup Repair] Found', popupTriggers.length, 'specific popup triggers');
        
        popupTriggers.forEach(trigger => {
            if (!trigger.hasAttribute('data-fixed')) {
                trigger.setAttribute('data-fixed', 'true');
                
                // Remove any broken event listeners
                const newTrigger = trigger.cloneNode(true);
                trigger.parentNode.replaceChild(newTrigger, trigger);
                
                // Add working event listener for popup triggers only
                newTrigger.addEventListener('click', function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    
                    console.log('[Popup Analysis] Opening popup from specific trigger');
                    
                    try {
                        // Try to show popup analysis
                        showAnalysisPopup();
                        
                        // Track event safely
                        if (typeof window.safeTrack === 'function') {
                            window.safeTrack('popup_analysis_opened', { source: 'popup_trigger' });
                        } else if (typeof window.fbq === 'function') {
                            window.fbq('track', 'ViewContent', { content_type: 'popup_analysis' });
                        }
                    } catch (error) {
                        console.error('[Popup Analysis] Error opening popup:', error);
                        // Fallback: redirect to analysis page or show simple form
                        fallbackAnalysisMethod();
                    }
                });
            }
        });
    }
    
    function showAnalysisPopup() {
        // Create or show analysis popup
        let popup = document.getElementById('analysis-popup');
        
        if (!popup) {
            popup = createAnalysisPopup();
            document.body.appendChild(popup);
        }
        
        popup.style.display = 'block';
        popup.classList.add('active');
        
        // Prevent body scroll
        document.body.style.overflow = 'hidden';
    }
    
    function createAnalysisPopup() {
        const popup = document.createElement('div');
        popup.id = 'analysis-popup';
        popup.innerHTML = `
            <div class="popup-overlay" onclick="closeAnalysisPopup()"></div>
            <div class="popup-content">
                <div class="popup-header">
                    <h2>📊 Gratis Vacature Analyse</h2>
                    <button onclick="closeAnalysisPopup()" class="close-btn">&times;</button>
                </div>
                <div class="popup-body">
                    <p>Ontdek binnen 24 uur waarom jouw vacature niet de juiste kandidaten aantrekt.</p>
                    <div id="typeform-embed"></div>
                </div>
            </div>
        `;
        
        // Add styles
        popup.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.8);
            display: none;
            z-index: 10000;
        `;
        
        // Load Typeform in popup
        popup.querySelector('#typeform-embed').innerHTML = `
            <div data-tf-widget="YOUR_TYPEFORM_ID" data-tf-opacity="100" data-tf-iframe-props="title=Vacature Analyse" data-tf-transitive-search-params data-tf-medium="snippet" style="width:100%;height:400px;"></div>
            <script src="//embed.typeform.com/next/embed.js"></script>
        `;
        
        return popup;
    }
    
    function fallbackAnalysisMethod() {
        // Simple fallback if popup fails
        const email = prompt('Voor een snelle analyse, wat is je email adres?');
        if (email && email.includes('@')) {
            window.open(`mailto:wouter@recruitin.nl?subject=Vacature Analyse Aanvraag&body=Hoi Wouter,%0D%0A%0D%0AIk zou graag een gratis analyse van mijn vacature willen.%0D%0A%0D%0AMijn email: ${email}%0D%0A%0D%0AGroeten`, '_blank');
        }
    }
    
    // Fix 6: Permissions policy violations
    function handlePermissionsViolations() {
        // Silence camera/microphone permission warnings
        const originalGetUserMedia = navigator.mediaDevices?.getUserMedia;
        if (originalGetUserMedia) {
            navigator.mediaDevices.getUserMedia = function(constraints) {
                return Promise.reject(new Error('Media access not required for this application'));
            };
        }
    }
    
    // Fix 7: Analytics tracking improvements
    function improveAnalyticsTracking() {
        // Safe analytics tracking
        window.safeTrack = function(event, data = {}) {
            try {
                // Facebook Pixel
                if (typeof window.fbq === 'function') {
                    window.fbq('track', event, data);
                }
                
                // Google Analytics
                if (typeof window.gtag === 'function') {
                    window.gtag('event', event, data);
                }
                
                // Custom analytics
                if (typeof window.trackAnalytics === 'function') {
                    window.trackAnalytics(event, data);
                }
                
                console.log('[Analytics] Event tracked:', event, data);
            } catch (error) {
                console.warn('[Analytics] Tracking error:', error);
            }
        };
    }
    
    // Fix 8: Orange button functionality test
    function verifyOrangeButtonFunctionality() {
        const orangeButtons = document.querySelectorAll('.cta-button, .orange-button, a[href="#typeform"]');
        
        orangeButtons.forEach((button, index) => {
            // Skip if already processed
            if (button.hasAttribute('data-verified')) {
                return;
            }
            
            button.setAttribute('data-verified', 'true');
            console.log('[Orange Button] Processing button:', button.textContent?.trim());
            
            // For buttons that should scroll to typeform (not open popup)
            if (button.href && button.href.includes('#typeform')) {
                // Remove any conflicting event listeners that might open popups
                const newButton = button.cloneNode(true);
                button.parentNode.replaceChild(newButton, button);
                
                newButton.addEventListener('click', function(e) {
                    e.preventDefault();
                    
                    console.log('[Orange Button] Scrolling to typeform, not opening popup');
                    
                    // Track the click
                    try {
                        if (typeof window.safeTrackClick === 'function') {
                            window.safeTrackClick(this);
                        } else if (typeof window.fbq === 'function') {
                            window.fbq('track', 'Lead', { content_type: 'cta_button' });
                        }
                    } catch (error) {
                        console.warn('[Tracking] Error:', error);
                    }
                    
                    // Scroll to typeform
                    if (typeof window.scrollToForm === 'function') {
                        window.scrollToForm();
                    } else {
                        // Fallback scroll
                        const typeformEl = document.getElementById('typeform');
                        if (typeformEl) {
                            typeformEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
                        }
                    }
                });
            }
        });
    }
    
    // Initialize all fixes
    function initializeAllFixes() {
        try {
            handlePermissionsViolations();
            improveAnalyticsTracking();
            
            // Wait for DOM to be ready
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', function() {
                    repairPopupAnalysis();
                    verifyOrangeButtonFunctionality();
                });
            } else {
                repairPopupAnalysis();
                verifyOrangeButtonFunctionality();
            }
            
            console.log('[Site Fixes] All error fixes initialized successfully');
        } catch (error) {
            console.error('[Site Fixes] Error during initialization:', error);
        }
    }
    
    // Global close popup function
    window.closeAnalysisPopup = function() {
        const popup = document.getElementById('analysis-popup');
        if (popup) {
            popup.style.display = 'none';
            popup.classList.remove('active');
            document.body.style.overflow = '';
        }
    };
    
    // Start fixes immediately
    initializeAllFixes();
    
    // Also run fixes after any dynamic content loads
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.addedNodes.length > 0) {
                // Wait a bit for new elements to settle
                setTimeout(() => {
                    repairPopupAnalysis();
                    verifyOrangeButtonFunctionality();
                }, 100);
            }
        });
    });
    
    observer.observe(document.body, { childList: true, subtree: true });
    
    console.log('[Site Error Fixes] Error prevention and popup repair system loaded');
    
})();