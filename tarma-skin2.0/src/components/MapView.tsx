import { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { Road } from '@/types/road';

interface MapViewProps {
  roads: Road[];
  selectedRoad: Road | null;
  onRoadSelect: (road: Road) => void;
}

export function MapView({ roads, selectedRoad, onRoadSelect }: MapViewProps) {
  const mapRef = useRef<L.Map | null>(null);
  const markersRef = useRef<Map<string, L.Polyline>>(new Map());

  useEffect(() => {
    if (!mapRef.current) {
      // Initialize map centered on Bangalore
      const map = L.map('map', {
        center: [12.9716, 77.5946],
        zoom: 12,
      });

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
      }).addTo(map);

      mapRef.current = map;
    }

    // Clear existing markers
    markersRef.current.forEach(marker => marker.remove());
    markersRef.current.clear();

    // Add road polylines
    roads.forEach(road => {
      const getColor = () => {
        switch (road.ai_verdict.label) {
          case 'Healthy': return '#10b981';
          case 'Warning': return '#f59e0b';
          case 'Critical': return '#ef4444';
          default: return '#3b82f6';
        }
      };

      const polyline = L.polyline(road.coords as [number, number][], {
        color: getColor(),
        weight: selectedRoad?.id === road.id ? 6 : 4,
        opacity: selectedRoad?.id === road.id ? 1 : 0.7,
      }).addTo(mapRef.current!);

      // Add tooltip
      polyline.bindTooltip(
        `<div class="font-semibold">${road.name}</div>
         <div class="text-sm">Status: ${road.ai_verdict.label}</div>
         <div class="text-xs">Health: ${road.metrics.structural_health_score}%</div>`,
        { permanent: false, direction: 'top' }
      );

      // Add click handler
      polyline.on('click', () => {
        onRoadSelect(road);
      });

      // Add mouseover cursor change
      polyline.on('mouseover', function() {
        this.setStyle({ weight: 6 });
      });

      polyline.on('mouseout', function() {
        if (selectedRoad?.id !== road.id) {
          this.setStyle({ weight: 4 });
        }
      });

      markersRef.current.set(road.id, polyline);
    });

    // Fit bounds to show all roads
    if (roads.length > 0) {
      const bounds = L.latLngBounds(
        roads.flatMap(road => road.coords as [number, number][])
      );
      mapRef.current?.fitBounds(bounds, { padding: [50, 50] });
    }

    return () => {
      // Cleanup on unmount
      if (mapRef.current) {
        markersRef.current.forEach(marker => marker.remove());
        markersRef.current.clear();
      }
    };
  }, [roads, selectedRoad, onRoadSelect]);

  return (
    <div 
      id="map" 
      className="w-full h-full rounded-lg shadow-lg"
      style={{ minHeight: '600px' }}
    />
  );
}
