import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { useTheme } from '@/hooks/useTheme';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { MapView } from '@/components/MapView';
import { RoadSidebar } from '@/components/RoadSidebar';
import { RoadDetails } from '@/components/RoadDetails';
// --- [FIXED IMPORT: Removed RoadMetrics] ---
import { Road, RoadsData } from '@/types/road';
import { WorkorderData } from '@/types/workorder';
import { Activity, Menu, User, LogOut, Moon, Sun } from 'lucide-react';
import { toast } from 'sonner';

// --- (Your DEMO_ROAD constant is here) ---
const DEMO_ROAD: Road = {
  id: 'rd_demo_001',
  name: 'DEMO Road',
  location: 'Digital Twin Proving Grounds',
  coords: [[12.9800, 77.6000], [12.9810, 77.6010], [12.9820, 77.6020]],
  last_updated: new Date(Date.now() - 7200000).toISOString(),
  ai_verdict: {
    label: 'Warning',
    confidence: 0.88,
  },
  metrics: {
    estimated_impact_force_N: 550,
    structural_health_score: 72,
    overload_alert: false,
    accel_x_g: 0.15,
    accel_y_g: 0.12,
    accel_z_g: 0.08,
    accel_rms_g: 0.09,
    loadcell_force_kg: 70,
  },
  timeseries: Array.from({ length: 13 }, (_, i) => ({
    ts: new Date(Date.now() - (12 - i) * 3600000).toISOString(),
    estimated_impact_force_N: 550 + Math.random() * 50,
    structural_health_score: 72 - Math.random() * 5,
    accel_x_g: 0.15 + (Math.random() - 0.5) * 0.05,
    accel_y_g: 0.12 + (Math.random() - 0.5) * 0.05,
    accel_z_g: 0.08 + (Math.random() - 0.5) * 0.05,
    accel_rms_g: 0.09 + Math.random() * 0.005,
    loadcell_force_kg: 70 + Math.random() * 5,
  })),
};
// ---

