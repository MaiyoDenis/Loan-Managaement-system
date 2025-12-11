import React, { useState } from 'react';
import {
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar,
  Divider,
  Box,
  Typography,
  Avatar,
  Chip,
  IconButton,
  useMediaQuery,
  useTheme,
} from '@mui/material';
import { Menu as MenuIcon } from '@mui/icons-material';
import {
  Dashboard,
  People,
  Business,
  Group,
  AccountBalance,
  Inventory,
  Analytics,
  Settings,
  ExitToApp,
  MonetizationOn,
  Assignment,
  Payment,
  Notifications
} from '@mui/icons-material';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

const drawerWidth = 280;

interface MenuItem {
  text: string;
  icon: React.ReactElement;
  path: string;
  roles: string[];
  permission?: string;
}

const menuItems: MenuItem[] = [
  {
    text: 'Dashboard',
    icon: <Dashboard />,
    path: '/dashboard',
    roles: ['admin', 'branch_manager', 'procurement_officer', 'loan_officer', 'customer']
  },
  {
    text: 'Users Management',
    icon: <People />,
    path: '/users',
    roles: ['admin', 'branch_manager', 'loan_officer']
  },
  {
    text: 'Branches',
    icon: <Business />,
    path: '/branches',
    roles: ['admin']
  },
  {
    text: 'Groups',
    icon: <Group />,
    path: '/groups',
    roles: ['admin', 'branch_manager', 'loan_officer']
  },
  {
    text: 'Loan Products',
    icon: <Inventory />,
    path: '/loan-products',
    roles: ['admin', 'branch_manager', 'procurement_officer']
  },
  {
    text: 'Loan Types',
    icon: <MonetizationOn />,
    path: '/loan-types',
    roles: ['admin', 'branch_manager']
  },
  {
    text: 'Loan Applications',
    icon: <Assignment />,
    path: '/loan-applications',
    roles: ['admin', 'branch_manager', 'procurement_officer', 'loan_officer', 'customer']
  },
  {
    text: 'Active Loans',
    icon: <AccountBalance />,
    path: '/loans',
    roles: ['admin', 'branch_manager', 'procurement_officer', 'loan_officer', 'customer']
  },
  {
    text: 'Payments',
    icon: <Payment />,
    path: '/payments',
    roles: ['admin', 'branch_manager', 'procurement_officer', 'loan_officer']
  },
  {
    text: 'Inventory',
    icon: <Inventory />,
    path: '/inventory',
    roles: ['admin', 'branch_manager', 'procurement_officer']
  },
  {
    text: 'Analytics',
    icon: <Analytics />,
    path: '/analytics',
    roles: ['admin', 'branch_manager', 'procurement_officer']
  },
  {
    text: 'Notifications',
    icon: <Notifications />,
    path: '/notifications',
    roles: ['admin', 'branch_manager', 'procurement_officer', 'loan_officer', 'customer']
  },
  {
    text: 'Settings',
    icon: <Settings />,
    path: '/settings',
    roles: ['admin', 'branch_manager']
  }
];

const Sidebar: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuth();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [mobileOpen, setMobileOpen] = useState(false);

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  const handleNavigation = (path: string) => {
    navigate(path);
    if (isMobile) {
      setMobileOpen(false);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const getRoleColor = (role: string) => {
    const colors: { [key: string]: 'default' | 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning' } = {
      admin: 'error',
      branch_manager: 'primary',
      procurement_officer: 'info',
      loan_officer: 'success',
      customer: 'default'
    };
    return colors[role] || 'default';
  };

  const getRoleLabel = (role: string) => {
    const labels: { [key: string]: string } = {
      admin: 'Admin',
      branch_manager: 'Branch Manager',
      procurement_officer: 'Procurement Officer',
      loan_officer: 'Loan Officer',
      customer: 'Customer'
    };
    return labels[role] || role;
  };

  const filteredMenuItems = menuItems.filter(item => 
    user && item.roles.includes(user.role)
  );

  const drawerContent = (
    <>
      <Toolbar>
        <Box sx={{ display: 'flex', alignItems: 'center', width: '100%' }}>
          <Avatar sx={{ mr: 2, bgcolor: 'primary.main' }}>
            {user?.first_name?.[0]}{user?.last_name?.[0]}
          </Avatar>
          <Box sx={{ flexGrow: 1 }}>
            <Typography variant="h6" noWrap component="div" sx={{ fontSize: '1rem' }}>
              Kim Loans
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Management System
            </Typography>
          </Box>
        </Box>
      </Toolbar>
      
      <Divider />
      
      {/* User Info */}
      <Box sx={{ p: 2, bgcolor: 'grey.50' }}>
        <Typography variant="subtitle2" gutterBottom>
          {user?.first_name} {user?.last_name}
        </Typography>
        <Typography variant="caption" color="text.secondary" display="block">
          @{user?.username}
        </Typography>
        <Box sx={{ mt: 1 }}>
          <Chip 
            label={getRoleLabel(user?.role || '')} 
            size="small" 
            color={getRoleColor(user?.role || '')}
          />
        </Box>
      </Box>
      
      <Divider />
      
      {/* Navigation Menu */}
      <Box sx={{ flexGrow: 1 }}>
        <List>
          {filteredMenuItems.map((item) => (
            <ListItem key={item.text} disablePadding>
              <ListItemButton
                selected={location.pathname === item.path}
                onClick={() => handleNavigation(item.path)}
                sx={{
                  '&.Mui-selected': {
                    backgroundColor: 'primary.light',
                    color: 'primary.contrastText',
                    '& .MuiListItemIcon-root': {
                      color: 'primary.contrastText',
                    },
                  },
                }}
              >
                <ListItemIcon>{item.icon}</ListItemIcon>
                <ListItemText 
                  primary={item.text}
                  primaryTypographyProps={{ fontSize: '0.9rem' }}
                />
              </ListItemButton>
            </ListItem>
          ))}
        </List>
      </Box>
      
      <Divider />
      
      {/* Logout Button */}
      <List>
        <ListItem disablePadding>
          <ListItemButton onClick={handleLogout}>
            <ListItemIcon>
              <ExitToApp />
            </ListItemIcon>
            <ListItemText primary="Logout" />
          </ListItemButton>
        </ListItem>
      </List>
    </>
  );

  return (
    <>
      {/* Mobile menu button */}
      {isMobile && (
        <IconButton
          color="inherit"
          aria-label="open drawer"
          edge="start"
          onClick={handleDrawerToggle}
          sx={{
            position: 'fixed',
            top: 16,
            left: 16,
            zIndex: theme.zIndex.drawer + 1,
            bgcolor: 'primary.main',
            color: 'white',
            '&:hover': {
              bgcolor: 'primary.dark',
            },
          }}
        >
          <MenuIcon />
        </IconButton>
      )}

      {/* Mobile drawer */}
      {isMobile ? (
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{
            keepMounted: true, // Better open performance on mobile
          }}
          sx={{
            display: { xs: 'block', md: 'none' },
            '& .MuiDrawer-paper': {
              width: drawerWidth,
              boxSizing: 'border-box',
            },
          }}
        >
          {drawerContent}
        </Drawer>
      ) : (
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: 'none', md: 'block' },
            width: drawerWidth,
            flexShrink: 0,
            '& .MuiDrawer-paper': {
              width: drawerWidth,
              boxSizing: 'border-box',
            },
          }}
        >
          {drawerContent}
        </Drawer>
      )}
    </>
  );
};

export default Sidebar;