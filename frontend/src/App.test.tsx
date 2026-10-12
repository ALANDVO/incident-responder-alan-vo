import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { App } from './App';

describe('Frontend Workflows and Dashboard', () => {
  it('renders application login screen for unauthenticated users', () => {
    render(
      <BrowserRouter>
        <AuthProvider>
          <App />
        </AuthProvider>
      </BrowserRouter>
    );

    expect(screen.getByRole('heading', { name: /sign in/i })).toBeDefined();
    expect(screen.getByLabelText(/email/i)).toBeDefined();
    expect(document.getElementById('password')).toBeDefined();
  });

  it('renders register link on authentication page', () => {
    render(
      <BrowserRouter>
        <AuthProvider>
          <App />
        </AuthProvider>
      </BrowserRouter>
    );

    const signupLink = screen.getByRole('link', { name: /create one/i });
    expect(signupLink).toBeDefined();
    expect(signupLink.getAttribute('href')).toBe('/register');
  });

  it('renders submit button for login credential verification', () => {
    render(
      <BrowserRouter>
        <AuthProvider>
          <App />
        </AuthProvider>
      </BrowserRouter>
    );

    const submitBtn = screen.getByRole('button', { name: /sign in/i });
    expect(submitBtn).toBeDefined();
  });
});
