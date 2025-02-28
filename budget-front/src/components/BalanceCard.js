import React, { useEffect, useState } from "react";
import { Grid, Paper, Typography, MenuItem, Select, FormControl, InputLabel } from "@mui/material";
import "../styles/dashboard.css";

const BalanceCard = () => {
    const [accounts, setAccounts] = useState([]);
    const [selectedAccount, setSelectedAccount] = useState("");
    const [balance, setBalance] = useState(null);
    const [currency, setCurrency] = useState("");
    const [loading, setLoading] = useState(true);

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
            return data.access;
        } catch (error) {
            console.error("Error refreshing token:", error);
            return null;
        }
    };

    const fetchAccounts = async () => {
        let token = localStorage.getItem("access_token");

        const fetchData = async (token) => {
            return fetch("http://127.0.0.1:8000/api/v1/accounts/", {
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`,
                },
            });
        };

        let response = await fetchData(token);

        if (response.status === 401) {  
            token = await refreshToken();
            if (token) {
                response = await fetchData(token);
            }
        }

        if (!response.ok) {
            console.error("Error fetching accounts:", response.status);
            setAccounts([]);
            setLoading(false);
            return;
        }

        const data = await response.json();
        if (data.results && Array.isArray(data.results) && data.results.length > 0) {
            setAccounts(data.results);
            setSelectedAccount(data.results[0].name);
            fetchAccountBalance(data.results[0].name);
        } else {
            setAccounts([]);
        }
        setLoading(false);
    };

    const fetchAccountBalance = async (accountName) => {
        setLoading(true);
        let token = localStorage.getItem("access_token");

        const fetchData = async (token) => {
            return fetch(`http://127.0.0.1:8000/api/v1/accounts/balance/${encodeURIComponent(accountName)}/`, {
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`,
                },
            });
        };

        let response = await fetchData(token);

        if (response.status === 401) {
            token = await refreshToken();
            if (token) {
                response = await fetchData(token);
            }
        }

        if (!response.ok) {
            console.error("Error fetching account balance:", response.status);
            setLoading(false);
            return;
        }

        const data = await response.json();
        setBalance(data.accountBalance);
        setCurrency(data.currency);
        setLoading(false);
    };

    const handleAccountChange = (event) => {
        const newAccount = event.target.value;
        setSelectedAccount(newAccount);
        fetchAccountBalance(newAccount);
    };

    useEffect(() => {
        fetchAccounts();
    }, []);

    return (
        <Paper sx={{ padding: 3, textAlign: "center", borderRadius: 2, boxShadow: 3 }}>
            {/* Dropdown Selector */}
            <FormControl fullWidth sx={{ marginBottom: 2 }}>
                <InputLabel>Selecciona una cuenta</InputLabel>
                <Select 
                    value={selectedAccount || ""} 
                    onChange={handleAccountChange} 
                    disabled={accounts.length === 0}
                >
                    {accounts.length > 0 ? (
                        accounts.map((account) => (
                            <MenuItem key={account.id} value={account.name}>
                                {account.name}
                            </MenuItem>
                        ))
                    ) : (
                        <MenuItem disabled>No accounts available</MenuItem>
                    )}
                </Select>
            </FormControl>

            {/* Balance Display */}
            <Typography variant="h6" color="primary">
                {selectedAccount ? selectedAccount : "Seleccione una cuenta"}
            </Typography>
            <Typography variant="h4" fontWeight="bold">
                {loading ? "Cargando..." : balance !== null ? `${balance.toLocaleString()} ${currency}` : "Sin saldo"}
            </Typography>
        </Paper>
    );
};

export default BalanceCard;
