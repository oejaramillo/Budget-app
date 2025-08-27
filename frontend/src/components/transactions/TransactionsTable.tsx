import React from 'react';
import { useTransactions } from '../../hooks/useTransactions';
import { Transaction } from '../../types/transactions';

interface TransactionsTableProps {
  onEdit?: (transaction: Transaction) => void;
}

const TransactionsTable: React.FC<TransactionsTableProps> = ({ onEdit }) => {
  const { transactions, isLoading, remove } = useTransactions();

  const handleDelete = (id: number) => {
    if (window.confirm('Are you sure you want to delete this transaction?')) {
      remove.mutate(id);
    }
  };

  if (isLoading) return <p>Loading transactions...</p>;

  return (
    <div>
      <h2>Transactions</h2>
      {transactions.length === 0 ? (
        <p>No transactions found.</p>
      ) : (
        <table style={{ borderCollapse: 'collapse', width: '100%' }}>
          <thead>
            <tr>
              <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left', padding: '8px' }}>Date</th>
              <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left', padding: '8px' }}>Account</th>
              <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left', padding: '8px' }}>Type</th>
              <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left', padding: '8px' }}>Amount</th>
              <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left', padding: '8px' }}>Description</th>
              <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left', padding: '8px' }}>Category</th>
              <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left', padding: '8px' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {transactions.map((transaction) => (
              <tr key={transaction.id}>
                <td style={{ padding: '8px' }}>
                  {new Date(transaction.transaction_date).toLocaleDateString()}
                </td>
                <td style={{ padding: '8px' }}>{transaction.account.name}</td>
                <td style={{ padding: '8px' }}>{transaction.transaction_type_display}</td>
                <td style={{ padding: '8px' }}>
                  {transaction.currency.code} {transaction.amount}
                </td>
                <td style={{ padding: '8px' }}>{transaction.description}</td>
                <td style={{ padding: '8px' }}>
                  {transaction.category?.name || 'No category'}
                </td>
                <td style={{ padding: '8px' }}>
                  {onEdit && (
                    <button 
                      onClick={() => onEdit(transaction)}
                      style={{ marginRight: '8px' }}
                    >
                      Edit
                    </button>
                  )}
                  <button 
                    onClick={() => handleDelete(transaction.id)}
                    style={{ backgroundColor: '#dc3545', color: 'white', border: 'none', padding: '4px 8px' }}
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};

export default TransactionsTable;