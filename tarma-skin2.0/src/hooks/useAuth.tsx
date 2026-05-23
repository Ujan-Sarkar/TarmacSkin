import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';

interface User {
  id: string;
  email: string;
  name: string;
}

interface AuthContextType {
  user: User | null;
  login: (email: string, password: string) => Promise<boolean>;
  register: (email: string, password: string, name: string) => Promise<boolean>;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    // Check for existing session
    const storedUser = localStorage.getItem('currentUser');
    if (storedUser) {
      setUser(JSON.parse(storedUser));
    }
  }, []);

  const register = async (email: string, password: string, name: string): Promise<boolean> => {
    try {
      // Validate inputs
      if (!email || !password || !name) {
        toast.error('All fields are required');
        return false;
      }

      if (!email.includes('@')) {
        toast.error('Please enter a valid email');
        return false;
      }

      if (password.length < 6) {
        toast.error('Password must be at least 6 characters');
        return false;
      }

      // Get existing users
      const users = JSON.parse(localStorage.getItem('users') || '[]');
      
      // Check if user already exists
      if (users.some((u: any) => u.email === email)) {
        toast.error('User with this email already exists');
        return false;
      }

      // Create new user (simple hash for demo - NOT production secure)
      const newUser = {
        id: `user_${Date.now()}`,
        email,
        name,
        password: btoa(password), // Base64 encode for demo only
      };

      users.push(newUser);
      localStorage.setItem('users', JSON.stringify(users));

      // Auto-login after registration
      const { password: _, ...userWithoutPassword } = newUser;
      setUser(userWithoutPassword);
      localStorage.setItem('currentUser', JSON.stringify(userWithoutPassword));

      toast.success('Registration successful! Welcome aboard.');
      navigate('/dashboard');
      return true;
    } catch (error) {
      toast.error('Registration failed. Please try again.');
      return false;
    }
  };

  const login = async (email: string, password: string): Promise<boolean> => {
    try {
      // Validate inputs
      if (!email || !password) {
        toast.error('Email and password are required');
        return false;
      }

      const users = JSON.parse(localStorage.getItem('users') || '[]');
      const foundUser = users.find(
        (u: any) => u.email === email && u.password === btoa(password)
      );

      if (!foundUser) {
        toast.error('Invalid email or password');
        return false;
      }

      const { password: _, ...userWithoutPassword } = foundUser;
      setUser(userWithoutPassword);
      localStorage.setItem('currentUser', JSON.stringify(userWithoutPassword));

      toast.success('Login successful! Welcome back.');
      navigate('/dashboard');
      return true;
    } catch (error) {
      toast.error('Login failed. Please try again.');
      return false;
    }
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem('currentUser');
    toast.success('Logged out successfully');
    navigate('/');
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        login,
        register,
        logout,
        isAuthenticated: !!user,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
