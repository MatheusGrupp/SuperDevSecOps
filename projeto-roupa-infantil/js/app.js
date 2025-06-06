import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Route, Switch, Redirect } from 'react-router-dom';
import Login from './components/Login';
import Dashboard from './components/Dashboard';
import MFA from './components/MFA';
import { isAuthenticated, getToken } from './utils/auth';
import './App.css';

function App() {
  const [isAuth, setIsAuth] = useState(false);
  const [mfaRequired, setMfaRequired] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkAuth = async () => {
      const token = getToken();
      if (token) {
        try {
          const response = await fetch('/api/auth/profile', {
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json'
            }
          });
          if (response.ok) {
            setIsAuth(true);
          }
        } catch (error) {
          console.error('Auth check failed:', error);
        }
      }
      setLoading(false);
    };
    
    checkAuth();
  }, []);

  if (loading) {
    return <div className="loading">Loading...</div>;
  }

  return (
    <Router>
      <div className="App">
        <Switch>
          <Route 
            path="/login" 
            render={() => 
              isAuth ? 
              <Redirect to="/dashboard" /> : 
              <Login 
                onLoginSuccess={() => setIsAuth(true)} 
                onMFARequired={() => setMfaRequired(true)}
              />
            } 
          />
          <Route 
            path="/mfa" 
            render={() => 
              mfaRequired ? 
              <MFA onMFASuccess={() => {
                setMfaRequired(false);
                setIsAuth(true);
              }} /> : 
              <Redirect to="/login" />
            } 
          />
          <Route 
            path="/dashboard" 
            render={() => 
              isAuth ? 
              <Dashboard onLogout={() => setIsAuth(false)} /> : 
              <Redirect to="/login" />
            } 
          />
          <Route 
            exact path="/" 
            render={() => 
              isAuth ? <Redirect to="/dashboard" /> : <Redirect to="/login" />
            } 
          />
        </Switch>
      </div>
    </Router>
  );
}

export default App;