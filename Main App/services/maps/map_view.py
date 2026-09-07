"""
Map Visualization Component: Google Maps + Leaflet / OpenStreetMap Fallback
===========================================================================
Renders an interactive responsive map in Streamlit via components.html:
- If GOOGLE_MAPS_API_KEY is present and provider is 'google': renders Google Maps JavaScript API.
- Otherwise: renders Leaflet.js with OpenStreetMap tiles (100% free, no billing required).
Displays start pin, finish/current pin, polyline route, auto-centering, and zoom controls.
"""
import os
import json
import streamlit as st
import streamlit.components.v1 as components
from typing import List, Tuple, Optional


def get_map_config():
    """Retrieve map provider settings and Google Maps API key."""
    google_key = os.environ.get("GOOGLE_MAPS_API_KEY", "")
    provider = os.environ.get("MAP_PROVIDER", "osm").lower()

    try:
        if not google_key and hasattr(st, "secrets") and "GOOGLE_MAPS_API_KEY" in st.secrets:
            google_key = st.secrets["GOOGLE_MAPS_API_KEY"]
        if hasattr(st, "secrets") and "MAP_PROVIDER" in st.secrets:
            provider = st.secrets["MAP_PROVIDER"].lower()
    except Exception:
        pass

    if google_key and provider == "google":
        return "google", google_key
    return "osm", ""


