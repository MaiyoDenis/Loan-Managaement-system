import React, { useState } from 'react';
import {
  Box,
  Button,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Alert,
  Chip,
  Stack,
  TablePagination,
} from '@mui/material';
import { Add as AddIcon, Edit as EditIcon, Delete as DeleteIcon } from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import { branchesAPI } from '../../services/api';
import { useApiError } from '../../hooks/useApiError';
import TableSkeleton from '../../components/common/TableSkeleton';

interface Branch {
  id: number;
  name: string;
  code: string;
  manager_id: number;
  procurement_officer_id: number;
  is_active: boolean;
}

const BranchesPage: React.FC = () => {
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const { showError } = useApiError();

  const { data: branches = [], isLoading, error } = useQuery({
    queryKey: ['branches'],
    queryFn: () => branchesAPI.getBranches(),
    retry: 1,
  });

  React.useEffect(() => {
    if (error) {
      showError(error as Error);
    }
  }, [error, showError]);

  const handleChangePage = (_event: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  // Paginate branches
  const paginatedBranches = branches.slice(
    page * rowsPerPage,
    page * rowsPerPage + rowsPerPage
  );

  if (isLoading) {
    return (
      <Stack spacing={3}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h4" component="h1">Branch Management</Typography>
        </Box>
        <TableSkeleton rows={10} columns={6} />
      </Stack>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 2 }}>
        Failed to load branches. Please try again later.
      </Alert>
    );
  }

  return (
    <Stack spacing={3}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h4" component="h1">
          Branch Management
        </Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => {
            // TODO: Implement create branch dialog
          }}
        >
          New Branch
        </Button>
      </Box>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>Code</TableCell>
              <TableCell>Manager ID</TableCell>
              <TableCell>Procurement Officer ID</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {branches.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} align="center">
                  <Typography variant="body2" color="text.secondary" sx={{ py: 4 }}>
                    No branches found
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              paginatedBranches.map((branch: Branch) => (
                <TableRow key={branch.id} hover>
                  <TableCell>{branch.name}</TableCell>
                  <TableCell>{branch.code}</TableCell>
                  <TableCell>{branch.manager_id}</TableCell>
                  <TableCell>{branch.procurement_officer_id}</TableCell>
                  <TableCell>
                    <Chip
                      label={branch.is_active ? 'Active' : 'Inactive'}
                      color={branch.is_active ? 'success' : 'error'}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    <IconButton
                      size="small"
                      onClick={() => {
                        // TODO: Implement edit branch
                      }}
                      aria-label={`Edit ${branch.name}`}
                    >
                      <EditIcon fontSize="small" />
                    </IconButton>
                    <IconButton
                      size="small"
                      onClick={() => {
                        // TODO: Implement delete branch
                      }}
                      aria-label={`Delete ${branch.name}`}
                    >
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
        <TablePagination
          rowsPerPageOptions={[5, 10, 25, 50]}
          component="div"
          count={branches.length}
          rowsPerPage={rowsPerPage}
          page={page}
          onPageChange={handleChangePage}
          onRowsPerPageChange={handleChangeRowsPerPage}
        />
      </TableContainer>
    </Stack>
  );
};

export default BranchesPage;