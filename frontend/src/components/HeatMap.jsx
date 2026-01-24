import React from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

const priorityColors = {
    critical: '#dc2626',
    high: '#ea580c',
    medium: '#ca8a04',
    low: '#059669'
};

const HeatMap = ({ geojson }) => {
    const features = geojson?.features || [];

    // Calculate center from features or use default
    let center = [31.9038, 35.2050]; // Ramallah default
    if (features.length > 0) {
        const lats = features.map(f => f.geometry.coordinates[1]);
        const lngs = features.map(f => f.geometry.coordinates[0]);
        center = [
            lats.reduce((a, b) => a + b, 0) / lats.length,
            lngs.reduce((a, b) => a + b, 0) / lngs.length
        ];
    }

    return (
        <MapContainer center={center} zoom={13} style={{ height: '100%', width: '100%' }}>
            <TileLayer
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                attribution='&copy; <a href="http://osm.org/copyright">OpenStreetMap</a>'
            />
            {features.map((feature, idx) => {
                const [lng, lat] = feature.geometry.coordinates;
                const props = feature.properties;
                const color = priorityColors[props.priority] || '#6b7280';
                const radius = 8 + (props.weight || 1) * 4;

                return (
                    <CircleMarker
                        key={idx}
                        center={[lat, lng]}
                        radius={radius}
                        fillColor={color}
                        fillOpacity={0.6}
                        color={color}
                        weight={2}
                    >
                        <Popup>
                            <div>
                                <strong>{props.request_id}</strong>
                                <p>{props.category}</p>
                                <p>Priority: {props.priority}</p>
                                <p>Status: {props.status}</p>
                                <p>Age: {props.age_hours?.toFixed(1)} hours</p>
                                <hr style={{ margin: '4px 0', borderTop: '1px solid #eee' }} />
                                <div style={{ fontSize: '0.8rem', color: '#666', marginBottom: '4px' }}>
                                    {lat.toFixed(5)}, {lng.toFixed(5)}
                                </div>
                                <a
                                    href={`https://www.google.com/maps?q=${lat},${lng}`}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    style={{ fontSize: '0.8rem', color: '#2563eb' }}
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
