import React from "react";
import { Box } from "@mui/material";
import NavBar from "../components/Navbar";
import Sidebar from "../components/Sidebar";

const Dashboard = () => {
    const handleLogout = () => {
        localStorage.removeItem("token");
        window.location.href = "/";
    }

    return (
        <Box sx={{ display: "flex" }}>
            <Sidebar />
            <Box sx={{ flexGrow: 1 }}>
                <NavBar onLogout={handleLogout} />
                <Box sx={{ padding: 3 }}>
                    <h2>Bienvenido a tu tablero</h2>
                    <p>Aquí encontrarás información sobre tus entradas, cuentas y Presupuestos</p>
                </Box>
            </Box>
        </Box>
    );
};

export default Dashboard;