import React from 'react';
import { Currency } from '../../types/currencies';

export const CurrenciesTable = ({ currencies, onDelete }: { currencies: Currency[]; onDelete: (id: number) => void }) => (
  <table>
    <thead>
      <tr>
        <th>Nombre</th>
        <th>ISO</th>
        <th>Tipo de cambio</th>
        <th>Principal</th>
        <th>Activo</th>
        <th>Acciones</th>
      </tr>
    </thead>
    <tbody>
      {currencies.map(cur => (
        <tr key={cur.id}>
          <td>{cur.name}</td>
          <td>{cur.code}</td>
          <td>{cur.exchange_rate}</td>
          <td>{cur.principal ? 'Yes' : 'No'}</td>
          <td>{cur.is_active ? 'Yes' : 'No'}</td>
          <td>
            <button onClick={() => onDelete(cur.id)}>Delete</button>
          </td>
        </tr>
      ))}
    </tbody>
  </table>
);