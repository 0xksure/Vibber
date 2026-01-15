import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from './App';

// Create a new QueryClient for each test
const createTestQueryClient = () => new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
    },
  },
});

// Wrap component with all necessary providers for testing
const renderWithProviders = (component) => {
  const testQueryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={testQueryClient}>
      <BrowserRouter>
        {component}
      </BrowserRouter>
    </QueryClientProvider>
  );
};

describe('App', () => {
  test('renders login page by default when not authenticated', () => {
    renderWithProviders(<App />);
    // Should show login page for unauthenticated users
    const loginElement = screen.getByText(/welcome back/i);
    expect(loginElement).toBeInTheDocument();
  });

  test('renders Vibber branding', () => {
    renderWithProviders(<App />);
    const brandingElement = screen.getByText(/vibber/i);
    expect(brandingElement).toBeInTheDocument();
  });

  test('shows email input field on login page', () => {
    renderWithProviders(<App />);
    const emailInput = screen.getByPlaceholderText(/you@company.com/i);
    expect(emailInput).toBeInTheDocument();
  });

  test('shows password input field on login page', () => {
    renderWithProviders(<App />);
    const passwordInput = screen.getByPlaceholderText(/enter your password/i);
    expect(passwordInput).toBeInTheDocument();
  });
});
