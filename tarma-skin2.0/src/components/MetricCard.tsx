import { Card, CardContent } from '@/components/ui/card';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface MetricCardProps {
  label: string;
  value: number;
  unit: string;
  trend?: 'up' | 'down' | 'neutral';
  sparklineData?: number[];
}

export function MetricCard({ label, value, unit, trend = 'neutral', sparklineData = [] }: MetricCardProps) {
  const getTrendIcon = () => {
    switch (trend) {
      case 'up':
        return <TrendingUp className="h-4 w-4 text-success" />;
      case 'down':
        return <TrendingDown className="h-4 w-4 text-destructive" />;
      default:
        return <Minus className="h-4 w-4 text-muted-foreground" />;
    }
  };

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-start justify-between mb-2">
          <span className="text-sm font-medium text-muted-foreground">{label}</span>
          {getTrendIcon()}
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-bold">{value.toFixed(2)}</span>
          <span className="text-sm text-muted-foreground">{unit}</span>
        </div>
        {sparklineData.length > 0 && (
          <div className="mt-2 h-8 flex items-end gap-0.5">
            {sparklineData.slice(-12).map((val, i) => {
              const max = Math.max(...sparklineData);
              const height = (val / max) * 100;
              return (
                <div
                  key={i}
                  className="flex-1 bg-primary/20 rounded-sm"
                  style={{ height: `${height}%` }}
                />
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
