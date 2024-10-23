import React, { useEffect, useState } from 'react';
import axios from 'axios';

const App = () => {
  const [accounts, setAccounts] = useState([]);

  useEffect(() => {
    axios.get('http://127.0.0.1:8000/api/v1/accounts/')
    .then(response => {
      setAccounts(response.data);
    })
    .catch(error => {
      console.error("There was an error fetching the accounts", error);
    });
  }, []);
  
  return (
    <div>
      <h1>Cuentas</h1>
      <ul>
        {accounts.map(account => (
          <li key={account.id}>{account.name} - {account.balance}</li>
        ))}
      </ul>
    </div>
  );
};

export default App;