def render_map_component(
    route_coords: List[List[float]],
    current_pos: Optional[Tuple[float, float]] = None,
    height_px: int = 420,
    is_active: bool = False,
    provider_override: Optional[str] = None
):
    """
    Renders the live or historical map using Leaflet (OSM) or Google Maps.
    route_coords: list of [lat, lng] pairs.
    current_pos: (lat, lng) of current user position.
    """
    provider, google_key = get_map_config()
    if provider_override:
        provider = provider_override

    # Determine center
    if current_pos and current_pos[0] is not None and current_pos[1] is not None:
        center_lat, center_lng = current_pos[0], current_pos[1]
    elif route_coords and len(route_coords) > 0:
        center_lat, center_lng = route_coords[-1][0], route_coords[-1][1]
    else:
        # Default center (e.g. Hyderabad / default coordinates)
        center_lat, center_lng = 17.3850, 78.4867

    route_json = json.dumps(route_coords)
    curr_lat_val = current_pos[0] if current_pos else center_lat
    curr_lng_val = current_pos[1] if current_pos else center_lng

    if provider == "google" and google_key:
        html_code = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body, html {{ margin: 0; padding: 0; height: 100%; width: 100%; font-family: sans-serif; }}
                #map {{ height: {height_px}px; width: 100%; border-radius: 12px; }}
                .provider-badge {{
                    position: absolute; bottom: 10px; left: 10px; z-index: 999;
                    background: rgba(15, 23, 42, 0.85); color: #0ecfb5;
                    padding: 4px 8px; border-radius: 6px; font-size: 11px; font-weight: 600;
                    border: 1px solid rgba(14, 207, 181, 0.3);
                }}
            </style>
            <script src="https://maps.googleapis.com/maps/api/js?key={google_key}"></script>
        </head>
        <body>
            <div class="provider-badge">🗺️ Google Maps</div>
            <div id="map"></div>
            <script>
                const route = {route_json};
                const center = {{ lat: {curr_lat_val}, lng: {curr_lng_val} }};

                const map = new google.maps.Map(document.getElementById("map"), {{
                    zoom: 16,
                    center: center,
                    styles: [
                        {{ elementType: "geometry", stylers: [{{ color: "#171c28" }}] }},
                        {{ elementType: "labels.text.stroke", stylers: [{{ color: "#171c28" }}] }},
                        {{ elementType: "labels.text.fill", stylers: [{{ color: "#9ca3af" }}] }},
                        {{ featureType: "road", elementType: "geometry", stylers: [{{ color: "#2d3348" }}] }},
                        {{ featureType: "water", elementType: "geometry", stylers: [{{ color: "#0c1017" }}] }}
                    ],
                    disableDefaultUI: false,
                    zoomControl: true,
                    mapTypeControl: false,
                    streetViewControl: false
                }});

                if (route.length > 0) {{
                    const path = route.map(p => ({{ lat: p[0], lng: p[1] }}));
                    new google.maps.Polyline({{
                        path: path,
                        geodesic: true,
                        strokeColor: "#0ecfb5",
                        strokeOpacity: 0.9,
                        strokeWeight: 5,
                        map: map
                    }});

                    // Start Marker
                    new google.maps.Marker({{
                        position: path[0],
                        map: map,
                        title: "Start",
                        icon: "http://maps.google.com/mapfiles/ms/icons/green-dot.png"
                    }});

                    // Current / End Marker
                    new google.maps.Marker({{
                        position: path[path.length - 1],
                        map: map,
                        title: "Current Location",
                        icon: "http://maps.google.com/mapfiles/ms/icons/red-dot.png"
                    }});

                    const bounds = new google.maps.LatLngBounds();
                    path.forEach(pt => bounds.extend(pt));
                    map.fitBounds(bounds);
                }} else {{
                    new google.maps.Marker({{
                        position: center,
                        map: map,
                        title: "Current Location"
                    }});
                }}
            </script>
        </body>
        </html>
        """
    else:
        # OpenStreetMap + Leaflet (Free fallback)
        html_code = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
            <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
            <style>
                body, html {{ margin: 0; padding: 0; height: 100%; width: 100%; font-family: sans-serif; }}
                #map {{ height: {height_px}px; width: 100%; border-radius: 12px; }}
                .provider-badge {{
                    position: absolute; bottom: 8px; left: 8px; z-index: 1000;
                    background: rgba(17, 21, 32, 0.85); color: #0ecfb5;
                    padding: 4px 8px; border-radius: 6px; font-size: 11px; font-weight: 600;
                    border: 1px solid rgba(14, 207, 181, 0.3); pointer-events: none;
                }}
            </style>
        </head>
        <body>
            <div class="provider-badge">🗺️ OpenStreetMap (Free Mode)</div>
            <div id="map"></div>
            <script>
                const route = {route_json};
                const centerLat = {curr_lat_val};
                const centerLng = {curr_lng_val};

                const map = L.map('map').setView([centerLat, centerLng], 16);

                // CartoDB Dark Matter tiles (sleek modern fitness style)
                L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
                    attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
                    subdomains: 'abcd',
                    maxZoom: 19
                }}).addTo(map);

                if (route.length > 0) {{
                    const latLngs = route.map(pt => [pt[0], pt[1]]);
                    const polyline = L.polyline(latLngs, {{
                        color: '#0ecfb5',
                        weight: 5,
                        opacity: 0.9,
                        lineJoin: 'round'
                    }}).addTo(map);

                    // Start marker (green)
                    L.circleMarker(latLngs[0], {{
                        radius: 8,
                        fillColor: '#10b981',
                        color: '#ffffff',
                        weight: 2,
                        fillOpacity: 0.95
                    }}).addTo(map).bindPopup("🏁 Start Point");

                    // End / Current marker (red pulse)
                    L.circleMarker(latLngs[latLngs.length - 1], {{
                        radius: 9,
                        fillColor: '#ef4444',
                        color: '#ffffff',
                        weight: 2,
                        fillOpacity: 0.95
                    }}).addTo(map).bindPopup("📍 Current Location");

                    map.fitBounds(polyline.getBounds(), {{ padding: [30, 30] }});
                }} else {{
                    L.circleMarker([centerLat, centerLng], {{
                        radius: 8,
                        fillColor: '#3b82f6',
                        color: '#ffffff',
                        weight: 2,
                        fillOpacity: 0.9
                    }}).addTo(map).bindPopup("📍 Waiting for GPS movement...");
                }}
            </script>
        </body>
        </html>
        """

    components.html(html_code, height=height_px + 20)