export default function Dashboard() {
  const [roads, setRoads] = useState<Road[]>([]);
  const [selectedRoad, setSelectedRoad] = useState<Road | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [workorders, setWorkorders] = useState<Record<string, WorkorderData>>({});

  // --- [NEW STATE for Data Mode] ---
  const [demoDataMode, setDemoDataMode] = useState<'manual' | 'real-time'>('manual');
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null); // To store interval ID
  // ---

  const { user, logout, isAuthenticated } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();

  // Effect for initial load (unchanged)
  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/');
      return;
    }

    fetch('/sensors.json')
      .then(res => res.json())
      .then((data: RoadsData) => {
        const allRoads = [DEMO_ROAD, ...data.roads];
        setRoads(allRoads);
        setSelectedRoad(DEMO_ROAD);
        toast.success('Dashboard loaded successfully');
      })
      .catch(err => {
        console.error('Failed to load sensor data:', err);
        toast.error('Failed to load sensor data');
      });
  }, [isAuthenticated, navigate]);

  // --- [NEW Effect for Real-time Polling] ---
  useEffect(() => {
    // Function to fetch latest data
    const fetchLatestDemoData = async () => {
      // Only fetch if the currently selected road *is* the demo road
      if (selectedRoad?.id !== 'rd_demo_001') {
        // console.log("Not polling: DEMO road is not selected."); // Optional log
        return; // Don't poll if DEMO road isn't visible
      }

      console.log("Polling for latest DEMO data...");
      try {
        const response = await fetch('http://localhost:5000/api/road/demo/latest');
        if (!response.ok) {
           const errorData = await response.json().catch(() => ({error: 'Failed to fetch latest data'}));
           throw new Error(errorData.error || 'Failed to fetch latest data');
        }
        const data = await response.json();

        // Check if data actually contains metrics (backend sends defaults if no ESP data yet)
        if (data && data.metrics && data.timestamp) {
            // Update the DEMO_ROAD object within the main 'roads' state
            setRoads(prevRoads => {
              return prevRoads.map(road => {
                if (road.id === 'rd_demo_001') {
                  // Create a new road object with updated metrics and verdict
                  return {
                    ...road,
                    metrics: data.metrics,
                    ai_verdict: data.ai_verdict,
                    last_updated: data.timestamp, // Use timestamp from backend
                  };
                }
                return road;
              });
            });

             // Also update selectedRoad state directly for immediate UI feedback
             setSelectedRoad(prev => prev && prev.id === 'rd_demo_001' ? ({
                 ...prev,
                 metrics: data.metrics,
                 ai_verdict: data.ai_verdict,
                 last_updated: data.timestamp,
             }) : prev);

        } else {
             console.log("Received default data or no timestamp from /latest endpoint. Waiting for ESP data.");
        }


      } catch (error) {
        console.error("Polling failed:", error);
        toast.error("Real-time data polling failed", { description: error instanceof Error ? error.message : undefined });
        // Optional: Stop polling after too many failures?
        // if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);
        // setDemoDataMode('manual'); // Switch back to manual on error?
      }
    };

    // Clear any previous interval before starting/stopping
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
      console.log("Cleared previous polling interval.");
    }

    // Start polling ONLY if mode is 'real-time'
    if (demoDataMode === 'real-time') {
      // Fetch immediately, then start interval
      fetchLatestDemoData(); // Fetch once right away
      pollingIntervalRef.current = setInterval(fetchLatestDemoData, 5000); // Poll every 5 seconds
      console.log("Real-time polling started (Interval ID:", pollingIntervalRef.current, ")");
    } else {
      console.log("Real-time polling stopped (mode is manual).");
    }

    // Cleanup function: Clear interval when component unmounts or mode changes
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null; // Clear ref on cleanup
        console.log("Polling interval cleared on cleanup.");
      }
    };
  // Ensure selectedRoad is a dependency so polling restarts/checks if it changes
  }, [demoDataMode, selectedRoad]);
  // --- [End Real-time Polling Effect] ---


  const handleAddSampleRoad = () => {
    // ... (logic for adding a sample road - unchanged) ...
    const sampleRoad: Road = {
      id: `rd_${Date.now()}`,
      name: 'Sample New Road',
      location: 'Test Location',
      coords: [[12.9816, 77.6046], [12.9826, 77.6056], [12.9836, 77.6066]],
      last_updated: new Date().toISOString(),
      ai_verdict: { label: 'Healthy', confidence: 0.95 },
      metrics: {
        estimated_impact_force_N: 400,
        structural_health_score: 90,
        overload_alert: false,
        accel_peak_g: 0.08,
        accel_rms_g: 0.025,
        loadcell_force_kg: 35,
        // Optional: Add x,y,z if needed for sample roads too
        // accel_x_g: 0.01,
        // accel_y_g: 0.01,
        // accel_z_g: 0.01,
      },
      timeseries: Array.from({ length: 13 }, (_, i) => ({
        ts: new Date(Date.now() - (12 - i) * 3600000).toISOString(),
        estimated_impact_force_N: 400 + Math.random() * 50,
        structural_health_score: 90 - Math.random() * 5,
        accel_peak_g: 0.08 + Math.random() * 0.02,
        accel_rms_g: 0.025 + Math.random() * 0.005,
        loadcell_force_kg: 35 + Math.random() * 5,
        // Optional: Add x,y,z if needed for sample roads too
        // accel_x_g: 0.01 + (Math.random() - 0.5) * 0.01,
        // accel_y_g: 0.01 + (Math.random() - 0.5) * 0.01,
        // accel_z_g: 0.01 + (Math.random() - 0.5) * 0.01,
      })),
     };
    setRoads(prev => [...prev, sampleRoad]);
    toast.success('Sample road added');
  };

  const handleWorkorderGenerated = (roadId: string, data: WorkorderData) => {
    // ... (unchanged) ...
    setWorkorders(prevWorkorders => ({
      ...prevWorkorders,
      [roadId]: data,
    }));
  };

  // --- [UPDATE Manual Handler to check mode and use correct type] ---
  // --- [FIXED TYPE: Use Road['metrics']] ---
  const handleDemoRoadMetricsUpdate = async (newMetricsFromForm: Road['metrics']) => {
    // Only process if in manual mode
    if (demoDataMode !== 'manual') {
      console.warn("Attempted to update metrics via form while in real-time mode. Ignoring.");
      toast.warning("Switch to Manual mode to enter data.", { description: "Real-time mode is active." });
      return; // Exit if not in manual mode
    }
    console.log("Processing manual update...");

    // Payload for manual processing endpoint
    // Ensure all expected fields are included, even if optional in the type
    const payload = {
      accel_x_g: newMetricsFromForm.accel_x_g ?? 0, // Use nullish coalescing for safety
      accel_y_g: newMetricsFromForm.accel_y_g ?? 0,
      accel_z_g: newMetricsFromForm.accel_z_g ?? 0,
      accel_rms_g: newMetricsFromForm.accel_rms_g,
      loadcell_force_kg: newMetricsFromForm.loadcell_force_kg,
    };

    try {
      // Call backend's manual processing endpoint
      const response = await fetch('http://localhost:5000/api/road/demo/process-manual', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
         const errorData = await response.json().catch(() => ({error: `API Error: ${response.statusText}`}));
         throw new Error(errorData.error || `API Error: ${response.statusText}`);
      }

      // Get calculated metrics/verdict from backend
      const { metrics: calculated_metrics, ai_verdict } = await response.json();

      // Update the DEMO_ROAD in the main 'roads' state
      let updatedDemoRoad : Road | null = null;
      const updatedRoads = roads.map(road => {
        if (road.id === 'rd_demo_001') {
           updatedDemoRoad = {
            ...road,
            metrics: calculated_metrics, // Use backend's response
            ai_verdict: ai_verdict,      // Use backend's response
            last_updated: new Date().toISOString(), // Manual update resets timestamp
           };
          return updatedDemoRoad;
        }
        return road;
      });
      setRoads(updatedRoads);

      // Update selectedRoad state directly for immediate UI feedback
      if (selectedRoad && selectedRoad.id === 'rd_demo_001' && updatedDemoRoad) {
        setSelectedRoad(updatedDemoRoad);
      }

    } catch (error) {
      console.error("Failed manual update:", error);
      toast.error("Failed to update demo metrics", { description: error instanceof Error ? error.message : "Could not connect to backend." });
    }
  };
  // --- [End Manual Handler Update] ---

  const getInitials = (name: string | null | undefined): string => {
    if (!name) return 'U';
    return name
      .split(' ')
      .map(n => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  return (
    <div className="h-screen flex flex-col bg-background">
      {/* Top Navigation (unchanged) */}
      <header className="border-b bg-card">
         {/* ... Header content ... */}
         <div className="flex items-center justify-between px-4 py-3">
             <div className="flex items-center gap-4"> {/* Left Side */}
                 <Button variant="ghost" size="icon" onClick={() => setSidebarOpen(!sidebarOpen)} className="lg:hidden"><Menu className="h-5 w-5" /></Button>
                 <div className="flex items-center gap-2"><Activity className="h-6 w-6 text-primary" /><h1 className="text-xl font-bold">TarmacSkin Dashboard</h1></div>
             </div>
             <div className="flex items-center gap-2"> {/* Right Side */}
                 <Button variant="ghost" size="icon" onClick={toggleTheme} aria-label="Toggle theme">{theme === 'light' ? <Moon className="h-5 w-5" /> : <Sun className="h-5 w-5" />}</Button>
                 <DropdownMenu> {/* User Menu */}
                     <DropdownMenuTrigger asChild><Button variant="ghost" className="gap-2"><Avatar className="h-8 w-8"><AvatarFallback className="bg-primary text-primary-foreground">{getInitials(user?.name)}</AvatarFallback></Avatar><span className="hidden sm:inline">{user?.name}</span></Button></DropdownMenuTrigger>
                     <DropdownMenuContent align="end"><DropdownMenuItem disabled><User className="mr-2 h-4 w-4" />View Profile</DropdownMenuItem><DropdownMenuItem onClick={logout}><LogOut className="mr-2 h-4 w-4" />Logout</DropdownMenuItem></DropdownMenuContent>
                 </DropdownMenu>
             </div>
         </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar (unchanged) */}
        <aside className={`${ sidebarOpen ? 'w-80' : 'w-0' } transition-all duration-300 overflow-hidden lg:w-80`}>
          <RoadSidebar
            roads={roads}
            selectedRoad={selectedRoad}
            onRoadSelect={setSelectedRoad}
            onAddSampleRoad={handleAddSampleRoad}
          />
        </aside>

        {/* Center Map (unchanged) */}
        <main className="flex-1 p-4">
          <MapView
            roads={roads}
            selectedRoad={selectedRoad}
            onRoadSelect={setSelectedRoad}
          />
        </main>

        {/* Right Details Panel */}
        {selectedRoad && (
          <aside className="w-full lg:w-96 border-l bg-card overflow-hidden">
            {/* --- [Pass Mode State and Setter Down] --- */}
            <RoadDetails
              road={selectedRoad}
              workorder={workorders[selectedRoad.id]}
              onWorkorderGenerated={(data) => handleWorkorderGenerated(selectedRoad.id, data)}
              onDemoRoadMetricsUpdate={handleDemoRoadMetricsUpdate}
              demoDataMode={demoDataMode} // Pass current mode
              onDemoDataModeChange={setDemoDataMode} // Pass the state setter function
            />
            {/* --- */}
          </aside>
        )}
      </div>
    </div>
  );
}

