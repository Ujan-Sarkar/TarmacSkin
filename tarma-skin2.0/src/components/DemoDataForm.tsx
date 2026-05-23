import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Road } from '@/types/road';
import { Edit } from 'lucide-react';

interface DemoDataFormProps {
  currentMetrics: Road['metrics'];
  onMetricsChange: (newMetrics: Road['metrics']) => void;
}

export function DemoDataForm({ currentMetrics, onMetricsChange }: DemoDataFormProps) {

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    
    const newMetrics: Road['metrics'] = {
      ...currentMetrics,
      [name]: Number(value),
    };
    
    onMetricsChange(newMetrics);
  };

  return (
    <Card className="border-l-4 border-l-primary">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Edit className="h-5 w-5" />
          Manual Data Entry (DEMO)
        </CardTitle>
        <CardDescription>
          Adjust the sensor metrics for this DEMO road in real-time.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Row 1: Ax, Ay, Az */}
        <div className="grid grid-cols-3 gap-4">
          <div className="space-y-2">
            <Label htmlFor="accel_x_g">Ax (g)</Label>
            <Input
              id="accel_x_g"
              name="accel_x_g"
              type="number"
              step="0.01"
              value={currentMetrics.accel_x_g ?? 0}
              onChange={handleChange}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="accel_y_g">Ay (g)</Label>
            <Input
              id="accel_y_g"
              name="accel_y_g"
              type="number"
              step="0.01"
              value={currentMetrics.accel_y_g ?? 0}
              onChange={handleChange}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="accel_z_g">Az (g)</Label>
            <Input
              id="accel_z_g"
              name="accel_z_g"
              type="number"
              step="0.01"
              value={currentMetrics.accel_z_g ?? 0}
              onChange={handleChange}
            />
          </div>
        </div>
        {/* Row 2: RMS and Load */}
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="accel_rms_g">RMS Accel (g)</Label>
            <Input
              id="accel_rms_g"
              name="accel_rms_g"
              type="number"
              step="0.01"
              value={currentMetrics.accel_rms_g}
              onChange={handleChange}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="loadcell_force_kg">Load (kg)</Label>
            <Input
              id="loadcell_force_kg"
              name="loadcell_force_kg"
              type="number"
              value={currentMetrics.loadcell_force_kg}
              onChange={handleChange}
            />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}