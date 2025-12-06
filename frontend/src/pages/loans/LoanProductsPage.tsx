import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Button,
  Grid,
  Card,
  CardContent,
  CardMedia,
  CardActions,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  MenuItem,
  FormControl,
  InputLabel,
  Select,
  IconButton,
  Alert,
  Fab,
  Badge
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Visibility as ViewIcon,
  PhotoCamera,
  AttachMoney,
  Category,
  Inventory
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { toast } from 'react-toastify';

import { loanProductsAPI, productCategoriesAPI } from '../../services/api';
import { useAuth } from '../../contexts/AuthContext';

interface LoanProduct {
  id: number;
  name: string;
  category_id: number;
  category_name: string;
  description: string;
  buying_price?: number;
  selling_price: number;
  profit_margin?: number;
  image_url?: string;
  current_quantity?: number;
  inventory_status?: string;
  is_active: boolean;
}

interface ProductCategory {
  id: number;
  name: string;
  description: string;
}

const LoanProductsPage: React.FC = () => {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  
  // State management
  const [open, setOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState<LoanProduct | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    category_id: '',
    description: '',
    buying_price: '',
    selling_price: '',
  });

  // API Queries
  const { data: products = [], isLoading: productsLoading } = useQuery(
    ['loan-products', selectedCategory],
    () => loanProductsAPI.getProducts({ 
      category_id: selectedCategory !== 'all' ? parseInt(selectedCategory) : undefined,
      branch_id: user?.branch_id 
    }),
    { refetchInterval: 30000 }
  );

  const { data: categories = [] } = useQuery(
    'product-categories',
    () => productCategoriesAPI.getCategories()
  );

  // Mutations
  const createProductMutation = useMutation(
    (data: FormData) => loanProductsAPI.createProduct(data),
    {
      onSuccess: () => {
        queryClient.invalidateQueries('loan-products');
        toast.success('Product created successfully!');
        handleCloseDialog();
      },
      onError: (error: any) => {
        toast.error(error.response?.data?.detail || 'Failed to create product');
      }
    }
  );

  const updateProductMutation = useMutation(
    ({ id, data }: { id: number; data: any }) => loanProductsAPI.updateProduct(id, data),
    {
      onSuccess: () => {
        queryClient.invalidateQueries('loan-products');
        toast.success('Product updated successfully!');
        handleCloseDialog();
      },
      onError: (error: any) => {
        toast.error(error.response?.data?.detail || 'Failed to update product');
      }
    }
  );

  const deleteProductMutation = useMutation(
    (id: number) => loanProductsAPI.deleteProduct(id),
    {
      onSuccess: () => {
        queryClient.invalidateQueries('loan-products');
        toast.success('Product deleted successfully!');
      },
      onError: (error: any) => {
        toast.error(error.response?.data?.detail || 'Failed to delete product');
      }
    }
  );

  // Event handlers
  const handleOpenDialog = (product?: LoanProduct) => {
    if (product) {
      setEditingProduct(product);
      setFormData({
        name: product.name,
        category_id: product.category_id.toString(),
        description: product.description || '',
        buying_price: product.buying_price?.toString() || '',
        selling_price: product.selling_price.toString(),
      });
    } else {
      setEditingProduct(null);
      setFormData({
        name: '',
        category_id: '',
        description: '',
        buying_price: '',
        selling_price: '',
      });
    }
    setImageFile(null);
    setOpen(true);
  };

  const handleCloseDialog = () => {
    setOpen(false);
    setEditingProduct(null);
    setImageFile(null);
  };

  const handleSubmit = () => {
    // Validate form
    if (!formData.name || !formData.category_id || !formData.selling_price) {
      toast.error('Please fill in all required fields');
      return;
    }

    if (user?.role === 'admin' && !formData.buying_price) {
      toast.error('Buying price is required');
      return;
    }

    // Prepare form data
    const submitData = new FormData();
    submitData.append('name', formData.name);
    submitData.append('category_id', formData.category_id);
    submitData.append('description', formData.description);
    submitData.append('selling_price', formData.selling_price);
    
    if (user?.role === 'admin' && formData.buying_price) {
      submitData.append('buying_price', formData.buying_price);
    }
    
    if (imageFile) {
      submitData.append('image', imageFile);
    }

    if (editingProduct) {
      updateProductMutation.mutate({ id: editingProduct.id, data: submitData });
    } else {
      createProductMutation.mutate(submitData);
    }
  };

  const handleDelete = (product: LoanProduct) => {
    if (window.confirm(`Are you sure you want to delete ${product.name}?`)) {
      deleteProductMutation.mutate(product.id);
    }
  };

  const getInventoryStatusColor = (status?: string) => {
    switch (status) {
      case 'critical': return 'error';
      case 'low': return 'warning';
      case 'ok': return 'success';
      default: return 'default';
    }
  };

  const canManageProducts = user?.role === 'admin' || user?.role === 'branch_manager';

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          Loan Products
        </Typography>
        
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
          <FormControl sx={{ minWidth: 150 }}>
            <InputLabel>Category</InputLabel>
            <Select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              label="Category"
              size="small"
            >
              <MenuItem value="all">All Categories</MenuItem>
              {categories.map((category: ProductCategory) => (
                <MenuItem key={category.id} value={category.id.toString()}>
                  {category.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          
          {canManageProducts && (
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={() => handleOpenDialog()}
            >
              Add Product
            </Button>
          )}
        </Box>
      </Box>

      {/* Products Grid */}
      <Grid container spacing={3}>
        {products.map((product: LoanProduct) => (
          <Grid item xs={12} sm={6} md={4} lg={3} key={product.id}>
            <Card 
              sx={{ 
                height: '100%', 
                display: 'flex', 
                flexDirection: 'column',
                position: 'relative'
              }}
            >
              {/* Inventory Status Badge */}
              {product.inventory_status && (
                <Badge
                  badgeContent={product.current_quantity}
                  color={getInventoryStatusColor(product.inventory_status)}
                  sx={{ 
                    position: 'absolute', 
                    top: 8, 
                    right: 8, 
                    zIndex: 1 
                  }}
                />
              )}
              
              {/* Product Image */}
              <CardMedia
                component="img"
                height="200"
                image={product.image_url || '/placeholder-product.jpg'}
                alt={product.name}
                sx={{ objectFit: 'cover' }}
              />
              
              <CardContent sx={{ flexGrow: 1 }}>
                <Typography variant="h6" component="h2" gutterBottom>
                  {product.name}
                </Typography>
                
                <Typography variant="body2" color="text.secondary" paragraph>
                  {product.description}
                </Typography>
                
                <Box sx={{ mb: 2 }}>
                  <Chip 
                    label={product.category_name} 
                    size="small" 
                    icon={<Category />}
                    sx={{ mb: 1 }}
                  />
                </Box>
                
                {/* Pricing */}
                <Box sx={{ mb: 2 }}>
                  <Typography variant="h6" color="primary">
                    ${product.selling_price.toLocaleString()}
                  </Typography>
                  
                  {user?.role === 'admin' && product.buying_price && (
                    <>
                      <Typography variant="caption" color="text.secondary" display="block">
                        Cost: ${product.buying_price.toLocaleString()}
                      </Typography>
                      <Typography variant="caption" color="success.main" display="block">
                        Profit: {product.profit_margin?.toFixed(1)}%
                      </Typography>
                    </>
                  )}
                </Box>
                
                {/* Inventory Info */}
                {product.current_quantity !== undefined && (
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Inventory fontSize="small" />
                    <Typography variant="caption">
                      Stock: {product.current_quantity}
                    </Typography>
                    <Chip 
                      label={product.inventory_status} 
                      size="small"
                      color={getInventoryStatusColor(product.inventory_status)}
                    />
                  </Box>
                )}
              </CardContent>
              
              {canManageProducts && (
                <CardActions>
                  <IconButton 
                    size="small" 
                    onClick={() => handleOpenDialog(product)}
                    color="primary"
                  >
                    <EditIcon />
                  </IconButton>
                  <IconButton 
                    size="small" 
                    onClick={() => handleDelete(product)}
                    color="error"
                  >
                    <DeleteIcon />
                  </IconButton>
                </CardActions>
              )}
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Add/Edit Product Dialog */}
      <Dialog 
        open={open} 
        onClose={handleCloseDialog}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          {editingProduct ? 'Edit Product' : 'Add New Product'}
        </DialogTitle>
        
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
            <TextField
              label="Product Name"
              value={formData.name}
              onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
              fullWidth
              required
            />
            
            <FormControl fullWidth required>
              <InputLabel>Category</InputLabel>
              <Select
                value={formData.category_id}
                onChange={(e) => setFormData(prev => ({ ...prev, category_id: e.target.value }))}
                label="Category"
              >
                {categories.map((category: ProductCategory) => (
                  <MenuItem key={category.id} value={category.id.toString()}>
                    {category.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            
            <TextField
              label="Description"
              value={formData.description}
              onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
              fullWidth
              multiline
              rows={3}
            />
            
            <Grid container spacing={2}>
              {user?.role === 'admin' && (
                <Grid item xs={6}>
                  <TextField
                    label="Buying Price (Secret)"
                    type="number"
                    value={formData.buying_price}
                    onChange={(e) => setFormData(prev => ({ ...prev, buying_price: e.target.value }))}
                    fullWidth
                    required
                    InputProps={{ startAdornment: '$' }}
                    helperText="Only visible to admin"
                  />
                </Grid>
              )}
              
              <Grid item xs={user?.role === 'admin' ? 6 : 12}>
                <TextField
                  label="Selling Price"
                  type="number"
                  value={formData.selling_price}
                  onChange={(e) => setFormData(prev => ({ ...prev, selling_price: e.target.value }))}
                  fullWidth
                  required
                  InputProps={{ startAdornment: '$' }}
                />
              </Grid>
            </Grid>
            
            {/* Image Upload */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Button
                variant="outlined"
                component="label"
                startIcon={<PhotoCamera />}
              >
                Upload Image
                <input
                  type="file"
                  hidden
                  accept="image/*"
                  onChange={(e) => setImageFile(e.target.files?.[0] || null)}
                />
              </Button>
              {imageFile && (
                <Typography variant="body2" color="primary">
                  {imageFile.name}
                </Typography>
              )}
            </Box>
            
            {/* Profit Calculation Preview */}
            {user?.role === 'admin' && formData.buying_price && formData.selling_price && (
              <Alert severity="info">
                <Typography variant="body2">
                  Profit Margin: {
                    ((parseFloat(formData.selling_price) - parseFloat(formData.buying_price)) / 
                     parseFloat(formData.buying_price) * 100).toFixed(1)
                  }%
                </Typography>
                <Typography variant="body2">
                  Profit per Unit: ${
                    (parseFloat(formData.selling_price) - parseFloat(formData.buying_price)).toFixed(2)
                  }
                </Typography>
              </Alert>
            )}
          </Box>
        </DialogContent>
        
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <Button 
            onClick={handleSubmit}
            variant="contained"
            disabled={createProductMutation.isLoading || updateProductMutation.isLoading}
          >
            {editingProduct ? 'Update' : 'Create'} Product
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default LoanProductsPage;