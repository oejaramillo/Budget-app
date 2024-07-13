import React, { useState } from "react";
import { Dialog, DialogTitle, DialogContent, TextField, DialogActions, Button, MenuItem } from '@mui/material';

const categories = ['Comida', 'Transporte' ];

const AddTransaction = ({ open, handleClose }) => {
    const [amount, setAmount] = useState('');
    const [category, setCategory] = useState('');
    const [date, setDate] = useState('');
    const [notes, setNotes] = useState('');

    const handleSubmit = () => {
        // submit logic
        handleClose();
    };

    return (
        <Dialog open={open} onClose={handleClose}>
            <DialogTitle>Añadir nueva transacción</DialogTitle>
            <DialogContent>
                <TextField
                margin='dense'
                label='Amount'
                type='number'
                fullWidth
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                />
                <TextField
                margin='dense'
                label='Category'
                select
                fullWidth
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                />
                {categories.map((category) => (
                    <MenuItem key={category} value={category}>
                        {category}
                    </MenuItem>
                ))}
                <TextField
                margin='dense'
                label='Date'
                type='date'
                fullWidth
                value={date}
                onChange={(e) => setDate(e.target.value)}
                InputLabelProps={{
                    shrink: true,
                }}
                />
                <TextField
                margin='dense'
                label='Notes'
                type='text'
                fullWidth
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                />
            </DialogContent>
            <DialogActions>
                <Button onclick={handleClose} color='primary'>
                    Cancelar
                </Button>
                <Button onclick={handleSubmit} color='primary'>
                    Guardar
                </Button>
            </DialogActions>
        </Dialog>
    );
};

export default AddTransactions;