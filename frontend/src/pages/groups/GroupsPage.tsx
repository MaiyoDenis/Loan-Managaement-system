import React, { useState, useEffect } from 'react';
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
  CircularProgress,
} from '@mui/material';
import { Add as AddIcon, Edit as EditIcon, Delete as DeleteIcon } from '@mui/icons-material';
import { getGroups } from '../../services/groupService';
import { GroupResponse } from '../../schemas/group';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';

const GroupsPage: React.FC = () => {
  const [groups, setGroups] = useState<GroupResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    fetchGroups();
  }, []);

  const fetchGroups = async () => {
    setLoading(true);
    const groups = await getGroups();
    setGroups(groups);
    setLoading(false);
  };

  const handleViewGroup = (groupId: number) => {
    navigate(`/groups/${groupId}`);
  };

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.5 }}>
      <Container maxWidth="lg">
        <Box sx={{ my: 4 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h4" component="h1" gutterBottom>
              Group Management
            </Typography>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={() => console.log('Create new group')}
            >
              New Group
            </Button>
          </Box>
          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
              <CircularProgress />
            </Box>
          ) : (
            <TableContainer component={Paper}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Name</TableCell>
                    <TableCell>Branch ID</TableCell>
                    <TableCell>Loan Officer ID</TableCell>
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {groups.map((group) => (
                    <TableRow
                      key={group.id}
                      hover
                      onClick={() => handleViewGroup(group.id)}
                      style={{ cursor: 'pointer' }}
                      component={motion.tr}
                      whileHover={{ scale: 1.02 }}
                    >
                      <TableCell>{group.name}</TableCell>
                      <TableCell>{group.branch_id}</TableCell>
                      <TableCell>{group.loan_officer_id}</TableCell>
                      <TableCell>
                        <IconButton onClick={(e) => { e.stopPropagation(); console.log(`Edit group ${group.id}`)}}>
                          <EditIcon />
                        </IconButton>
                        <IconButton onClick={(e) => { e.stopPropagation(); console.log(`Delete group ${group.id}`)}}>
                          <DeleteIcon />
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </Box>
      </Container>
    </motion.div>
  );
};

export default GroupsPage;
