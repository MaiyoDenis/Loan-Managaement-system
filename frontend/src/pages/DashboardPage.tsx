import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Stack,
  CircularProgress,
  Alert,
  Button,
  Card,
  CardContent,
  Avatar,
} from '@mui/material';
import {
  AttachMoney,
  CheckCircle,
  Payment,
  People,
} from '@mui/icons-material';
import { analyticsAPI } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import { useApiError } from '../hooks/useApiError';
import CardSkeleton from '../components/common/CardSkeleton';

interface AnalyticsData {
  total_loans: number;
  active_loans: number;
  total_payments: number;
  pending_approvals: number;
  total_accounts: number;
  monthly_revenue: number;
}

interface StatCardProps {
  title: string;
  value: number | string;
  icon: React.ReactElement;
  color: string;
}

const StatCard: React.FC<StatCardProps> = ({ title, value, icon, color }) => (
  <Card elevation={1}>
    <CardContent>
      <Stack direction="row" spacing={2} alignItems="center">
        <Avatar sx={{ bgcolor: color, width: 48, height: 48 }}>
          {icon}
        </Avatar>
        <Box sx={{ flexGrow: 1 }}>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            {title}
          </Typography>
          <Typography variant="h5" component="div" fontWeight="medium">
            {value}
          </Typography>
        </Box>
      </Stack>
    </CardContent>
  </Card>
);

const DashboardPage: React.FC = () => {
  const { user } = useAuth();
  const { showError } = useApiError();
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const response = await analyticsAPI.getAnalytics();
        setAnalytics(response);
        setError(null);
      } catch (err) {
        const errorMessage = 'Failed to load analytics data';
        setError(errorMessage);
        showError(err as Error);
      } finally {
        setLoading(false);
      }
    };

    fetchAnalytics();
  }, [showError]);

  if (loading) {
    return (
      <Stack spacing={3}>
        <Paper elevation={1} sx={{ p: 3 }}>
          <Typography variant="h4" component="h1" fontWeight="bold" gutterBottom>
            Welcome back!
          </Typography>
        </Paper>
        <Box
          sx={{
            display: 'grid',
            gridTemplateColumns: {
              xs: '1fr',
              sm: 'repeat(2, 1fr)',
              lg: 'repeat(4, 1fr)',
            },
            gap: 3,
          }}
        >
          <CardSkeleton count={4} />
        </Box>
      </Stack>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 2 }}>
        {error}
      </Alert>
    );
  }

  return (
    <Stack spacing={3}>
      {/* Welcome Header */}
      <Paper elevation={1} sx={{ p: 3 }}>
        <Typography variant="h4" component="h1" fontWeight="bold" gutterBottom>
          Welcome back, {user?.name || 'User'}!
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Here's an overview of your loan management system.
        </Typography>
      </Paper>

      {/* Stats Cards */}
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: {
            xs: '1fr',
            sm: 'repeat(2, 1fr)',
            lg: 'repeat(4, 1fr)',
          },
          gap: 3,
        }}
      >
        <StatCard
          title="Total Loans"
          value={analytics?.total_loans || 0}
          icon={<AttachMoney />}
          color="primary.main"
        />
        <StatCard
          title="Active Loans"
          value={analytics?.active_loans || 0}
          icon={<CheckCircle />}
          color="success.main"
        />
        <StatCard
          title="Total Payments"
          value={analytics?.total_payments || 0}
          icon={<Payment />}
          color="warning.main"
        />
        <StatCard
          title="Total Accounts"
          value={analytics?.total_accounts || 0}
          icon={<People />}
          color="secondary.main"
        />
      </Box>

      {/* Additional Stats */}
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', md: 'repeat(2, 1fr)' },
          gap: 3,
        }}
      >
        <Paper elevation={1} sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            Pending Approvals
          </Typography>
          <Typography variant="h3" color="warning.main" fontWeight="bold">
            {analytics?.pending_approvals || 0}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            Loan applications awaiting approval
          </Typography>
        </Paper>

        <Paper elevation={1} sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            Monthly Revenue
          </Typography>
          <Typography variant="h3" color="success.main" fontWeight="bold">
            KES {analytics?.monthly_revenue?.toLocaleString() || '0'}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            Revenue from payments this month
          </Typography>
        </Paper>
      </Box>

      {/* Quick Actions */}
      <Paper elevation={1} sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          Quick Actions
        </Typography>
        <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} sx={{ mt: 2 }}>
          <Button variant="contained" color="primary" fullWidth>
            Create New Loan
          </Button>
          <Button variant="contained" color="success" fullWidth>
            Process Payment
          </Button>
          <Button variant="contained" color="secondary" fullWidth>
            View Reports
          </Button>
        </Stack>
      </Paper>
    </Stack>
  );
};

export default DashboardPage;