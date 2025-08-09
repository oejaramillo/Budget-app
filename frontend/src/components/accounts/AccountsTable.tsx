import React from 'react';
import { Account } from '../../types/accounts';

export const AccountsTable = ({ accounts, onDelete }: { accounts: Account[]; onDelete: (id: number) => void }) => (
  <table>
    <thead>
      <tr>
        <th>Nombre</th>
        <th>Tipo</th>
        <th>Balance</th>
        <th>Moneda</th>
        <th>Acciones</th>
      </tr>
    </thead>
    <tbody>
      {accounts.map(acc => (
        <tr key={acc.id}>
          <td>{acc.name}</td>
          <td>{acc.account_type}</td>
          <td>{acc.balance}</td>
          <td>{acc.currency}</td>
          <td>
            <button onClick={() => onDelete(acc.id)}>Delete</button>
          </td>
        </tr>
      ))}
    </tbody>
  </table>
);