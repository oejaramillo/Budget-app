import React, { useState, useEffect } from 'react';
import { useCurrencies } from '../../hooks/useCurrencies';

export const AccountForm = ({ onCreated }) => {
  const [name, setName] = useState('');
  const [accountType, setAccountType] = useState('checking');
  const [balance, setBalance] = useState('');
  const { currencies, isLoading } = useCurrencies();
  const [currency, setCurrency] = useState('165');

  // Set default to principal currency if available
  useEffect(() => {
    if (!currency && currencies.length > 0) {
      const principal = currencies.find(c => c.principal);
      if (principal) setCurrency(String(principal.id));
    }
  }, [currencies, currency]);

  const handleSubmit = (e) => {
    e.preventDefault();
    const accountData = {
      name,
      account_type: accountType,
      balance,
      currency: Number(currency), // send as number
      // ...other fields
    };
    // Call create mutation here, then onCreated()
  };

  return (
    <form onSubmit={handleSubmit}>
      <input value={name} onChange={e => setName(e.target.value)} placeholder="Nombre de la cuenta" required />
      <select value={accountType} onChange={e => setAccountType(e.target.value)}>
        <option value="checking">Corriente</option>
        <option value="savings">Ahorros</option>
        <option value="credit">Crédito</option>
      </select>
      <input value={balance} onChange={e => setBalance(e.target.value)} placeholder="Balance" required />
      <select value={currency} onChange={e => setCurrency(e.target.value)} >
        <option value="">--Seleccione una moneda--</option>
        {currencies.map(cur => (
          <option key={cur.id} value={cur.id}>
            {cur.name} ({cur.code})
          </option>
        ))}
      </select>
      <button type="submit">Crear cuenta</button>
    </form>
  );
};