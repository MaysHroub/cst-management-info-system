import React from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup, GeoJSON } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

const priorityColors = {
    critical: '#dc2626',
    high: '#ea580c',
    medium: '#ca8a04',
    low: '#059669'
};

const HeatMap = ({ geojson, zoneJson }) => {
    console.log('HeatMap render - geojson:', geojson);
    console.log('HeatMap render - zoneJson:', zoneJson);
    
    const features = geojson?.features || [];
    console.log('HeatMap render - features count:', features.length);

    // Calculate center from features or use default
    let center = [31.9038, 35.2050]; // Ramallah default
    if (features.length > 0) {
        const lats = features.map(f => f.geometry?.coordinates?.[1]).filter(Boolean);
        const lngs = features.map(f => f.geometry?.coordinates?.[0]).filter(Boolean);
        if (lats.length > 0 && lngs.length > 0) {
            center = [
                lats.reduce((a, b) => a + b, 0) / lats.length,
                lngs.reduce((a, b) => a + b, 0) / lngs.length
            ];
        }
    }

    const zoneStyle = (feature) => {
        const count = feature.properties.request_count || 0;
        // Thresholds: >10 = dark red, 6-10 = orange, 1-5 = yellow, 0 = gray
        let fillColor;
        if (count > 10) {
            fillColor = '#991b1b';  // Dark red
        } else if (count >= 6) {
            fillColor = '#f97316';  // Orange
        } else if (count >= 1) {
            fillColor = '#fbbf24';  // Yellow
        } else {
            fillColor = '#94a3b8';  // Gray
        }
        
        return {
            fillColor: fillColor,
            weight: 2,
            opacity: 1,
            color: 'white',
            dashArray: '3',
            fillOpacity: 0.3
        };
    };

    return (
        <MapContainer center={center} zoom={13} style={{ height: '100%', width: '100%' }}>
            <TileLayer
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                attribution='&copy; <a href="http://osm.org/copyright">OpenStreetMap</a>'
            />

            {/* Zone Choropleth Layer */}
            {zoneJson && (
                <GeoJSON
                    data={zoneJson}
                    style={zoneStyle}
                    onEachFeature={(feature, layer) => {
                        layer.bindPopup(`<strong>Zone: ${feature.properties.name}</strong><br/>Open Requests: ${feature.properties.request_count}`);
                    }}
                />
            )}

            {/* Request Points Layer */}
            {features.map((feature, idx) => {
                if (!feature?.geometry?.coordinates) {
                    console.warn('Skipping feature without valid geometry:', feature);
                    return null;
                }
                
                const [lng, lat] = feature.geometry.coordinates;
                if (!lat || !lng) {
                    console.warn('Skipping feature with invalid coordinates:', feature);
                    return null;
                }
                
                const props = feature.properties || {};
                const color = priorityColors[props.priority] || '#6b7280';
                const radius = 8 + (props.weight || 1) * 4;

                return (
                    <CircleMarker
                        key={idx}
                        center={[lat, lng]}
                        radius={radius}
                        fillColor={color}
                        fillOpacity={0.7}
                        color="#fff" // White border for contrast
                        weight={2}
                    >
                        <Popup>
                            <div style={{ minWidth: '150px' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                                    <strong>{props.request_id}</strong>
                                    <span className="badge" style={{ background: color, color: '#fff', fontSize: '0.6rem' }}>{props.priority}</span>
                                </div>
                                <p style={{ margin: '0', fontSize: '0.85rem' }}>{props.category}</p>
                                <p style={{ margin: '4px 0', fontSize: '0.8rem', color: '#666' }}>Status: {props.status}</p>
                                <p style={{ margin: '0', fontSize: '0.75rem', color: '#999' }}>Age: {props.age_hours?.toFixed(1)} hrs</p>
                                <hr style={{ margin: '8px 0', border: 'none', borderTop: '1px solid #eee' }} />
                                <a
                                    href={`https://www.google.com/maps?q=${lat},${lng}`}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    style={{ fontSize: '0.8rem', color: '#2563eb', textDecoration: 'none' }}
                                >
                                    Open in Google Maps ↗
                                </a>
                            </div>
                        </Popup>
                    </CircleMarker>
                );
            })}
        </MapContainer>
    );
};

export default HeatMap;
