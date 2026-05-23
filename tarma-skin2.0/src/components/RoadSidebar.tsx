import { useState, useMemo } from 'react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Road } from '@/types/road';
import { Search, Plus, AlertCircle, CheckCircle, AlertTriangle } from 'lucide-react';
import { Badge } from '@/components/ui/badge';

interface RoadSidebarProps {
  roads: Road[];
  selectedRoad: Road | null;
  onRoadSelect: (road: Road) => void;
  onAddSampleRoad: () => void;
}

export function RoadSidebar({ roads, selectedRoad, onRoadSelect, onAddSampleRoad }: RoadSidebarProps) {
  const [searchQuery, setSearchQuery] = useState('');

  const filteredRoads = useMemo(() => {
    const query = searchQuery.toLowerCase();
    return roads.filter(road =>
      road.name.toLowerCase().includes(query) ||
      road.location.toLowerCase().includes(query)
    );
  }, [roads, searchQuery]);

  const getStatusIcon = (label: string) => {
    switch (label) {
      case 'Healthy':
        return <CheckCircle className="h-4 w-4 text-success" />;
      case 'Warning':
        return <AlertTriangle className="h-4 w-4 text-warning" />;
      case 'Critical':
        return <AlertCircle className="h-4 w-4 text-destructive" />;
      default:
        return null;
    }
  };

  const getStatusBadge = (label: string) => {
    const variants: Record<string, 'default' | 'destructive' | 'outline' | 'secondary'> = {
      'Healthy': 'default',
      'Warning': 'secondary',
      'Critical': 'destructive',
    };
    
    return (
      <Badge variant={variants[label] || 'outline'} className="ml-auto">
        {label}
      </Badge>
    );
  };

  return (
    <div className="flex flex-col h-full bg-card border-r">
      <div className="p-4 space-y-4">
        <h2 className="text-lg font-semibold">Road Monitoring</h2>
        
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            type="search"
            placeholder="Search roads..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
        </div>

        <Button onClick={onAddSampleRoad} variant="outline" className="w-full">
          <Plus className="mr-2 h-4 w-4" />
          Add Sample Road
        </Button>
      </div>

      <ScrollArea className="flex-1 px-4">
        <div className="space-y-2 pb-4">
          {filteredRoads.map(road => (
            <button
              key={road.id}
              onClick={() => onRoadSelect(road)}
              className={`w-full text-left p-3 rounded-lg border transition-all hover:bg-accent ${
                selectedRoad?.id === road.id
                  ? 'bg-accent border-primary'
                  : 'bg-card border-border'
              }`}
            >
              <div className="flex items-start gap-2">
                {getStatusIcon(road.ai_verdict.label)}
                <div className="flex-1 min-w-0">
                  <h3 className="font-medium truncate">{road.name}</h3>
                  <p className="text-sm text-muted-foreground truncate">
                    {road.location}
                  </p>
                  <div className="mt-2 flex items-center gap-2">
                    {getStatusBadge(road.ai_verdict.label)}
                    <span className="text-xs text-muted-foreground">
                      Health: {road.metrics.structural_health_score}%
                    </span>
                  </div>
                </div>
              </div>
            </button>
          ))}
        </div>
      </ScrollArea>
    </div>
  );
}
