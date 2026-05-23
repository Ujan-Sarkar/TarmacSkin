# TarmacSkin 2.0 - Infrastructure Monitoring Dashboard

An advanced AI-powered infrastructure monitoring system for real-time road and bridge health assessment using embedded sensors and machine learning analytics.

## Features

- **Real-time Monitoring**: Interactive map showing road and bridge infrastructure with live health status
- **AI-Powered Analysis**: Machine learning models analyze sensor data to predict maintenance needs
- **Comprehensive Metrics**: Track impact forces, structural health scores, accelerometer readings, and load measurements
- **Data Export**: Download sensor data as CSV for further analysis
- **Authentication**: Secure login and registration system using localStorage
- **Responsive Design**: Mobile-first design that works on all devices
- **Theme Support**: Light and dark mode toggle
- **Accessibility**: WCAG AA compliant with keyboard navigation and ARIA labels

## Technology Stack

- **Frontend**: React 18 with TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS with custom design system
- **UI Components**: shadcn/ui component library
- **Maps**: Leaflet for interactive mapping
- **Data Visualization**: Custom metric cards with sparklines
- **State Management**: React Context API for authentication and theme
- **Routing**: React Router v6

## Getting Started

### Prerequisites

- Node.js 16+ and npm installed
- Modern web browser

### Installation

1. Clone the repository:
```bash
git clone <your-git-url>
cd <project-name>
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

4. Open your browser and navigate to `http://localhost:8080`

### Building for Production

```bash
npm run build
```

The built files will be in the `dist` directory and can be served by any static file server.

## Project Structure

```
src/
├── components/          # Reusable UI components
│   ├── ui/             # shadcn/ui base components
│   ├── LoginModal.tsx
│   ├── RegisterModal.tsx
│   ├── MapView.tsx
│   ├── RoadSidebar.tsx
│   ├── RoadDetails.tsx
│   └── MetricCard.tsx
├── hooks/              # Custom React hooks
│   ├── useAuth.tsx     # Authentication logic
│   └── useTheme.tsx    # Theme management
├── pages/              # Page components
│   ├── Home.tsx        # Landing page
│   ├── Dashboard.tsx   # Main dashboard
│   └── NotFound.tsx    # 404 page
├── types/              # TypeScript type definitions
│   └── road.ts
└── App.tsx             # Root component

public/
└── sensors.json        # Mock sensor data
```

## Data Model

The application uses a JSON file (`public/sensors.json`) to simulate sensor data. Each road entry contains:

- **id**: Unique identifier
- **name**: Road/bridge name
- **location**: Geographic location
- **coords**: Array of [latitude, longitude] coordinates
- **last_updated**: Timestamp of last sensor reading
- **ai_verdict**: AI health assessment with confidence score
- **metrics**: Current sensor readings including:
  - estimated_impact_force_N
  - structural_health_score
  - overload_alert
  - accel_peak_g
  - accel_rms_g
  - loadcell_force_kg
- **timeseries**: Array of historical readings

## Authentication

The demo uses localStorage for authentication:

- Registered users are stored in `localStorage.users`
- Current session is stored in `localStorage.currentUser`
- Passwords are base64 encoded (NOT production-ready)

**For production use**, replace with a proper backend authentication system.

## Replacing Mock Data with Real API

To connect to a real sensor API:

1. Update `src/pages/Dashboard.tsx`:
```typescript
// Replace the fetch call
fetch('/sensors.json')
  .then(res => res.json())
  .then((data: RoadsData) => {
    setRoads(data.roads);
  });

// With your API endpoint
fetch('https://your-api.com/roads')
  .then(res => res.json())
  .then((data: RoadsData) => {
    setRoads(data.roads);
  });
```

2. Ensure your API returns data matching the `Road` interface in `src/types/road.ts`

## Features Walkthrough

### Home Page
- Hero section with project overview
- Feature cards explaining purpose, how it works, and key metrics
- Login/Register modal forms
- Theme toggle
- Responsive navigation

### Dashboard
- **Left Sidebar**: Search and filter roads, add sample roads
- **Center Map**: Interactive Leaflet map showing all monitored infrastructure
  - Color-coded by health status (green/orange/red)
  - Click to select and view details
  - Hover for quick status tooltip
- **Right Panel**: Detailed metrics for selected road
  - AI health assessment with confidence
  - 6 key sensor metrics with trend sparklines
  - Recent data table
  - CSV export functionality

## Customization

### Theme Colors
Edit `src/index.css` to customize the color palette:
```css
:root {
  --primary: 221 83% 53%;  /* Blue */
  --success: 142 71% 45%;  /* Green */
  --warning: 38 92% 50%;   /* Orange */
  --destructive: 0 84% 60%; /* Red */
}
```

### Adding New Metrics
1. Update the `Road` interface in `src/types/road.ts`
2. Add new data to `public/sensors.json`
3. Create metric cards in `src/components/RoadDetails.tsx`

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Mobile browsers (iOS Safari, Chrome Android)

## Accessibility

- Keyboard navigable
- ARIA labels on all interactive elements
- High contrast mode support
- Screen reader friendly
- Focus indicators on all focusable elements

## License

This project is provided as-is for demonstration purposes.

## Contact

For questions or support, contact the Infrastructure Monitoring Division.

---

**Note**: This is a frontend-only demonstration. For production use, implement proper backend authentication, real-time sensor connections, and secure data handling.
