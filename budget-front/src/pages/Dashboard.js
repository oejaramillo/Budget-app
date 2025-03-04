import React from "react";
import { Grid, Box } from "@mui/material";
import NavBar from "../components/Navbar";
import TotalBalanceCard from "../components/TotalBalanceCard";
import BalanceCard from "../components/BalanceCard";
import IncomeExpenseChart from "../components/IncomeExpenseChart";
import ExpenseBreakdown from "../components/ExpenseBreakdown";
import "../styles/dashboard.css";

const Dashboard = () => {
  return (
    <Box sx={{ flexGrow: 1, padding: 3 }}>
      <NavBar />
      
      <Grid container spacing={3} alignItems="center">
        {/* Left Side - Balance & Account Selector */}
        <Grid item xs={12} md={4} sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <TotalBalanceCard />
          <BalanceCard />
        </Grid>

        {/* Right Side - Charts */}
        <Grid item xs={12} md={8}>
          <IncomeExpenseChart />
        </Grid>

        {/* Full Width - Expense Breakdown */}
        <Grid item xs={12}>
          <ExpenseBreakdown />
        </Grid>
      </Grid>
    </Box>
  );
};

export default Dashboard;
