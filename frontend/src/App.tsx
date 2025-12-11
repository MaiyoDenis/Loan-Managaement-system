import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { CssBaseline, Box } from '@mui/material';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Provider } from 'react-redux';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

import { store } from './store';
import { AuthProvider } from './contexts/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import Layout from './components/Layout';

// Pages
import LoginPage from './pages/auth/LoginPage';
import DashboardPage from './pages/DashboardPage';
import UsersPage from './pages/users/UsersPage';
import BranchesPage from './pages/branches/BranchesPage';
import GroupsPage from './pages/groups/GroupsPage';
import GroupDetailsPage from './pages/groups/GroupDetailsPage';
import LoanProductsPage from './pages/loan-products/LoanProductsPage';

// Theme configuration
const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
      light: '#42a5f5',
      dark: '#1565c0',
    },
    secondary: {
      main: '#dc004e',
    },
    background: {
      default: '#f5f5f5',
    },
  },
  typography: {
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
    h4: {
      fontWeight: 600,
    },
  },
  shape: {
    borderRadius: 8,
  },
});

// React Query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
});

function App() {
  return (
    <Provider store={store}>
      <QueryClientProvider client={queryClient}>
        <ThemeProvider theme={theme}>
          <CssBaseline />
          <AuthProvider>
            <Router>
              <Box sx={{ display: 'flex', minHeight: '100vh' }}>
                <Routes>
                  {/* Public routes */}
                  <Route path="/login" element={<LoginPage />} />
                  
                  {/* Protected routes */}
                  <Route
                    path="/*"
                    element={
                      <ProtectedRoute>
                        <Layout>
                          <Routes>
                            <Route path="/" element={<Navigate to="/dashboard" replace />} />
                            <Route path="/dashboard" element={<DashboardPage />} />
                            <Route path="/users" element={<UsersPage />} />
                            <Route path="/branches" element={<BranchesPage />} />
                            <Route path="/groups" element={<GroupsPage />} />
                            <Route path="/groups/:groupId" element={<GroupDetailsPage />} />
                            <Route path="/loan-products" element={<LoanProductsPage />} />
                            {/* Add more routes as needed */}
                          </Routes>
                        </Layout>
                      </ProtectedRoute>
                    }
                  />
                </Routes>
              </Box>
            </Router>
          </AuthProvider>
          <ToastContainer
            position="top-right"
            autoClose={5000}
            hideProgressBar={false}
            newestOnTop={false}
            closeOnClick
            rtl={false}
            pauseOnFocusLoss
            draggable
            pauseOnHover
          />
        </ThemeProvider>
      </QueryClientProvider>
    </Provider>
  );
}

export default App;
