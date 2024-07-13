import React from 'react';
import { Card, CardContent, Typography, Box } from '@mui/material';

const Dashboard = () => {
    return (
        <Box my={4}>
            <Card>
                <CardContent>
                    <Typography variant='h5' component='h2'>
                        Dashboard overview
                    </Typography>
                    <Typography>Total Income: $XXXX</Typography>
                    <Typography>Total Expenses: $XXXX</Typography>
                    <Typography>Current Balance: $XXXX</Typography>
                    {/* Add a graphical overview here*/}
                </CardContent>
            </Card>
        </Box>
    );
};

export default Dashboard;