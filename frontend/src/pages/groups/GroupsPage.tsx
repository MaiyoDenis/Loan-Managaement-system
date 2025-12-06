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
import { Search, Add, Group } from '@mui/icons-material';

interface Group {
  id: number;
  name: string;
  loan_officer: string;
  branch: string;
  meeting_day: string;
  meeting_time: string;
  total_members: number;
  is_active: boolean;
}

const GroupsPage: React.FC = () => {
  const [groups, setGroups] = useState<Group[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    fetchGroups();
  }, [searchTerm]);

  const fetchGroups = async () => {
    try {
      // TODO: Implement API call to fetch groups
      // For now, using mock data
      setGroups([
        {
          id: 1,
          name: 'Hope Group',
          loan_officer: 'John Doe',
          branch: 'Main Branch',
          meeting_day: 'Monday',
          meeting_time: '2:00 PM',
          total_members: 15,
          is_active: true,
        },
        {
          id: 2,
          name: 'Unity Group',
          loan_officer: 'Jane Smith',
          branch: 'Westlands Branch',
          meeting_day: 'Wednesday',
          meeting_time: '4:00 PM',
          total_members: 12,
          is_active: true,
        },
      ]);
    } catch (error) {
      console.error('Error fetching groups:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <Typography>Loading groups...</Typography>
      </Box>
    );
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" component="h1">
          Groups Management
        </Typography>
        <Button variant="contained" startIcon={<Add />}>
          Add Group
        </Button>
      </Box>

      <Box mb={3}>
        <TextField
          placeholder="Search groups..."
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
              <TableCell>Group Name</TableCell>
              <TableCell>Loan Officer</TableCell>
              <TableCell>Branch</TableCell>
              <TableCell>Meeting Schedule</TableCell>
              <TableCell>Members</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {groups.map((group) => (
              <TableRow key={group.id}>
                <TableCell>
                  <Box display="flex" alignItems="center">
                    <Group sx={{ mr: 1, color: 'primary.main' }} />
                    {group.name}
                  </Box>
                </TableCell>
                <TableCell>{group.loan_officer}</TableCell>
                <TableCell>{group.branch}</TableCell>
                <TableCell>
                  <Box>
                    <Typography variant="body2">{group.meeting_day}</Typography>
                    <Typography variant="body2" color="text.secondary">
                      {group.meeting_time}
                    </Typography>
                  </Box>
                </TableCell>
                <TableCell>{group.total_members}</TableCell>
                <TableCell>
                  <Chip
                    label={group.is_active ? 'Active' : 'Inactive'}
                    color={group.is_active ? 'success' : 'error'}
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

export default GroupsPage;
