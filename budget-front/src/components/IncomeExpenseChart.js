import React, { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from "recharts";
import { Paper, Typography } from "@mui/material";
import "../styles/dashboard.css";

const IncomeExpenseChart = () => {
  const [data, setData] = useState([]);

  useEffect(() => {
    // Simulated API call - Replace with actual API endpoint
    fetch("/api/dashboard/income-expense")
      .then((res) => res.json())
      .then((data) => setData(data))
      .catch((err) => console.error("Error fetching chart data:", err));
  }, []);

  return (
    <Paper className="chart-container">
      <Typography variant="h6" className="chart-title">Ingresos vs Gastos Mensual</Typography>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data}>
          <XAxis dataKey="month" />
          <YAxis />
          <Tooltip />
          <Legend />
          <Bar dataKey="income" fill="#4CAF50" name="Ingresos" />
          <Bar dataKey="expenses" fill="#E53935" name="Gastos" />
        </BarChart>
      </ResponsiveContainer>
    </Paper>
  );
};

export default IncomeExpenseChart;
