import React, { useEffect, useState } from "react";
import { Grid, Paper, Typography, MenuItem, Select, FormControl, InputLabel } from "@mui/material";
import "../styles/dashboard.css";

const AccountBalanceCard = () => {
  const [accounts, setAccounts] = useState([]); // Stores all user accounts
  const [selectedAccount, setSelectedAccount] = useState(""); // Currently selected account
  const [balance, setBalance] = useState(null); // Balance of selected account
  const [currency, setCurrency] = useState(""); // Currency of the selected account

  // Fetch user accounts
  const fetchAccounts = async () => {
    const token = localStorage.getItem("access_token");
    try {
      const response = await fetch("http://127.0.0.1:8000/api/v1/accounts/", {
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) throw new Error(`HTTP Error: ${response.status}`);

      const data = await response.json();
      setAccounts(data);
      if (data.length > 0) {
        setSelectedAccount(data[0].name); // Set the first account as default
        fetchAccountBalance(data[0].name);
      }
    } catch (error) {
      console.error("Error fetching accounts:", error);
    }
  };

  // Fetch balance of the selected account
  const fetchAccountBalance = async (accountName) => {
    const token = localStorage.getItem("access_token");
    try {
      const response = await fetch(`http://127.0.0.1:8000/api/v1/accounts/balance/${encodeURIComponent(accountName)}/`, {
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) throw new Error(`HTTP Error: ${response.status}`);

      const data = await response.json();
      setBalance(data.balance);
      setCurrency(data.currency);
    } catch (error) {
      console.error("Error fetching account balance:", error);
    }
  };

  // Handle account selection change
  const handleAccountChange = (event) => {
    const newAccount = event.target.value;
    setSelectedAccount(newAccount);
    fetchAccountBalance(newAccount);
  };

  useEffect(() => {
    fetchAccounts();
  }, []);

  return (
    <Grid container spacing={3} justifyContent="center">
      <Grid item xs={12} sm={8} md={6}>
        <FormControl fullWidth>
          <InputLabel>Selecciona una cuenta</InputLabel>
          <Select value={selectedAccount} onChange={handleAccountChange}>
            {accounts.map((account) => (
              <MenuItem key={account.id} value={account.name}>
                {account.name}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </Grid>

      <Grid item xs={12} sm={8} md={6}>
        <Paper className="balance-card">
          <Typography variant="h5" color="primary">
            {selectedAccount ? selectedAccount : "Seleccione una cuenta"}
          </Typography>
          <Typography variant="h4">
            {balance !== null ? `${balance.toLocaleString()} ${currency}` : "Cargando..."}
          </Typography>
          <Typography variant="subtitle1">Saldo Disponible</Typography>
        </Paper>
      </Grid>
    </Grid>
  );
};

export default AccountBalanceCard;
