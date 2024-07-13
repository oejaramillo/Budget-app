import React from "react";
import { Card, CardContent, Typography, Box } from '@mui/material';
// IMport chart libraries

const Reports = () => {
    return (
        <Box my={4}>
            <Card>
                <CardContent>
                    <Typography variant='h5' component='h2'>
                        Reports
                    </Typography>
                    {/* Add graphs and charts here*/}
                </CardContent>
            </Card>
        </Box>
    );
};

export default Reports;