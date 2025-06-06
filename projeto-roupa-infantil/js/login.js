import React, { useState } from 'react';
import { setToken } from '../utils/auth';

const Login = ({ onLoginSuccess, onMFARequired }) => {
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    mfaToken: ''
  });
  const [showMFA, setShowMFA] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: formData.email,
          password: formData.password,
          mfa_token: formData.mfaToken || undefined
        }),
      });

      const data = await response.json();

      if (response.ok) {
        if (data.mfa_required) {
          setShowMFA(true);
        } else {
          setToken(data.access, data.refresh);
          onLoginSuccess();
        }
      } else {
        setError(data.error || 'Login failed');
      }
    } catch (error) {
      setError('Network error. Please try again.');
      console.error('Login error:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-form">
        <h2>SuperDevSecOps Login</h2>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="email">Email:</label>
            <input
              type="email"
              id="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              required
              disabled={loading}
            />
          </div>
          
          <div className="form-group">
            <label htmlFor="password">Password:</label>
            <input
              type="password"
              id="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              required
              disabled={loading}
            />
          </div>

          {showMFA && (
            <div className="form-group">
              <label htmlFor="mfaToken">MFA Token:</label>
              <input
                type="text"
                id="mfaToken"
                name="mfaToken"
                value={formData.mfaToken}
                onChange={handleChange}
                placeholder="Enter 6-digit code"
                maxLength="6"
                disabled={loading}
              />
            </div>
          )}

          {error && <div className="error-message">{error}</div>}

          <button type="submit" disabled={loading}>
            {loading ? 'Logging in...' : 'Login'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default Login;