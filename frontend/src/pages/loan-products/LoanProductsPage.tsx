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
import { getLoanProducts } from '../../services/loanProductService';
import { LoanProductResponse } from '../../schemas/loan';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';

const LoanProductsPage: React.FC = () => {
  const [products, setProducts] = useState<LoanProductResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    fetchProducts();
  }, []);

  const fetchProducts = async () => {
    setLoading(true);
    const products = await getLoanProducts();
    setProducts(products);
    setLoading(false);
  };

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.5 }}>
      <Container maxWidth="lg">
        <Box sx={{ my: 4 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h4" component="h1" gutterBottom>
              Loan Product Management
            </Typography>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={() => console.log('Create new product')}
            >
              New Product
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
                    <TableCell>Category ID</TableCell>
                    <TableCell>Selling Price</TableCell>
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {products.map((product) => (
                    <TableRow
                      key={product.id}
                      hover
                      component={motion.tr}
                      whileHover={{ scale: 1.02 }}
                    >
                      <TableCell>{product.name}</TableCell>
                      <TableCell>{product.category_id}</TableCell>
                      <TableCell>{product.selling_price}</TableCell>
                      <TableCell>
                        <IconButton onClick={() => console.log(`Edit product ${product.id}`)}>
                          <EditIcon />
                        </IconButton>
                        <IconButton onClick={() => console.log(`Delete product ${product.id}`)}>
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

export default LoanProductsPage;
