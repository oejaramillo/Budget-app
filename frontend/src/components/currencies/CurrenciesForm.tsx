import React, { useState } from 'react';

export const CurrencyForm = ({ onCreated }: { onCreated: () => void }) => {
  const [name, setName] = useState('');
  const [code, setCode] = useState('');
  const [exchangeRate, setExchangeRate] = useState('');
  const [principal, setPrincipal] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // Call create mutation here, then onCreated()
  };

  return (
    <form onSubmit={handleSubmit}>
      <input value={name} onChange={e => setName(e.target.value)} placeholder="Name" required />
      <input value={code} onChange={e => setCode(e.target.value)} placeholder="Code" required />
      <input value={exchangeRate} onChange={e => setExchangeRate(e.target.value)} placeholder="Exchange Rate" required />
      <label>
        <input type="checkbox" checked={principal} onChange={e => setPrincipal(e.target.checked)} />
        Principal
      </label>
      <button type="submit">Create Currency</button>
    </form>
  );
};