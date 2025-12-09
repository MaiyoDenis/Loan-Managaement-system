import React from 'react';
import {
  Box,
  Button,
  Container,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
} from '@mui/material';
import { Add as AddIcon, Edit as EditIcon, Delete as DeleteIcon } from '@mui/icons-material';

const placeholderBranches = [
  { id: 1, name: 'Main Branch', code: 'MAIN', manager_id: 2, procurement_officer_id: 3, is_active: true },
  { id: 2, name: 'Second Branch', code: 'SEC', manager_id: 4, procurement_officer_id: 5, is_active: true },
];

const BranchesPage: React.FC = () => {
  return (
    <Container maxWidth="lg">
      <Box sx={{ my: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h4" component="h1" gutterBottom>
            Branch Management
          </Typography>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => console.log('Create new branch')}
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
              {placeholderBranches.map((branch) => (
                <TableRow key={branch.id}>
                  <TableCell>{branch.name}</TableCell>
                  <TableCell>{branch.code}</TableCell>
                  <TableCell>{branch.manager_id}</TableCell>
                  <TableCell>{branch.procurement_officer_id}</TableCell>
                  <TableCell>{branch.is_active ? 'Active' : 'Inactive'}</TableCell>
                  <TableCell>
                    <IconButton onClick={() => console.log(`Edit branch ${branch.id}`)}>
                      <EditIcon />
                    </IconButton>
                    <IconButton onClick={() => console.log(`Delete branch ${branch.id}`)}>
                      <DeleteIcon />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Box>
    </Container>
  );
};

export default BranchesPage;
