import React from "react";
import { Drawer, iconButtonClasses, List, ListItem, ListItemIcon, ListItemText } from "@mui/material";
import HomeIcon from "@mui/icons-material/Home";
import AccountBalanceIcon from "@mui/icons-material/AttachMoney";
import BudgetIcon from "@mui/icons-material/AttachMoney";
import ListAltIcon from "@mui/icons-material/ListAlt";
import SettingsIcon from "@mui/icons-material/Settings";
import { useNavigate } from "react-router-dom";

const Sidebar = () => {
    const navigate = useNavigate();

    const menuItems = [
        { text: "Inicio", icon: <HomeIcon />, path: "/dashboard" },
        { text: "Cuentas", icon: <AccountBalanceIcon />, path: "/accounts" },
        { text: "Presupuestos", icon: <BudgetIcon />, path: "/budgets" },
        { text: "Entradas", icon: <ListAltIcon />, path: "/transactions" },
        { text: "Configuración", icon: <SettingsIcon />, path: "/settings" }
    ];

    return   (
        <Drawer variant="permanent" sx={{ width: 240, flexShrink: 0 }}>
            <List>
                {menuItems.map((item) => (
                    <ListItem button key={item.text} onclick={() => navigate(item.path)}>
                        <ListItemIcon>{item.icon}</ListItemIcon>
                        <ListItemText primary={item.text} />
                    </ListItem>
                ))}
            </List>
        </Drawer>
    );
};

export default Sidebar;