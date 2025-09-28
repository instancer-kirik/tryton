// Custom configuration for SAO to connect to Railway Tryton server
(function() {
    'use strict';

    // Configuration for Railway deployment
    var config = {
        // Railway Tryton server URL
        server: 'https://tryton-app-production.up.railway.app',
        // Database name
        database: 'divvyqueue_prod',
        // Application title
        title: 'DivvyQueue Tryton ERP',
        // Enable development mode for better debugging
        dev: false,
        // Session timeout (in seconds)
        session_timeout: 3600,
        // Language
        language: 'en'
    };

    // Apply configuration when Sao is loaded
    if (typeof Sao !== 'undefined') {
        // Set server URL and database
        Sao.server = config.server;
        Sao.database = config.database;

        // Set application title
        if (config.title) {
            document.title = config.title;
            var titleElement = document.getElementById('title');
            if (titleElement) {
                titleElement.textContent = config.title;
            }
        }

        // Configure session timeout
        if (config.session_timeout) {
            Sao.Session.timeout = config.session_timeout * 1000; // Convert to milliseconds
        }

        // Set language if specified
        if (config.language) {
            Sao.i18n.setlang(config.language);
        }

        // Development mode configurations
        if (config.dev) {
            // Enable more verbose logging
            console.log('SAO Development Mode Enabled');
            console.log('Server:', config.server);
            console.log('Database:', config.database);

            // Add connection status indicator
            Sao.Session.current_session.then(function(session) {
                console.log('Connected to Tryton server');
                console.log('Session ID:', session ? session.session_id : 'No session');
            }).catch(function(error) {
                console.error('Failed to connect to Tryton server:', error);
            });
        }

        // Custom styling for DivvyQueue branding
        var customCSS = `
            .navbar-brand {
                font-weight: bold;
                color: #2563eb !important;
            }

            .navbar-inverse {
                background-color: #1e293b;
                border-color: #334155;
            }

            .navbar-inverse .navbar-nav > li > a {
                color: #cbd5e1;
            }

            .navbar-inverse .navbar-nav > li > a:hover {
                color: #f1f5f9;
                background-color: #334155;
            }

            /* Connection status indicator */
            .connection-status {
                position: fixed;
                top: 10px;
                right: 10px;
                padding: 5px 10px;
                border-radius: 4px;
                font-size: 12px;
                z-index: 9999;
            }

            .connection-status.connected {
                background-color: #10b981;
                color: white;
            }

            .connection-status.disconnected {
                background-color: #ef4444;
                color: white;
            }
        `;

        // Inject custom CSS
        var style = document.createElement('style');
        style.type = 'text/css';
        if (style.styleSheet) {
            style.styleSheet.cssText = customCSS;
        } else {
            style.appendChild(document.createTextNode(customCSS));
        }
        document.getElementsByTagName('head')[0].appendChild(style);

        // Add connection status indicator
        function updateConnectionStatus(connected) {
            var indicator = document.getElementById('connection-status');
            if (!indicator) {
                indicator = document.createElement('div');
                indicator.id = 'connection-status';
                indicator.className = 'connection-status';
                document.body.appendChild(indicator);
            }

            if (connected) {
                indicator.className = 'connection-status connected';
                indicator.textContent = '● Connected to ' + config.database;
            } else {
                indicator.className = 'connection-status disconnected';
                indicator.textContent = '● Disconnected';
            }
        }

        // Monitor connection status
        if (Sao.rpc) {
            var originalRpc = Sao.rpc;
            Sao.rpc = function() {
                return originalRpc.apply(this, arguments).then(function(result) {
                    updateConnectionStatus(true);
                    return result;
                }).catch(function(error) {
                    updateConnectionStatus(false);
                    throw error;
                });
            };
        }

        console.log('SAO Custom Configuration Loaded');
        console.log('Configured for:', config.server + '/' + config.database);

    } else {
        // Sao not loaded yet, wait for it
        console.log('Waiting for Sao to load...');
        setTimeout(arguments.callee, 100);
    }
})();

// Additional utility functions for DivvyQueue integration

// Function to check server health
function checkServerHealth() {
    fetch('https://tryton-app-production.up.railway.app/health')
        .then(response => response.json())
        .then(data => {
            console.log('Server Health:', data);
            return data.status === 'healthy';
        })
        .catch(error => {
            console.error('Health check failed:', error);
            return false;
        });
}

// Auto-refresh session before it expires
function setupSessionRefresh() {
    if (typeof Sao !== 'undefined' && Sao.Session) {
        setInterval(function() {
            if (Sao.Session.current_session && Sao.Session.current_session.session_id) {
                // Make a simple call to keep the session alive
                Sao.rpc({
                    'method': 'common.context',
                    'params': []
                }, Sao.Session.current_session).catch(function(error) {
                    console.warn('Session refresh failed:', error);
                });
            }
        }, 300000); // Refresh every 5 minutes
    }
}

// Initialize session refresh when page loads
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(setupSessionRefresh, 2000); // Wait 2 seconds for SAO to initialize
});
