import React from "react";
import { AppBar, Toolbar, Typography, Button } from "@mui/material";

const NavBar = ({ onLogout }) => {
    return (
        <AppBar position="static" color="primary">
            <Toolbar style={{ display: "flex", justifyContent: "space-between" }}>
                <Typography variant="h6">Budget App</Typography> 
                <Button color="inherit" onClick={onLogout}>Cerrar sesión</Button>
            </Toolbar>
        </AppBar>
    );
};

export default NavBar;