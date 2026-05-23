import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Road } from '@/types/road';
import { WorkorderData } from '@/types/workorder';
import { MetricCard } from './MetricCard';
import { WorkorderCreated } from './WorkorderCreated';
import { DemoDataForm } from './DemoDataForm';
import { Download, Activity, AlertCircle, Wrench, Loader2 } from 'lucide-react';
import { format } from 'date-fns';
import { toast } from 'sonner';
import { useState } from 'react';
// --- [NEW Imports for Toggle] ---
import { Label } from "@/components/ui/label"; // <-- IMPORT ADDED HERE
import { Switch } from "@/components/ui/switch";
// ---

// --- [UPDATE Props] ---
interface RoadDetailsProps {
  road: Road;
  workorder: WorkorderData | undefined;
  onWorkorderGenerated: (data: WorkorderData) => void;
  onDemoRoadMetricsUpdate: (newMetrics: Road['metrics']) => void;
  demoDataMode: 'manual' | 'real-time'; // Add mode prop
  onDemoDataModeChange: (mode: 'manual' | 'real-time') => void; // Add handler prop
}
// ---

export function RoadDetails({
  road,
  workorder,
  onWorkorderGenerated,
  onDemoRoadMetricsUpdate,
  demoDataMode, // Get mode prop
  onDemoDataModeChange, // Get handler prop
}: RoadDetailsProps) {

  const [isGeneratingWorkorder, setIsGeneratingWorkorder] = useState(false);

  // --- Calculate Peak Accel (unchanged) ---
  const calculatedPeakAccel = road.metrics.accel_peak_g ?? Math.max(
    road.metrics.accel_x_g ?? 0,
    road.metrics.accel_y_g ?? 0,
    road.metrics.accel_z_g ?? 0
  );
  const peakSparkline = road.timeseries.map(d =>
    d.accel_peak_g ?? Math.max(
      d.accel_x_g ?? 0,
      d.accel_y_g ?? 0,
      d.accel_z_g ?? 0
    )
  );
  // ---

  const getVerdictColor = () => {
    switch (road.ai_verdict.label) {
      case 'Healthy':
        return 'bg-success text-success-foreground';
      case 'Warning':
        return 'bg-warning text-warning-foreground';
      case 'Critical':
        return 'bg-destructive text-destructive-foreground';
      default:
        return 'bg-secondary text-secondary-foreground';
    }
   };

  const exportToCSV = () => {
    // ... (CSV export logic - unchanged) ...
     const headers = ['Timestamp', 'Impact Force (N)', 'Health Score', 'Accel Peak (g)', 'Accel RMS (g)', 'Load Cell (kg)'];
     const rows = road.timeseries.map(data => {
        const peak = data.accel_peak_g ?? Math.max(data.accel_x_g ?? 0, data.accel_y_g ?? 0, data.accel_z_g ?? 0);
        return [
         data.ts,
         (data.estimated_impact_force_N || 0).toFixed(0), // Handle potential null/undefined
         data.structural_health_score,
         peak.toFixed(3), // Ensure consistent formatting
         (data.accel_rms_g || 0).toFixed(3),
         (data.loadcell_force_kg || 0).toFixed(1),
       ];
     });
     const csvContent = [headers.join(','), ...rows.map(row => row.join(','))].join('\n');
     const blob = new Blob([csvContent], { type: 'text/csv' });
     const url = window.URL.createObjectURL(blob);
     const a = document.createElement('a');
     a.href = url;
     a.download = `${road.name.replace(/\s+/g, '_')}_data.csv`;
     document.body.appendChild(a);
     a.click();
     document.body.removeChild(a);
     window.URL.revokeObjectURL(url);
     toast.success('Data exported successfully');
  };

  const handleGenerateWorkorder = async () => {
    console.log("Generate Workorder button clicked..."); // Debug log
    setIsGeneratingWorkorder(true); // Show loading spinner

    // 1. Gather data to send to backend
    const workorderPayload = {
      roadId: road.id,
      roadName: road.name,
      roadLocation: road.location,
      currentStatus: road.ai_verdict.label, // Send the current predicted status
    };
    console.log("Payload to send:", workorderPayload); // Debug log

    try {
      // 2. Call the backend endpoint
      console.log("Sending request to backend..."); // Debug log
      const response = await fetch('http://localhost:5000/api/workorder/create', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(workorderPayload),
      });
      console.log("Backend response status:", response.status); // Debug log

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: `API Error: ${response.statusText}` })); // Handle non-JSON errors
        console.error("Backend error response:", errorData); // Debug log
        throw new Error(errorData.error || `API Error: ${response.statusText}`);
      }

      // 3. Get the generated data (including hash) from the backend
      const result = await response.json();
      console.log("Backend success response:", result); // Debug log

      // 4. Create the complete WorkorderData object for the frontend state
      const newWorkorderData: WorkorderData = {
        timestamp: new Date(result.timestamp), // Convert ISO string back to Date
        workorderId: result.workorderId,
        onChainHash: result.onChainHash,
        // Ensure all possible statuses from backend are handled
        status: result.status as 'active' | 'completed' | 'pending' ,
      };

      // 5. Call the parent handler (in Dashboard.tsx) to update the global state
      onWorkorderGenerated(newWorkorderData);

      toast.success('Workorder Generated Successfully!', {
        description: `Workorder ID: ${newWorkorderData.workorderId}`,
      });

    } catch (error) {
      console.error("Failed to generate workorder:", error); // Log the full error object
      toast.error("Failed to generate workorder", {
         description: error instanceof Error ? error.message : "Could not connect to backend or unexpected error.",
      });
    } finally {
       setIsGeneratingWorkorder(false); // Hide loading spinner
       console.log("Finished handleGenerateWorkorder."); // Debug log
    }
   };


  return (
    <div className="h-full overflow-auto">
      <div className="p-6 space-y-6">
        {/* Header */}
        <div>
          <div className="flex items-start justify-between mb-2">
            <div>
              <h2 className="text-2xl font-bold">{road.name}</h2>
              <p className="text-muted-foreground">{road.location}</p>
            </div>
            <div className="flex flex-col items-end gap-2">
              <Button onClick={exportToCSV} variant="outline" size="sm" className="w-full">
                <Download className="mr-2 h-4 w-4" />
                Export CSV
              </Button>
              {/* --- [UPDATE BUTTON with loading state] --- */}
              <Button
                onClick={handleGenerateWorkorder}
                size="sm"
                className="w-full"
                disabled={isGeneratingWorkorder} // Disable while loading
              >
                {isGeneratingWorkorder ? (
                   <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                   <Wrench className="mr-2 h-4 w-4" />
                )}
                {isGeneratingWorkorder ? 'Generating...' : 'Generate Workorder'}
              </Button>
              {/* --- */}
            </div>
          </div>
          <p className="text-sm text-muted-foreground">
            Last updated: {format(new Date(road.last_updated), 'PPpp')}
          </p>
        </div>

        {/* Workorder Card (if generated) */}
        {workorder && (
          <WorkorderCreated
            timestamp={workorder.timestamp}
            workorderId={workorder.workorderId}
            onChainHash={workorder.onChainHash}
            status={workorder.status}
          />
        )}

        {/* AI Verdict */}
         <Card>
           <CardHeader>
             <CardTitle className="flex items-center gap-2">
               <Activity className="h-5 w-5" />
               AI Health Assessment
             </CardTitle>
           </CardHeader>
           <CardContent>
             <div className="flex items-center gap-3">
               <Badge className={`${getVerdictColor()} text-lg px-4 py-1`}>
                 {road.ai_verdict.label}
               </Badge>
               <div className="flex-1">
                 <div className="text-sm text-muted-foreground mb-1">
                   Confidence: {(road.ai_verdict.confidence * 100).toFixed(1)}%
                 </div>
                 <div className="w-full bg-secondary rounded-full h-2">
                   <div
                     className="bg-primary h-2 rounded-full transition-all"
                     style={{ width: `${road.ai_verdict.confidence * 100}%` }}
                   />
                 </div>
               </div>
             </div>
             {road.metrics.overload_alert && (
               <div className="mt-4 p-3 bg-destructive/10 border border-destructive/20 rounded-lg flex items-start gap-2">
                 <AlertCircle className="h-5 w-5 text-destructive flex-shrink-0 mt-0.5" />
                 <div>
                   <div className="font-medium text-destructive">Overload Alert</div>
                   <div className="text-sm text-muted-foreground">
                     This structure is experiencing loads beyond safe operational limits
                   </div>
                 </div>
               </div>
             )}
           </CardContent>
         </Card>

        {/* --- [Toggle for DEMO Road] --- */}
        {road.id === 'rd_demo_001' && (
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                 <Label htmlFor="data-mode-toggle" className="font-medium">
                   DEMO Data Source
                 </Label>
                 <div className="flex items-center space-x-2">
                   <Label htmlFor="data-mode-toggle" className={demoDataMode === 'manual' ? '' : 'text-muted-foreground'}>
                     Manual
                   </Label>
                   <Switch
                     id="data-mode-toggle"
                     checked={demoDataMode === 'real-time'}
                     onCheckedChange={(checked) => {
                       onDemoDataModeChange(checked ? 'real-time' : 'manual');
                     }}
                     aria-label="Toggle between manual and real-time data input"
                   />
                   <Label htmlFor="data-mode-toggle" className={demoDataMode === 'real-time' ? '' : 'text-muted-foreground'}>
                     Real-time
                   </Label>
                 </div>
              </div>
            </CardContent>
          </Card>
        )}
        {/* --- [End Toggle] --- */}


        {/* --- [Conditional Demo Data Form] --- */}
        {road.id === 'rd_demo_001' && demoDataMode === 'manual' && (
          <DemoDataForm
            currentMetrics={road.metrics}
            onMetricsChange={onDemoRoadMetricsUpdate}
          />
        )}
        {/* --- */}

        {/* Metrics Grid */}
        <div>
          <h3 className="text-lg font-semibold mb-4">Sensor Metrics</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
             <MetricCard
               label="Impact Force"
               value={road.metrics.estimated_impact_force_N}
               unit="N"
               sparklineData={road.timeseries.map(d => d.estimated_impact_force_N)}
               trend={road.metrics.estimated_impact_force_N > 500 ? 'up' : 'neutral'}
             />
             <MetricCard
               label="Structural Health Score"
               value={road.metrics.structural_health_score}
               unit="%"
               sparklineData={road.timeseries.map(d => d.structural_health_score)}
               trend={road.metrics.structural_health_score > 80 ? 'up' : road.metrics.structural_health_score < 60 ? 'down' : 'neutral'}
             />
             <MetricCard
               label="Peak Acceleration"
               value={calculatedPeakAccel}
               unit="g"
               sparklineData={peakSparkline}
             />
             <MetricCard
               label="RMS Acceleration"
               value={road.metrics.accel_rms_g}
               unit="g"
               sparklineData={road.timeseries.map(d => d.accel_rms_g)}
             />
             <MetricCard
               label="Load Cell Force"
               value={road.metrics.loadcell_force_kg}
               unit="kg"
               sparklineData={road.timeseries.map(d => d.loadcell_force_kg)}
             />
             <Card>
               <CardContent className="p-4">
                 <div className="text-sm font-medium text-muted-foreground mb-2">
                   Overload Status
                 </div>
                 <div className="flex items-center gap-2">
                   <div className={`h-3 w-3 rounded-full ${road.metrics.overload_alert ? 'bg-destructive pulse-dot' : 'bg-success'}`} />
                   <span className="text-2xl font-bold">
                     {road.metrics.overload_alert ? 'ACTIVE' : 'Normal'}
                   </span>
                 </div>
               </CardContent>
             </Card>
          </div>
        </div>

        {/* Recent Data Table */}
        <Card>
          <CardHeader>
            <CardTitle>Recent Sensor Readings</CardTitle>
            <CardDescription>Last 5 measurements</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-2 px-2">Time</th>
                    <th className="text-right py-2 px-2">Impact (N)</th>
                    <th className="text-right py-2 px-2">Health (%)</th>
                    <th className="text-right py-2 px-2">Accel (g)</th>
                    <th className="text-right py-2 px-2">Load (kg)</th>
                  </tr>
                </thead>
                <tbody>
                  {road.timeseries.slice(-5).reverse().map((data, index) => {
                     const rowPeakAccel = data.accel_peak_g ?? Math.max(data.accel_x_g ?? 0, data.accel_y_g ?? 0, data.accel_z_g ?? 0);
                     // Add checks for null/undefined before calling toFixed
                     const impactN = data.estimated_impact_force_N ?? 0;
                     const loadKg = data.loadcell_force_kg ?? 0;
                     return (
                       <tr key={index} className="border-b last:border-0">
                         <td className="py-2 px-2 text-muted-foreground">{format(new Date(data.ts), 'HH:mm')}</td>
                         <td className="py-2 px-2 text-right font-mono">{impactN.toFixed(0)}</td>
                         <td className="py-2 px-2 text-right font-mono">{data.structural_health_score}</td>
                         <td className="py-2 px-2 text-right font-mono">{rowPeakAccel.toFixed(3)}</td>
                         <td className="py-2 px-2 text-right font-mono">{loadKg.toFixed(1)}</td>
                       </tr>
                     );
                  })}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

