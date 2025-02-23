import React, { useEffect, useState } from "react";
import { Grid, Paper, Typography } from "@mui/material";
import "../styles/dashboard.css";

const BalanceCards = () => {
  const [balances, setBalances] = useState({
    total: 0,
    bank: 0,
    cash: 0,
  });

  // Token management
  const refreshToken = async () => {
    try {
      const refresh = localStorage.getItem("refresh_token");
      if (!refresh) throw new Error("No refresh token found!");

      const response = await fetch("http://127.0.0.1:8000/api/v1/auth/token/refresh/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh }),
      });

      if (!response.ok) throw new Error("Failed to refresh token");

      const data = await response.json();
      localStorage.setItem("access_token", data.access);  
      console.log("Token refreshed:", data.access);
      return data.access;
    } catch (error) {
      console.error("Error refreshing token:", error);
      return null;
    }
  };

  // Fetching API
  const fetchBalances = async () => {
    let token = localStorage.getItem("access_token");

    const fetchData = async (token) => {
      return fetch("http://127.0.0.1:8000/api/v1/dashboard/balances/", {
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
      });
    };

    let response = await fetchData(token);

    // If token is expired, refresh it and retry
    if (response.status === 401) {
      token = await refreshToken();
      if (token) {
        response = await fetchData(token);
      }
    }

    if (response.ok) {
      const data = await response.json();
      setBalances({
        total: data.totalBalance,
        bank: data.totalBalance,  
        cash: data.totalBalance,  
      });
    } else {
      console.error("Error fetching balance data:", response.status);
    }
  };

  // Fetch data when the component loads
  useEffect(() => {
    fetchBalances();
  }, []);

  // Card styles
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
