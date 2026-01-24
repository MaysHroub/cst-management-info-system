import React from 'react';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';

// Fix for default marker icon
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
    iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
    iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

const MapDisplay = ({ coordinates, zoom = 15 }) => {
    if (!coordinates || coordinates.length !== 2) {
        return <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f1f5f9' }}>No location data</div>;
    }

    // GeoJSON is [lng, lat], Leaflet needs [lat, lng]
    const position = [coordinates[1], coordinates[0]];

    return (
        <MapContainer center={position} zoom={zoom} style={{ height: '100%', width: '100%' }}>
            <TileLayer
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                attribution='&copy; <a href="http://osm.org/copyright">OpenStreetMap</a>'
            />
            <Marker position={position}>
                <Popup>
                    <div style={{ minWidth: '150px' }}>
                        <div style={{ fontSize: '0.9rem', marginBottom: '4px' }}>
                            {position[0].toFixed(5)}, {position[1].toFixed(5)}
                        </div>
                        <a
                            href={`https://www.google.com/maps?q=${position[0]},${position[1]}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            style={{ fontSize: '0.9rem', color: '#2563eb' }}
                        >
                            Open in Google Maps ↗
                        </a>
                    </div>
                </Popup>
            </Marker>
        </MapContainer>
    );
};

export default MapDisplay;
