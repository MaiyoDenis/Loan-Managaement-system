import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Button,
  Chip,
  TextField,
  InputAdornment,
} from '@mui/material';
import { Search, Add, LocationOn } from '@mui/icons-material';

interface Branch {
  id: number;
  name: string;
  location: string;
  manager_name: string;
  phone_number: string;
  email: string;
  is_active: boolean;
  total_users: number;
}

const BranchesPage: React.FC = () => {
  const [branches, setBranches] = useState<Branch[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    fetchBranches();
  }, [searchTerm]);

  const fetchBranches = async () => {
    try {
      // TODO: Implement API call to fetch branches
      // For now, using mock data
      setBranches([
        {
          id: 1,
          name: 'Main Branch',
          location: 'Nairobi CBD',
          manager_name: 'Jane Smith',
          phone_number: '+254700000001',
          email: 'main@lumitrix.com',
          is_active: true,
          total_users: 25,
        },
        {
          id: 2,
          name: 'Westlands Branch',
          location: 'Westlands',
          manager_name: 'Mike Johnson',
          phone_number: '+254700000002',
          email: 'westlands@lumitrix.com',
          is_active: true,
          total_users: 18,
        },
      ]);
    } catch (error) {
      console.error('Error fetching branches:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <Typography>Loading branches...</Typography>
      </Box>
    );
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" component="h1">
          Branches Management
        </Typography>
        <Button variant="contained" startIcon={<Add />}>
          Add Branch
        </Button>
      </Box>

      <Box mb={3}>
        <TextField
          placeholder="Search branches..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <Search />
              </InputAdornment>
            ),
          }}
          sx={{ minWidth: 300 }}
        />
      </Box>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Branch Name</TableCell>
              <TableCell>Location</TableCell>
              <TableCell>Manager</TableCell>
              <TableCell>Contact</TableCell>
              <TableCell>Users</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {branches.map((branch) => (
              <TableRow key={branch.id}>
                <TableCell>
                  <Box display="flex" alignItems="center">
                    <LocationOn sx={{ mr: 1, color: 'primary.main' }} />
                    {branch.name}
                  </Box>
                </TableCell>
                <TableCell>{branch.location}</TableCell>
                <TableCell>{branch.manager_name}</TableCell>
                <TableCell>
                  <Box>
                    <Typography variant="body2">{branch.phone_number}</Typography>
                    <Typography variant="body2" color="text.secondary">
                      {branch.email}
                    </Typography>
                  </Box>
                </TableCell>
                <TableCell>{branch.total_users}</TableCell>
                <TableCell>
                  <Chip
                    label={branch.is_active ? 'Active' : 'Inactive'}
                    color={branch.is_active ? 'success' : 'error'}
                    size="small"
                  />
                </TableCell>
                <TableCell>
                  <Button size="small" variant="outlined">
                    Edit
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};

export default BranchesPage;
