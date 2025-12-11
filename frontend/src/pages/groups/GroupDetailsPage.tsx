import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
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
import { getGroup } from '../../services/groupService';
import { getGroupMembers, createCustomer } from '../../services/userService';
import type { GroupResponse } from '../../schemas/group';
import type { UserResponse, CustomerCreate } from '../../schemas/user';
import { motion } from 'framer-motion';
import CustomerForm from './CustomerForm';

const GroupDetailsPage: React.FC = () => {
  const { groupId } = useParams<{ groupId: string }>();
  const [group, setGroup] = useState<GroupResponse | null>(null);
  const [members, setMembers] = useState<UserResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (groupId) {
      fetchGroupDetails(parseInt(groupId));
    }
  }, [groupId]);

  const fetchGroupDetails = async (id: number) => {
    setLoading(true);
    const [groupData, membersData] = await Promise.all([
      getGroup(id),
      getGroupMembers(id),
    ]);
    setGroup(groupData);
    setMembers(membersData);
    setLoading(false);
  };

  const handleOpen = () => {
    setOpen(true);
  };

  const handleClose = () => {
    setOpen(false);
  };

  const handleSubmit = async (customerData: CustomerCreate) => {
    await createCustomer(customerData);
    if (groupId) {
      fetchGroupDetails(parseInt(groupId));
    }
    handleClose();
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (!group) {
    return (
      <Container maxWidth="lg">
        <Typography variant="h4" component="h1" gutterBottom>
          Group not found
        </Typography>
      </Container>
    );
  }

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.5 }}>
      <Container maxWidth="lg">
        <Box sx={{ my: 4 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h4" component="h1" gutterBottom>
              {group.name}
            </Typography>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={handleOpen}
            >
              Add Member
            </Button>
          </Box>
          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Name</TableCell>
                  <TableCell>Phone Number</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {members.map((member) => (
                  <TableRow
                    key={member.id}
                    hover
                    component={motion.tr}
                    whileHover={{ scale: 1.02 }}
                  >
                    <TableCell>{member.first_name} {member.last_name}</TableCell>
                    <TableCell>{member.phone_number}</TableCell>
                    <TableCell>
                      <IconButton 
                        onClick={() => {
                          // TODO: Implement edit member
                        }}
                        aria-label={`Edit ${member.first_name} ${member.last_name}`}
                      >
                        <EditIcon />
                      </IconButton>
                      <IconButton 
                        onClick={() => {
                          // TODO: Implement delete member
                        }}
                        aria-label={`Delete ${member.first_name} ${member.last_name}`}
                      >
                        <DeleteIcon />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
          <CustomerForm
            open={open}
            onClose={handleClose}
            onSubmit={handleSubmit}
            groupId={parseInt(groupId!)}
          />
        </Box>
      </Container>
    </motion.div>
  );
};

export default GroupDetailsPage;
