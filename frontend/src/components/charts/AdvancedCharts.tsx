import React from 'react';
import { Card, CardContent, Typography, Stack, Box } from '@mui/material';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  ArcElement,
  Tooltip,
  Legend,
  type ChartOptions,
} from 'chart.js';
import { Line, Doughnut } from 'react-chartjs-2';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, ArcElement, Tooltip, Legend);

type Props = {
  monthlyLabels?: string[];
  monthlyTotals?: number[];
  statusBreakdown?: { label: string; value: number; color: string }[];
};

const AdvancedCharts: React.FC<Props> = ({
  monthlyLabels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
  monthlyTotals = [120000, 135000, 128000, 142000, 150000, 160000, 158000, 162000, 168000, 172000, 175000, 180000],
  statusBreakdown = [
    { label: 'Active', value: 64, color: '#4caf50' },
    { label: 'Pending', value: 18, color: '#ffb300' },
    { label: 'Overdue', value: 10, color: '#f44336' },
    { label: 'Closed', value: 8, color: '#90caf9' },
  ],
}) => {
  const lineData = {
    labels: monthlyLabels,
    datasets: [
      {
        label: 'Monthly Revenue (KES)',
        data: monthlyTotals,
        borderColor: '#1976d2',
        backgroundColor: 'rgba(25,118,210,0.15)',
        tension: 0.35,
        pointRadius: 4,
        pointHoverRadius: 6,
      },
    ],
  };

  const lineOptions: ChartOptions<'line'> = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
        labels: {
          usePointStyle: true,
          font: { size: 12, weight: 'bold' },
        },
      },
      tooltip: { mode: 'index', intersect: false },
    },
    interaction: { mode: 'nearest', intersect: false },
    scales: {
      x: { grid: { display: false } },
      y: { beginAtZero: true, ticks: { precision: 0 } },
    },
  };

  const doughnutData = {
    labels: statusBreakdown.map((s) => s.label),
    datasets: [
      {
        data: statusBreakdown.map((s) => s.value),
        backgroundColor: statusBreakdown.map((s) => s.color),
        borderWidth: 0,
      },
    ],
  };

  const doughnutOptions: ChartOptions<'doughnut'> = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'bottom',
        labels: {
          usePointStyle: true,
          font: { size: 12, weight: 'bold' },
        },
      },
    },
  };

  return (
    <Stack spacing={3}>
      <Card elevation={1}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Revenue Trend
          </Typography>
          <Box sx={{ height: 320 }}>
            <Line data={lineData} options={lineOptions} />
          </Box>
        </CardContent>
      </Card>

      <Card elevation={1}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Loan Status Breakdown
          </Typography>
          <Box sx={{ height: 260 }}>
            <Doughnut data={doughnutData} options={doughnutOptions} />
          </Box>
        </CardContent>
      </Card>
    </Stack>
  );
};

export default AdvancedCharts;
