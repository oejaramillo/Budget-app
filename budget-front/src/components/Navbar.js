import React, { useState } from "react";
import { AppBar, Toolbar, Tabs, Tab, Box, Avatar, Menu, MenuItem, IconButton } from "@mui/material";
import { useNavigate } from "react-router-dom";
import AccountCircleIcon from "@mui/icons-material/AccountCircle";
import "../styles/navbar.css";

const Navbar = () => {
  const [selectedTab, setSelectedTab] = useState(0);
  const [anchorEl, setAnchorEl] = useState(null);
  const navigate = useNavigate();

  const handleTabChange = (event, newValue) => {
    setSelectedTab(newValue);
    const routes = ["/dashboard", "/transactions", "/accounts", "/budgets", "/investments", "/charts"];
    navigate(routes[newValue]);
  };

  const handleMenuOpen = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  return (
    <AppBar position="static" className="navbar">
      <Toolbar className="toolbar">
        {/* Navigation Tabs */}
        <Tabs value={selectedTab} onChange={handleTabChange} className="nav-tabs">
          <Tab label="Inicio" />
          <Tab label="Transacciones" />
          <Tab label="Cuentas" />
          <Tab label="Presupuestos" />
          <Tab label="Inversiones" />
          <Tab label="Gráficos" />
        </Tabs>

        {/* User Profile Section */}
        <Box className="user-profile" onClick={handleMenuOpen}>
          <IconButton>
            <Avatar className="avatar">
              <AccountCircleIcon fontSize="large" />
            </Avatar>
          </IconButton>
          <span className="username">Usuario</span>
        </Box>

        {/* Dropdown Menu */}
        <Menu anchorEl={anchorEl} open={Boolean(anchorEl)} onClose={handleMenuClose}>
          <MenuItem onClick={() => navigate("/profile")}>Perfil</MenuItem>
          <MenuItem onClick={() => navigate("/settings")}>Configuración</MenuItem>
          <MenuItem onClick={() => navigate("/logout")}>Cerrar Sesión</MenuItem>
        </Menu>
      </Toolbar>
    </AppBar>
  );
};

export default Navbar;
