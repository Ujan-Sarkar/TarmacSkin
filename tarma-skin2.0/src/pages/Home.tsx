import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { LoginModal } from '@/components/LoginModal';
import { RegisterModal } from '@/components/RegisterModal';
import { useAuth } from '@/hooks/useAuth';
import { useTheme } from '@/hooks/useTheme';
import { Link } from 'react-router-dom';
import { Activity, Shield, TrendingUp, Moon, Sun } from 'lucide-react';

export default function Home() {
  const [loginOpen, setLoginOpen] = useState(false);
  const [registerOpen, setRegisterOpen] = useState(false);
  const { isAuthenticated } = useAuth();
  const { theme, toggleTheme } = useTheme();

  return (
    <div className="min-h-screen bg-background">
      {/* Navigation */}
      <nav className="border-b">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Activity className="h-6 w-6 text-primary" />
              <h1 className="text-xl font-bold">TarmacSkin 2.0</h1>
            </div>
            <div className="flex items-center gap-4">
              <Button variant="ghost" asChild>
                <Link to="/">Home</Link>
              </Button>
              <Button variant="ghost" asChild>
                <a href="#about">About</a>
              </Button>
              {isAuthenticated ? (
                <Button asChild>
                  <Link to="/dashboard">Dashboard</Link>
                </Button>
              ) : (
                <>
                  <Button variant="outline" onClick={() => setLoginOpen(true)}>
                    Login
                  </Button>
                  <Button onClick={() => setRegisterOpen(true)}>
                    Register
                  </Button>
                </>
              )}
              <Button
                variant="ghost"
                size="icon"
                onClick={toggleTheme}
                aria-label="Toggle theme"
              >
                {theme === 'light' ? <Moon className="h-5 w-5" /> : <Sun className="h-5 w-5" />}
              </Button>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="container mx-auto px-4 py-20 text-center">
        <div className="max-w-3xl mx-auto space-y-6">
          <h2 className="text-5xl font-bold tracking-tight">
            Real-Time Infrastructure Monitoring
          </h2>
          <p className="text-xl text-muted-foreground">
            Advanced AI-powered system for monitoring road and bridge health using
            embedded sensors and machine learning analytics
          </p>
          {!isAuthenticated && (
            <div className="flex gap-4 justify-center pt-4">
              <Button size="lg" onClick={() => setRegisterOpen(true)}>
                Get Started
              </Button>
              <Button size="lg" variant="outline" onClick={() => setLoginOpen(true)}>
                Sign In
              </Button>
            </div>
          )}
        </div>
      </section>

      {/* Feature Cards */}
      <section className="container mx-auto px-4 py-16">
        <div className="grid md:grid-cols-3 gap-6">
          <Card>
            <CardHeader>
              <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center mb-4">
                <Shield className="h-6 w-6 text-primary" />
              </div>
              <CardTitle>Purpose</CardTitle>
            </CardHeader>
            <CardContent>
              <CardDescription className="text-base">
                Prevent infrastructure failures by continuously monitoring structural
                health through advanced sensor networks and AI analysis
              </CardDescription>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="w-12 h-12 rounded-lg bg-success/10 flex items-center justify-center mb-4">
                <Activity className="h-6 w-6 text-success" />
              </div>
              <CardTitle>How It Works</CardTitle>
            </CardHeader>
            <CardContent>
              <CardDescription className="text-base">
                Embedded sensors capture impact forces, accelerometer data, and load
                measurements. AI models analyze patterns to predict maintenance needs
              </CardDescription>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="w-12 h-12 rounded-lg bg-warning/10 flex items-center justify-center mb-4">
                <TrendingUp className="h-6 w-6 text-warning" />
              </div>
              <CardTitle>Key Metrics</CardTitle>
            </CardHeader>
            <CardContent>
              <CardDescription className="text-base">
                Track structural health scores, impact forces, overload alerts,
                and accelerometer readings in real-time with historical trend analysis
              </CardDescription>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* About Section */}
      <section id="about" className="container mx-auto px-4 py-16">
        <Card>
          <CardHeader>
            <CardTitle className="text-2xl">About TarmacSkin 2.0</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-muted-foreground">
              TarmacSkin 2.0 is an innovative infrastructure monitoring system that combines
              embedded sensor technology with advanced AI algorithms to provide real-time
              health assessments of roads and bridges.
            </p>
            <p className="text-muted-foreground">
              Our system measures critical parameters including estimated impact forces,
              structural health scores, accelerometer readings, and load cell measurements
              to provide comprehensive infrastructure monitoring.
            </p>
          </CardContent>
        </Card>
      </section>

      {/* Footer */}
      <footer className="border-t mt-20">
        <div className="container mx-auto px-4 py-8">
          <div className="flex flex-col md:flex-row justify-between items-center gap-4">
            <div className="text-sm text-muted-foreground">
              © 2025 TarmacSkin 2.0. All rights reserved.
            </div>
            <div className="flex gap-6 text-sm text-muted-foreground">
              <a href="mailto:contact@tarmacskin.com" className="hover:text-foreground">
                Contact
              </a>
              <span>Team: Infrastructure Monitoring Division</span>
            </div>
          </div>
        </div>
      </footer>

      {/* Modals */}
      <LoginModal open={loginOpen} onOpenChange={setLoginOpen} />
      <RegisterModal open={registerOpen} onOpenChange={setRegisterOpen} />
    </div>
  );
}
