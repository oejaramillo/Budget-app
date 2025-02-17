import React, { useEffect, useState } from "react";
import { Grid, Paper, Typography } from "@mui/material";
import "../styles/dashboard.css";

const BalanceCards = () => {
  const [balances, setBalances] = useState({
    total: 0,
    bank: 0,
    cash: 0,
  });

  useEffect(() => {
    fetch("/api/v1/accounts")
      .then((res) => res.json())
      .then((data) => {
        setBalances({
          total: data.totalBalance,
          bank: data.bankBalance,
          cash: data.cashBalance,
        });
      })
      .catch((err) => console.error("Error fetching balance data:", err));
  }, []);

  const cardStyle = {
    padding: "20px",
    textAlign: "center",
    borderRadius: "10px",
    boxShadow: "0 4px 8px rgba(0, 0, 0, 0.1)",
    background: "#ffffff",
  };

  return (
    <Grid container spacing={3}>
      <Grid item xs={12}>
        <Paper style={cardStyle}>
          <Typography variant="h5" color="primary">${balances.total.toLocaleString()}</Typography>
          <Typography variant="subtitle1">Balance Total</Typography>
        </Paper>
      </Grid>
      <Grid item xs={6}>
        <Paper style={cardStyle}>
          <Typography variant="h5" color="primary">${balances.bank.toLocaleString()}</Typography>
          <Typography variant="subtitle1">Balance Banco</Typography>
        </Paper>
      </Grid>
      <Grid item xs={6}>
        <Paper style={cardStyle}>
          <Typography variant="h5" color="primary">${balances.cash.toLocaleString()}</Typography>
          <Typography variant="subtitle1">Balance Efectivo</Typography>
        </Paper>
      </Grid>
    </Grid>
  );
};

export default BalanceCards;
