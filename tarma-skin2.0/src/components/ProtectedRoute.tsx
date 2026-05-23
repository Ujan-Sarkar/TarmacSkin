import { useAuth } from '@/hooks/useAuth';
import { Navigate, useLocation } from 'react-router-dom';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

/**
 * This component checks if the user is authenticated.
 * If they are, it renders the child components (e.g., the Dashboard).
 * If they are NOT, it redirects them to the login page ("/").
 */
export default function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { isAuthenticated } = useAuth();
  const location = useLocation();

  if (!isAuthenticated) {
    // Redirect them to the / login (Home) page
    // state={{ from: location }} is optional, but good practice.
    // It remembers the page they were trying to access.
    return <Navigate to="/" state={{ from: location }} replace />;
  }

  // If they are authenticated, just render the component they asked for.
  return <>{children}</>;
}

