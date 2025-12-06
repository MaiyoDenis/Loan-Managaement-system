import React, { useState } from 'react';
import {
  Box,
  Typography,
  Tabs,
  Tab,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  IconButton,
  Grid,
  Card,
  CardContent,
  Alert,
  CircularProgress
} from '@mui/material';
import {
  Payment as PaymentIcon,
  CheckCircle,
  Cancel,
  Pending,
  PhoneAndroid,
  MonetizationOn,
  TrendingUp,
  Warning
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { toast } from 'react-toastify';

import { paymentsAPI, mpesaAPI } from '../../services/api';
import { useAuth } from '../../contexts/AuthContext';

const PaymentsPage: React.FC = () => {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  
  const [tabValue, setTabValue] = useState(0);
  const [mpesaDialog, setMpesaDialog] = useState(false);
  const [manualPaymentDialog, setManualPaymentDialog] = useState(false);
  const [selectedLoan, setSelectedLoan] = useState<any>(null);
  
  const [mpesaForm, setMpesaForm] = useState({
    phone_number: '',
    amount: '',
    loan_id: ''
  });
  
  const [manualForm, setManualForm] = useState({
    loan_id: '',
    amount: '',
    payment_method: 'cash',
    mpesa_code: '',
    payment_date: new Date().toISOString().split('T')[0],
    notes: ''
  });

  // Queries
  const { data: payments = [], isLoading: paymentsLoading } = useQuery(
    ['payments', user?.branch_id],
    () => paymentsAPI.getPayments({ branch_id: user?.branch_id }),
    { refetchInterval: 30000 }
  );

  const { data: pendingPayments = [] } = useQuery(
    ['pending-payments'],
    () => paymentsAPI.getPendingPayments(),
    { 
      enabled: user?.role === 'procurement_officer' || user?.role === 'admin',
      refetchInterval: 15000 
    }
  );

  const { data: paymentStats } = useQuery(
    ['payment-stats', user?.branch_id],
    () => paymentsAPI.getPaymentStats({ branch_id: user?.branch_id }),
    { refetchInterval: 60000 }
  );

  const { data: mpesaTransactions = [] } = useQuery(
    ['mpesa-transactions'],
    () => paymentsAPI.getMpesaTransactions(),
    { refetchInterval: 30000 }
  );

  // Mutations
  const initiateMpesaMutation = useMutation(
    (data: any) => mpesaAPI.initiatePayment(data),
    {
      onSuccess: (data) => {
        if (data.success) {
          toast.success('M-Pesa payment request sent to customer phone!');
          setMpesaDialog(false);
          queryClient.invalidateQueries(['mpesa-transactions']);
        } else {
          toast.error(data.message || 'Failed to initiate M-Pesa payment');
        }
      },
      onError: (error: any) => {
        toast.error(error.response?.data?.detail || 'Failed to initiate payment');
      }
    }
  );

  const createManualPaymentMutation = useMutation(
    (data: any) => paymentsAPI.createManualPayment(data),
    {
      onSuccess: () => {
        toast.success('Manual payment recorded successfully! Waiting for approval.');
        setManualPaymentDialog(false);
        queryClient.invalidateQueries(['payments']);
        queryClient.invalidateQueries(['pending-payments']);
      },
      onError: (error: any) => {
        toast.error(error.response?.data?.detail || 'Failed to record payment');
      }
    }
  );

  const confirmPaymentMutation = useMutation(
    (paymentId: number) => paymentsAPI.confirmPayment(paymentId),
    {
      onSuccess: () => {
        toast.success('Payment confirmed successfully!');
        queryClient.invalidateQueries(['payments']);
        queryClient.invalidateQueries(['pending-payments']);
      },
      onError: (error: any) => {
        toast.error(error.response?.data?.detail || 'Failed to confirm payment');
      }
    }
  );

  // Event handlers
  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleInitiateMpesa = () => {
    if (!mpesaForm.phone_number || !mpesaForm.amount || !mpesaForm.loan_id) {
      toast.error('Please fill in all required fields');
      return;
    }

    initiateMpesaMutation.mutate({
      phone_number: mpesaForm.phone_number,
      amount: parseFloat(mpesaForm.amount),
      loan_id: parseInt(mpesaForm.loan_id)
    });
  };

  const handleManualPayment = () => {
    if (!manualForm.loan_id || !manualForm.amount) {
      toast.error('Please fill in all required fields');
      return;
    }

    createManualPaymentMutation.mutate({
      loan_id: parseInt(manualForm.loan_id),
      amount: parseFloat(manualForm.amount),
      payment_method: manualForm.payment_method,
      mpesa_code: manualForm.mpesa_code,
      payment_date: manualForm.payment_date,
      notes: manualForm.notes
    });
  };

  const getPaymentStatusColor = (status: string) => {
    switch (status) {
      case 'confirmed': return 'success';
      case 'pending': return 'warning';
      case 'rejected': return 'error';
      default: return 'default';
    }
  };

  const getPaymentMethodIcon = (method: string) => {
    switch (method) {
      case 'mpesa': return <PhoneAndroid />;
      case 'cash': return <MonetizationOn />;
      case 'drawdown_auto': return <TrendingUp />;
      default: return <PaymentIcon />;
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          Payment Management
        </Typography>
        
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            variant="outlined"
            startIcon={<PhoneAndroid />}
            onClick={() => setMpesaDialog(true)}
            disabled={user?.role === 'customer'}
          >
            M-Pesa Payment
          </Button>
          <Button
            variant="contained"
            startIcon={<PaymentIcon />}
            onClick={() => setManualPaymentDialog(true)}
            disabled={user?.role === 'customer'}
          >
            Record Payment
          </Button>
        </Box>
      </Box>

      {/* Payment Statistics Cards */}
      {paymentStats && (
        <Grid container spacing={3} sx={{ mb: 3 }}>
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                  <PaymentIcon color="primary" fontSize="large" />
                  <Box>
                    <Typography variant="h5">
                      {paymentStats.total_payments}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Total Payments
                    </Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>
          
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                  <MonetizationOn color="success" fontSize="large" />
                  <Box>
                    <Typography variant="h5">
                      ${paymentStats.total_amount.toLocaleString()}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Total Amount
                    </Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>
          
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                  <TrendingUp color="info" fontSize="large" />
                  <Box>
                    <Typography variant="h5">
                      ${paymentStats.average_payment.toFixed(0)}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Average Payment
                    </Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>
          
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                  <Warning color="warning" fontSize="large" />
                  <Box>
                    <Typography variant="h5">
                      {pendingPayments.length}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Pending Approval
                    </Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Tabs */}
      <Paper sx={{ width: '100%' }}>
        <Tabs value={tabValue} onChange={handleTabChange}>
          <Tab label="All Payments" />
          <Tab label="Pending Approval" />
          <Tab label="M-Pesa Transactions" />
          <Tab label="Payment Analytics" />
        </Tabs>

        {/* All Payments Tab */}
        <TabPanel value={tabValue} index={0}>
          {paymentsLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
              <CircularProgress />
            </Box>
          ) : (
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Payment #</TableCell>
                    <TableCell>Customer</TableCell>
                    <TableCell>Loan #</TableCell>
                    <TableCell>Amount</TableCell>
                    <TableCell>Method</TableCell>
                    <TableCell>Date</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {payments.map((payment: any) => (
                    <TableRow key={payment.id}>
                      <TableCell>{payment.payment_number}</TableCell>
                      <TableCell>{payment.payer_name}</TableCell>
                      <TableCell>{payment.loan_number}</TableCell>
                      <TableCell>
                        <Typography fontWeight="bold" color="success.main">
                          ${payment.amount.toLocaleString()}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          {getPaymentMethodIcon(payment.payment_method)}
                          {payment.payment_method.toUpperCase()}
                        </Box>
                      </TableCell>
                      <TableCell>{payment.payment_date}</TableCell>
                      <TableCell>
                        <Chip
                          label={payment.status}
                          color={getPaymentStatusColor(payment.status)}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>
                        {payment.status === 'pending' && (user?.role === 'procurement_officer' || user?.role === 'admin') && (
                          <Button
                            size="small"
                            variant="contained"
                            color="success"
                            onClick={() => confirmPaymentMutation.mutate(payment.id)}
                          >
                            Confirm
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </TabPanel>

        {/* Pending Approval Tab */}
        <TabPanel value={tabValue} index={1}>
          {(user?.role === 'procurement_officer' || user?.role === 'admin') ? (
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Payment #</TableCell>
                    <TableCell>Customer</TableCell>
                    <TableCell>Loan #</TableCell>
                    <TableCell>Amount</TableCell>
                    <TableCell>Method</TableCell>
                    <TableCell>M-Pesa Code</TableCell>
                    <TableCell>Created By</TableCell>
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {pendingPayments.map((payment: any) => (
                    <TableRow key={payment.id}>
                      <TableCell>{payment.payment_number}</TableCell>
                      <TableCell>{payment.payer_name}</TableCell>
                      <TableCell>{payment.loan_number}</TableCell>
                      <TableCell>
                        <Typography fontWeight="bold">
                          ${payment.amount.toLocaleString()}
                        </Typography>
                      </TableCell>
                      <TableCell>{payment.payment_method}</TableCell>
                      <TableCell>{payment.mpesa_transaction_code || '-'}</TableCell>
                      <TableCell>{payment.created_by_name}</TableCell>
                      <TableCell>
                        <Box sx={{ display: 'flex', gap: 1 }}>
                          <Button
                            size="small"
                            variant="contained"
                            color="success"
                            startIcon={<CheckCircle />}
                            onClick={() => confirmPaymentMutation.mutate(payment.id)}
                          >
                            Confirm
                          </Button>
                          <Button
                            size="small"
                            variant="outlined"
                            color="error"
                            startIcon={<Cancel />}
                            onClick={() => {/* TODO: Reject payment */}}
                          >
                            Reject
                          </Button>
                        </Box>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          ) : (
            <Alert severity="info">
              Only procurement officers can approve payments.
            </Alert>
          )}
        </TabPanel>

        {/* M-Pesa Transactions Tab */}
        <TabPanel value={tabValue} index={2}>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Transaction Code</TableCell>
                  <TableCell>Phone Number</TableCell>
                  <TableCell>Account Number</TableCell>
                  <TableCell>Amount</TableCell>
                  <TableCell>Time</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Processed</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {mpesaTransactions.map((transaction: any) => (
                  <TableRow key={transaction.id}>
                    <TableCell>{transaction.transaction_code}</TableCell>
                    <TableCell>{transaction.phone_number}</TableCell>
                    <TableCell>{transaction.account_number}</TableCell>
                    <TableCell>
                      <Typography fontWeight="bold" color="success.main">
                        ${transaction.amount.toLocaleString()}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      {new Date(transaction.transaction_time).toLocaleString()}
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={transaction.status}
                        color={transaction.status === 'confirmed' ? 'success' : 'warning'}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={transaction.processed ? 'Yes' : 'No'}
                        color={transaction.processed ? 'success' : 'error'}
                        size="small"
                      />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </TabPanel>

        {/* Analytics Tab */}
        <TabPanel value={tabValue} index={3}>
          <Typography variant="h6" gutterBottom>
            Payment Analytics Dashboard
          </Typography>
          <Typography variant="body1">
            Advanced analytics will be implemented with charts and forecasting.
          </Typography>
        </TabPanel>
      </Paper>

      {/* M-Pesa Payment Dialog */}
      <Dialog open={mpesaDialog} onClose={() => setMpesaDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Initiate M-Pesa Payment</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
            <TextField
              label="Customer Phone Number"
              value={mpesaForm.phone_number}
              onChange={(e) => setMpesaForm(prev => ({ ...prev, phone_number: e.target.value }))}
              fullWidth
              required
              placeholder="+254700000000"
            />
            
            <TextField
              label="Loan ID"
              type="number"
              value={mpesaForm.loan_id}
              onChange={(e) => setMpesaForm(prev => ({ ...prev, loan_id: e.target.value }))}
              fullWidth
              required
            />
            
            <TextField
              label="Amount"
              type="number"
              value={mpesaForm.amount}
              onChange={(e) => setMpesaForm(prev => ({ ...prev, amount: e.target.value }))}
              fullWidth
              required
              InputProps={{ startAdornment: 'KES ' }}
            />
            
            <Alert severity="info">
              Customer will receive M-Pesa prompt on their phone to complete payment.
            </Alert>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setMpesaDialog(false)}>Cancel</Button>
          <Button 
            onClick={handleInitiateMpesa}
            variant="contained"
            disabled={initiateMpesaMutation.isLoading}
            startIcon={initiateMpesaMutation.isLoading ? <CircularProgress size={20} /> : <PhoneAndroid />}
          >
            Send M-Pesa Request
          </Button>
        </DialogActions>
      </Dialog>

      {/* Manual Payment Dialog */}
      <Dialog open={manualPaymentDialog} onClose={() => setManualPaymentDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>Record Manual Payment</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
            <Grid container spacing={2}>
              <Grid item xs={6}>
                <TextField
                  label="Loan ID"
                  type="number"
                  value={manualForm.loan_id}
                  onChange={(e) => setManualForm(prev => ({ ...prev, loan_id: e.target.value }))}
                  fullWidth
                  required
                />
              </Grid>
              
              <Grid item xs={6}>
                <TextField
                  label="Amount"
                  type="number"
                  value={manualForm.amount}
                  onChange={(e) => setManualForm(prev => ({ ...prev, amount: e.target.value }))}
                  fullWidth
                  required
                  InputProps={{ startAdornment: 'KES ' }}
                />
              </Grid>
            </Grid>
            
            <Grid container spacing={2}>
              <Grid item xs={6}>
                <FormControl fullWidth>
                  <InputLabel>Payment Method</InputLabel>
                  <Select
                    value={manualForm.payment_method}
                    onChange={(e) => setManualForm(prev => ({ ...prev, payment_method: e.target.value }))}
                    label="Payment Method"
                  >
                    <MenuItem value="cash">Cash</MenuItem>
                    <MenuItem value="mpesa">M-Pesa</MenuItem>
                    <MenuItem value="bank_transfer">Bank Transfer</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              
              <Grid item xs={6}>
                <TextField
                  label="Payment Date"
                  type="date"
                  value={manualForm.payment_date}
                  onChange={(e) => setManualForm(prev => ({ ...prev, payment_date: e.target.value }))}
                  fullWidth
                  InputLabelProps={{ shrink: true }}
                />
              </Grid>
            </Grid>
            
            {manualForm.payment_method === 'mpesa' && (
              <TextField
                label="M-Pesa Transaction Code"
                value={manualForm.mpesa_code}
                onChange={(e) => setManualForm(prev => ({ ...prev, mpesa_code: e.target.value }))}
                fullWidth
                required
                placeholder="e.g., QA1B2C3D4E"
              />
            )}
            
            <TextField
              label="Notes"
              value={manualForm.notes}
              onChange={(e) => setManualForm(prev => ({ ...prev, notes: e.target.value }))}
              fullWidth
              multiline
              rows={3}
              placeholder="Additional payment details..."
            />
            
            <Alert severity="warning">
              Manual payments require approval from procurement officer before being processed.
            </Alert>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setManualPaymentDialog(false)}>Cancel</Button>
          <Button 
            onClick={handleManualPayment}
            variant="contained"
            disabled={createManualPaymentMutation.isLoading}
          >
            Record Payment
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

// TabPanel component
function TabPanel(props: any) {
  const { children, value, index, ...other } = props;
  return (
    <div role="tabpanel" hidden={value !== index} {...other}>
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

export default PaymentsPage;