import React from "react";
import { Grid, Box } from "@mui/material";
import NavBar from "../components/Navbar";
import BalanceCards from "../components/BalanceCards";
import IncomeExpenseChart from "../components/IncomeExpenseChart";
import ExpenseBreakdown from "../components/ExpenseBreakdown";
import "../styles/dashboard.css";

const Dashboard = () => {
  return (
    <Box sx={{ flexGrow: 1 }}>
      <NavBar />
      <Box sx={{ padding: 3 }}>
        <Grid container spacing={3}>
          <Grid item xs={12} md={3}>
            <BalanceCards />
          </Grid>
          <Grid item xs={12} md={9}>
            <IncomeExpenseChart />
          </Grid>
          <Grid item xs={12}>
            <ExpenseBreakdown />
          </Grid>
        </Grid>
      </Box>
    </Box>
  );
};

export default Dashboard;
