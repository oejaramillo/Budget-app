import React, { useState } from 'react';
import { Container, Typography, Box, Button } from '@mui/material';
import AddTransaction from './components/AddTransaction';
import Dashboard from './components/Dashboard';
import Reports from '.components/Reports';

const App = () => {
  const [open, setOpen] = useState(false);

  const handleClickOpen = () => {
    setOpen(true);
  };

  const handleClose = () => {
    setOpen(false);
  };

  return (
    <Container>
      <Box my={4}>
        <Typography variant="h4" component="h1" gutterBottom>
          Budget App
        </Typography>
        <Button variant='contained' color='primary' onClick={handleClickOpen}>
          Add Transaction
        </Button>
      </Box>
      <AddTransaction open={open} handleClose={handleClose} />
      <Dashboard />
      <Reports />
    </Container>
  );
};

export default App;