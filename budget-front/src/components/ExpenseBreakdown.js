import React, { useEffect, useState } from "react";
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { Paper, Typography } from "@mui/material";
import "../styles/dashboard.css";

const ExpenseBreakdown = () => {
  const [data, setData] = useState([]);

  useEffect(() => {
    // Simulated API call - Replace with actual API endpoint
    fetch("/api/dashboard/expense-breakdown")
      .then((res) => res.json())
      .then((data) => setData(data))
      .catch((err) => console.error("Error fetching pie chart data:", err));
  }, []);

  const COLORS = ["#FF9800", "#4CAF50", "#E53935", "#009688", "#1976D2"];

  return (
    <Paper className="chart-container">
      <Typography variant="h6" className="chart-title">Detalle Gastos</Typography>
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie data={data} dataKey="value" nameKey="category" cx="50%" cy="50%" outerRadius={100} label>
            {data.map((_, index) => <Cell key={index} fill={COLORS[index % COLORS.length]} />)}
          </Pie>
          <Tooltip />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </Paper>
  );
};

export default ExpenseBreakdown;
