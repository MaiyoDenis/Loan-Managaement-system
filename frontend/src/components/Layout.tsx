import React from 'react';
import { Box } from '@mui/material';
import Sidebar from './Layout/Sidebar';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: 'grey.100' }}>
      <Sidebar />
      <Box 
        sx={{ 
          flexGrow: 1, 
          display: 'flex', 
          flexDirection: 'column', 
          overflow: 'hidden',
          width: { xs: '100%', md: 'calc(100% - 280px)' },
        }}
      >
        <Box
          component="main"
          sx={{
            flexGrow: 1,
            overflowX: 'hidden',
            overflowY: 'auto',
            bgcolor: 'grey.100',
            p: { xs: 2, sm: 3 },
            pt: { xs: 8, md: 3 }, // Extra padding top on mobile for menu button
          }}
        >
          {children}
        </Box>
      </Box>
    </Box>
  );
};

export default Layout;