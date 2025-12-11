import React from 'react';
import {
  Alert,
  Box,
  Card,
  CardContent,
  Chip,
  Divider,
  LinearProgress,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';
import { AccountBalance, Payment, PeopleAlt, TrendingDown, TrendingUp } from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import { analyticsAPI } from '../../services/api';

type PaymentEntry = {
  id: number;
  payer_name: string;
  amount: number;
  payment_method: string;
  payment_date: string;
  status?: string;
};

type BranchEntry = {
  name: string;
  total: number;
  growth?: number;
};

type DashboardData = {
  active_loans?: number;
  active_loans_change?: number;
  total_customers?: number;
  total_disbursed?: number;
  delinquency_rate?: number;
  recent_payments?: PaymentEntry[];
  top_branches?: BranchEntry[];
};

const formatNumber = (value: number | undefined) =>
  typeof value === 'number' ? value.toLocaleString() : '0';

const formatCurrency = (value: number | undefined) =>
  typeof value === 'number' ? `$${value.toLocaleString()}` : '$0';

const AdvancedAnalyticsDashboard: React.FC = () => {
  const { data, isLoading, isError } = useQuery<DashboardData>({
    queryKey: ['analytics-dashboard'],
    queryFn: () => analyticsAPI.getAnalytics(),
  });

  const stats = [
    {
      label: 'Active Loans',
      value: data?.active_loans ?? 0,
      delta: data?.active_loans_change ?? 0,
      icon: <AccountBalance color="primary" />,
    },
    {
      label: 'Total Customers',
      value: data?.total_customers ?? 0,
      icon: <PeopleAlt color="info" />,
    },
    {
      label: 'Total Disbursed',
      value: data?.total_disbursed ?? 0,
      icon: <Payment color="success" />,
    },
    {
      label: 'Delinquency Rate',
      value: data?.delinquency_rate ?? 0,
      format: (v: number) => `${v.toFixed(2)}%`,
      icon: <TrendingDown color="warning" />,
    },
  ];

  const recentPayments: PaymentEntry[] = data?.recent_payments ?? [];
  const topBranches: BranchEntry[] = data?.top_branches ?? [];

  return (
    <Box sx={{ p: 3 }}>
      <Stack spacing={3}>
        <Typography variant="h4" component="h1">
          Advanced Analytics
        </Typography>

        {isLoading && <LinearProgress />}
        {isError && <Alert severity="error">Unable to load analytics right now.</Alert>}

        <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
          {stats.map((stat) => (
            <Card key={stat.label} sx={{ flex: 1, minWidth: 220 }}>
              <CardContent>
                <Stack direction="row" spacing={2} alignItems="center" justifyContent="space-between">
                  {stat.icon}
                  <Box>
                    <Typography variant="h6">{stat.label}</Typography>
                    <Typography variant="h4" fontWeight={700}>
                      {stat.format ? stat.format(stat.value as number) : formatNumber(stat.value as number)}
                    </Typography>
                  </Box>
                  {'delta' in stat && typeof stat.delta === 'number' ? (
                    <Chip
                      size="small"
                      color={stat.delta >= 0 ? 'success' : 'error'}
                      icon={stat.delta >= 0 ? <TrendingUp /> : <TrendingDown />}
                      label={`${stat.delta >= 0 ? '+' : ''}${stat.delta.toFixed(1)}%`}
                    />
                  ) : null}
                </Stack>
              </CardContent>
            </Card>
          ))}
        </Stack>

        <Card>
          <CardContent>
            <Stack direction="row" justifyContent="space-between" alignItems="center" mb={1}>
              <Typography variant="h6">Recent Payments</Typography>
              <Chip label={`${recentPayments.length} records`} size="small" />
            </Stack>
            <Divider sx={{ mb: 2 }} />
            {recentPayments.length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                No payment data available yet.
              </Typography>
            ) : (
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Customer</TableCell>
                    <TableCell>Amount</TableCell>
                    <TableCell>Method</TableCell>
                    <TableCell>Date</TableCell>
                    <TableCell>Status</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {recentPayments.map((payment) => (
                    <TableRow key={payment.id} hover>
                      <TableCell>{payment.payer_name}</TableCell>
                      <TableCell>{formatCurrency(payment.amount)}</TableCell>
                      <TableCell>{payment.payment_method}</TableCell>
                      <TableCell>{payment.payment_date}</TableCell>
                      <TableCell>
                        <Chip
                          size="small"
                          color={payment.status === 'confirmed' ? 'success' : payment.status === 'pending' ? 'warning' : 'default'}
                          label={payment.status ?? 'n/a'}
                        />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardContent>
            <Stack direction="row" justifyContent="space-between" alignItems="center" mb={1}>
              <Typography variant="h6">Top Branches</Typography>
              <Chip label={`${topBranches.length} branches`} size="small" />
            </Stack>
            <Divider sx={{ mb: 2 }} />
            {topBranches.length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                No branch performance data yet.
              </Typography>
            ) : (
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Branch</TableCell>
                    <TableCell align="right">Total</TableCell>
                    <TableCell align="right">Growth</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {topBranches.map((branch) => (
                    <TableRow key={branch.name} hover>
                      <TableCell>{branch.name}</TableCell>
                      <TableCell align="right">{formatCurrency(branch.total)}</TableCell>
                      <TableCell align="right">
                        {branch.growth !== undefined ? (
                          <Chip
                            size="small"
                            color={branch.growth >= 0 ? 'success' : 'error'}
                            icon={branch.growth >= 0 ? <TrendingUp /> : <TrendingDown />}
                            label={`${branch.growth >= 0 ? '+' : ''}${branch.growth.toFixed(1)}%`}
                          />
                        ) : (
                          '--'
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </Stack>
    </Box>
  );
};

export default AdvancedAnalyticsDashboard;
