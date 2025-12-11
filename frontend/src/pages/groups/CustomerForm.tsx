import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
} from '@mui/material';
import type { CustomerCreate } from '../../schemas/user';
import { motion } from 'framer-motion';

interface CustomerFormProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (customer: CustomerCreate) => void;
  groupId: number;
}

const CustomerForm: React.FC<CustomerFormProps> = ({ open, onClose, onSubmit, groupId }) => {
  const [formData, setFormData] = useState<Omit<CustomerCreate, 'group_id'>>({
    phone_number: '',
    first_name: '',
    last_name: '',
    national_id: '',
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({ ...formData, group_id: groupId });
  };

  return (
    <Dialog open={open} onClose={onClose}>
      <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.3 }}>
        <DialogTitle>Add New Member</DialogTitle>
        <form onSubmit={handleSubmit}>
          <DialogContent>
            <TextField
              name="first_name"
              label="First Name"
              value={formData.first_name}
              onChange={handleChange}
              fullWidth
              margin="normal"
            />
            <TextField
              name="last_name"
              label="Last Name"
              value={formData.last_name}
              onChange={handleChange}
              fullWidth
              margin="normal"
            />
            <TextField
              name="phone_number"
              label="Phone Number"
              value={formData.phone_number}
              onChange={handleChange}
              fullWidth
              margin="normal"
            />
            <TextField
              name="national_id"
              label="National ID"
              value={formData.national_id || ''}
              onChange={handleChange}
              fullWidth
              margin="normal"
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={onClose}>Cancel</Button>
            <Button type="submit" variant="contained">
              Create
            </Button>
          </DialogActions>
        </form>
      </motion.div>
    </Dialog>
  );
};

export default CustomerForm;
