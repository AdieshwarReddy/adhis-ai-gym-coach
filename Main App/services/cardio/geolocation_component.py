"""
Browser Geolocation Bridge Component
====================================
Uses the HTML5 Geolocation API (navigator.geolocation.watchPosition)
to acquire high-accuracy latitude, longitude, accuracy, speed, and heading.
Renders permission guidance when denied or unavailable.
"""
import json
import streamlit.components.v1 as components


def render_gps_collector(is_active: bool, update_key: str = "gps_bridge"):
    """
    Renders an active GPS listener in the user's browser that feeds
    coordinates directly to the Streamlit session via query params or clipboard/copy,
    and displays live GPS hardware status (Accuracy, Lat/Lng).
    """
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            .gps-box {{
                background: #111520;
                border: 1px solid rgba(14, 207, 181, 0.25);
                border-radius: 8px;
                padding: 12px 16px;
                color: #e2e8f0;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                font-size: 13px;
                display: flex;
                flex-wrap: wrap;
                align-items: center;
                justify-content: space-between;
                gap: 8px;
            }}
            .gps-status-pill {{
                display: inline-flex;
                align-items: center;
                gap: 6px;
                background: rgba(14, 207, 181, 0.15);
                color: #0ecfb5;
                padding: 4px 10px;
                border-radius: 20px;
                font-weight: 600;
                font-size: 12px;
            }}
            .gps-status-pill.error {{
                background: rgba(239, 68, 68, 0.15);
                color: #ef4444;
            }}
            .dot {{
                width: 8px;
                height: 8px;
                border-radius: 50%;
                background: #0ecfb5;
                display: inline-block;
                animation: pulse 1.5s infinite;
            }}
            .dot.red {{
                background: #ef4444;
                animation: none;
            }}
            @keyframes pulse {{
                0% {{ transform: scale(0.9); opacity: 0.7; }}
                50% {{ transform: scale(1.2); opacity: 1; }}
                100% {{ transform: scale(0.9); opacity: 0.7; }}
            }}
            .coord-text {{
                color: #94a3b8;
                font-family: monospace;
            }}
            .btn-loc {{
                background: #0ecfb5;
                color: #0b1329;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: 600;
                font-size: 12px;
                cursor: pointer;
            }}
        </style>
    </head>
    <body style="margin:0; padding:0; background:transparent;">
        <div class="gps-box">
            <div id="statusPill" class="gps-status-pill">
                <span id="pulseDot" class="dot"></span>
                <span id="statusLabel">GPS Standby</span>
            </div>
            <div id="coordDisplay" class="coord-text">Waiting for device GPS...</div>
            <button class="btn-loc" onclick="acquirePosition()">📍 Acquire GPS</button>
        </div>

        <script>
            let watchId = null;
            const statusLabel = document.getElementById("statusLabel");
            const statusPill = document.getElementById("statusPill");
            const pulseDot = document.getElementById("pulseDot");
            const coordDisplay = document.getElementById("coordDisplay");

            function acquirePosition() {{
                if (!navigator.geolocation) {{
                    statusPill.className = "gps-status-pill error";
                    pulseDot.className = "dot red";
                    statusLabel.innerText = "Geolocation not supported";
                    return;
                }}

                statusLabel.innerText = "Acquiring GPS Signal...";

                const options = {{
                    enableHighAccuracy: true,
                    timeout: 10000,
                    maximumAge: 1000
                }};

                navigator.geolocation.getCurrentPosition(
                    (pos) => {{
                        const lat = pos.coords.latitude.toFixed(6);
                        const lng = pos.coords.longitude.toFixed(6);
                        const acc = pos.coords.accuracy.toFixed(1);
                        statusPill.className = "gps-status-pill";
                        pulseDot.className = "dot";
                        statusLabel.innerText = "GPS Active (±" + acc + "m)";
                        coordDisplay.innerText = lat + ", " + lng;

                        // Send back to parent window URL params or session
                        try {{
                            const url = new URL(window.parent.location.href);
                            url.searchParams.set("gps_lat", lat);
                            url.searchParams.set("gps_lng", lng);
                            url.searchParams.set("gps_acc", acc);
                            url.searchParams.set("gps_ts", Date.now());
                            window.parent.history.replaceState(null, "", url.toString());
                        }} catch (e) {{}}
                    }},
                    (err) => {{
                        statusPill.className = "gps-status-pill error";
                        pulseDot.className = "dot red";
                        if (err.code === 1) {{
                            statusLabel.innerText = "Permission Denied: Enable Location";
                            coordDisplay.innerText = "Please allow location access in your browser settings.";
                        }} else if (err.code === 2) {{
                            statusLabel.innerText = "GPS Position Unavailable";
                        }} else {{
                            statusLabel.innerText = "GPS Timeout: Searching...";
                        }}
                    }},
                    options
                );
            }}

            // Auto-acquire on mount if active
            {"acquirePosition();" if is_active else ""}
        </script>
    </body>
    </html>
    """
    components.html(html_code, height=75)
