import React, { useState } from 'react';
import {
  Box,
  Typography,
  Tab,
  Tabs,
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
  Alert,
  Grid,
  Card,
  CardContent
} from '@mui/material';
import {
  AccountBalance,
  TrendingUp,
  SwapHoriz,
  Add as AddIcon,
  Search as SearchIcon,
  Download as DownloadIcon
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { toast } from 'react-toastify';

import { accountsAPI } from '../../services/api';
import { useAuth } from '../../contexts/AuthContext';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`accounts-tabpanel-${index}`}
      aria-labelledby={`accounts-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  );
}

const AccountsPage: React.FC = () => {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  
  // State
  const [tabValue, setTabValue] = useState(0);
  const [transferDialog, setTransferDialog] = useState(false);
  const [depositDialog, setDepositDialog] = useState(false);
  const [selectedAccount, setSelectedAccount] = useState<any>(null);
  const [transferForm, setTransferForm] = useState({
    user_id: '',
    from_account: 'savings',
    to_account: 'drawdown',
    amount: '',
    description: ''
  });
  const [depositForm, setDepositForm] = useState({
    user_id: '',
    account_type: 'savings',
    amount: '',
    payment_method: 'cash',
    reference_number: '',
    description: ''
  });

  // Queries
  const { data: savingsAccounts = [], isLoading: savingsLoading } = useQuery(
    ['savings-accounts', user?.branch_id],
    () => accountsAPI.getSavingsAccounts(user?.branch_id),
    { enabled: !!user }
  );

  const { data: drawdownAccounts = [], isLoading: drawdownLoading } = useQuery(
    ['drawdown-accounts', user?.branch_id],
    () => accountsAPI.getDrawdownAccounts(user?.branch_id),
    { enabled: !!user }
  );

  // Mutations
  const transferMutation = useMutation(
    (data: any) => accountsAPI.transferFunds(data),
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['savings-accounts']);
        queryClient.invalidateQueries(['drawdown-accounts']);
        toast.success('Transfer completed successfully!');
        setTransferDialog(false);
      },
      onError: (error: any) => {
        toast.error(error.response?.data?.detail || 'Transfer failed');
      }
    }
  );

  const depositMutation = useMutation(
    (data: any) => accountsAPI.depositFunds(data),
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['savings-accounts']);
        queryClient.invalidateQueries(['drawdown-accounts']);
        toast.success('Deposit recorded successfully!');
        setDepositDialog(false);
      },
      onError: (error: any) => {
        toast.error(error.response?.data?.detail || 'Deposit failed');
      }
    }
  );

  // Event handlers
  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleTransferSubmit = () => {
    if (!transferForm.user_id || !transferForm.amount) {
      toast.error('Please fill in all required fields');
      return;
    }

    transferMutation.mutate({
      user_id: parseInt(transferForm.user_id),
      from_account: transferForm.from_account,
      to_account: transferForm.to_account,
      amount: parseFloat(transferForm.amount),
      description: transferForm.description
    });
  };

  const handleDepositSubmit = () => {
    if (!depositForm.user_id || !depositForm.amount) {
      toast.error('Please fill in all required fields');
      return;
    }

    depositMutation.mutate({
      user_id: parseInt(depositForm.user_id),
      account_type: depositForm.account_type,
      amount: parseFloat(depositForm.amount),
      payment_method: depositForm.payment_method,
      reference_number: depositForm.reference_number,
      description: depositForm.description
    });
  };

  const getAccountStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'success';
      case 'pending': return 'warning';
      case 'suspended': return 'error';
      default: return 'default';
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          Account Management
        </Typography>
        
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            variant="outlined"
            startIcon={<SwapHoriz />}
            onClick={() => setTransferDialog(true)}
            disabled={user?.role === 'customer'}
          >
            Transfer Funds
          </Button>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setDepositDialog(true)}
            disabled={user?.role === 'customer'}
          >
            Record Deposit
          </Button>
        </Box>
      </Box>

      {/* Account Summary Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <AccountBalance color="primary" />
                <Box>
                  <Typography variant="h6">
                    ${savingsAccounts.reduce((sum: number, acc: any) => sum + acc.balance, 0).toLocaleString()}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Total Savings
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <TrendingUp color="info" />
                <Box>
                  <Typography variant="h6">
                    ${drawdownAccounts.reduce((sum: number, acc: any) => sum + acc.balance, 0).toLocaleString()}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Total Drawdown
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <AddIcon color="success" />
                <Box>
                  <Typography variant="h6">
                    {savingsAccounts.filter((acc: any) => acc.status === 'active').length}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Active Accounts
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Tabs */}
      <Paper sx={{ width: '100%' }}>
        <Tabs value={tabValue} onChange={handleTabChange} sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tab label="Savings Accounts" />
          <Tab label="Drawdown Accounts" />
          <Tab label="Transactions" />
        </Tabs>

        {/* Savings Accounts Tab */}
        <TabPanel value={tabValue} index={0}>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Account Number</TableCell>
                  <TableCell>Customer</TableCell>
                  <TableCell>Phone</TableCell>
                  <TableCell>Balance</TableCell>
                  <TableCell>Loan Limit</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Registration</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {savingsAccounts.map((account: any) => (
                  <TableRow key={account.id}>
                    <TableCell>{account.account_number}</TableCell>
                    <TableCell>{account.user_name}</TableCell>
                    <TableCell>{account.user_phone}</TableCell>
                    <TableCell>
                      <Typography
                        color={account.balance >= 0 ? 'success.main' : 'error.main'}
                        fontWeight="bold"
                      >
                        ${account.balance.toLocaleString()}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography color="primary">
                        ${account.loan_limit?.toLocaleString()}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={account.status}
                        color={getAccountStatusColor(account.status)}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={account.registration_fee_paid ? 'Paid' : 'Pending'}
                        color={account.registration_fee_paid ? 'success' : 'warning'}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      <IconButton
                        size="small"
                        onClick={() => {/* TODO: View account details */}}
                      >
                        <SearchIcon />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </TabPanel>

        {/* Drawdown Accounts Tab */}
        <TabPanel value={tabValue} index={1}>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Account Number</TableCell>
                  <TableCell>Customer</TableCell>
                  <TableCell>Phone</TableCell>
                  <TableCell>Balance</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {drawdownAccounts.map((account: any) => (
                  <TableRow key={account.id}>
                    <TableCell>{account.account_number}</TableCell>
                    <TableCell>{account.user_name}</TableCell>
                    <TableCell>{account.user_phone}</TableCell>
                    <TableCell>
                      <Typography
                        color={account.balance >= 0 ? 'success.main' : 'error.main'}
                        fontWeight="bold"
                      >
                        ${account.balance.toLocaleString()}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <IconButton
                        size="small"
                        onClick={() => {/* TODO: View account details */}}
                      >
                        <SearchIcon />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </TabPanel>

        {/* Transactions Tab */}
        <TabPanel value={tabValue} index={2}>
          <Typography variant="body1">
            Transaction history will be implemented in Phase 3
          </Typography>
        </TabPanel>
      </Paper>

      {/* Transfer Dialog */}
      <Dialog open={transferDialog} onClose={() => setTransferDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Transfer Funds</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
            <TextField
              label="User ID"
              type="number"
              value={transferForm.user_id}
              onChange={(e) => setTransferForm(prev => ({ ...prev, user_id: e.target.value }))}
              fullWidth
              required
            />
            
            <Grid container spacing={2}>
              <Grid item xs={6}>
                <FormControl fullWidth>
                  <InputLabel>From Account</InputLabel>
                  <Select
                    value={transferForm.from_account}
                    onChange={(e) => setTransferForm(prev => ({ ...prev, from_account: e.target.value }))}
                    label="From Account"
                  >
                    <MenuItem value="savings">Savings</MenuItem>
                    <MenuItem value="drawdown">Drawdown</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              
              <Grid item xs={6}>
                <FormControl fullWidth>
                  <InputLabel>To Account</InputLabel>
                  <Select
                    value={transferForm.to_account}
                    onChange={(e) => setTransferForm(prev => ({ ...prev, to_account: e.target.value }))}
                    label="To Account"
                  >
                    <MenuItem value="savings">Savings</MenuItem>
                    <MenuItem value="drawdown">Drawdown</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
            </Grid>
            
            <TextField
              label="Amount"
              type="number"
              value={transferForm.amount}
              onChange={(e) => setTransferForm(prev => ({ ...prev, amount: e.target.value }))}
              fullWidth
              required
              InputProps={{ startAdornment: '$' }}
            />
            
            <TextField
              label="Description"
              value={transferForm.description}
              onChange={(e) => setTransferForm(prev => ({ ...prev, description: e.target.value }))}
              fullWidth
              multiline
              rows={2}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setTransferDialog(false)}>Cancel</Button>
          <Button 
            onClick={handleTransferSubmit}
            variant="contained"
            disabled={transferMutation.isLoading}
          >
            Transfer
          </Button>
        </DialogActions>
      </Dialog>

      {/* Deposit Dialog */}
      <Dialog open={depositDialog} onClose={() => setDepositDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Record Deposit</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
            <TextField
              label="User ID"
              type="number"
              value={depositForm.user_id}
              onChange={(e) => setDepositForm(prev => ({ ...prev, user_id: e.target.value }))}
              fullWidth
              required
            />
            
            <Grid container spacing={2}>
              <Grid item xs={6}>
                <FormControl fullWidth>
                  <InputLabel>Account Type</InputLabel>
                  <Select
                    value={depositForm.account_type}
                    onChange={(e) => setDepositForm(prev => ({ ...prev, account_type: e.target.value }))}
                    label="Account Type"
                  >
                    <MenuItem value="savings">Savings</MenuItem>
                    <MenuItem value="drawdown">Drawdown</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              
              <Grid item xs={6}>
                <FormControl fullWidth>
                  <InputLabel>Payment Method</InputLabel>
                  <Select
                    value={depositForm.payment_method}
                    onChange={(e) => setDepositForm(prev => ({ ...prev, payment_method: e.target.value }))}
                    label="Payment Method"
                  >
                    <MenuItem value="cash">Cash</MenuItem>
                    <MenuItem value="mpesa">M-Pesa</MenuItem>
                    <MenuItem value="bank_transfer">Bank Transfer</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
            </Grid>
            
            <TextField
              label="Amount"
              type="number"
              value={depositForm.amount}
              onChange={(e) => setDepositForm(prev => ({ ...prev, amount: e.target.value }))}
              fullWidth
              required
              InputProps={{ startAdornment: '$' }}
            />
            
            {depositForm.payment_method === 'mpesa' && (
              <TextField
                label="M-Pesa Transaction Code"
                value={depositForm.reference_number}
                onChange={(e) => setDepositForm(prev => ({ ...prev, reference_number: e.target.value }))}
                fullWidth
                required
              />
            )}
            
            <TextField
              label="Description"
              value={depositForm.description}
              onChange={(e) => setDepositForm(prev => ({ ...prev, description: e.target.value }))}
              fullWidth
              multiline
              rows={2}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDepositDialog(false)}>Cancel</Button>
          <Button 
            onClick={handleDepositSubmit}
            variant="contained"
            disabled={depositMutation.isLoading}
          >
            Record Deposit
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default AccountsPage;