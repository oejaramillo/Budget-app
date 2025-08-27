import React from 'react';
import { useAccounts } from '../../hooks/useAccounts';
import { Account } from '../../types/accounts';

interface AccountsTableProps {
  onEdit?: (account: Account) => void;
}

const AccountsTable: React.FC<AccountsTableProps> = ({ onEdit }) => {
  const { accounts, isLoading, remove } = useAccounts();

  const handleDelete = (id: number) => {
    if (window.confirm('Are you sure you want to delete this account?')) {
      remove.mutate(id);
    }
  };

  if (isLoading) return <p>Loading accounts...</p>;

  return (
    <div>
      <h2>Accounts</h2>
      {accounts.length === 0 ? (
        <p>No accounts found.</p>
      ) : (
        <table style={{ borderCollapse: 'collapse', width: '100%' }}>
          <thead>
            <tr>
              <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left', padding: '8px' }}>Name</th>
              <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left', padding: '8px' }}>Type</th>
              <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left', padding: '8px' }}>Balance</th>
              <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left', padding: '8px' }}>Institution</th>
              <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left', padding: '8px' }}>Created</th>
              <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left', padding: '8px' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {accounts.map((account) => (
              <tr key={account.id}>
                <td style={{ padding: '8px' }}>{account.name}</td>
                <td style={{ padding: '8px' }}>
                  {account.account_type.charAt(0).toUpperCase() + account.account_type.slice(1)}
                </td>
                <td style={{ padding: '8px' }}>{account.balance}</td>
                <td style={{ padding: '8px' }}>{account.institution || 'N/A'}</td>
                <td style={{ padding: '8px' }}>
                  {new Date(account.created_date).toLocaleDateString()}
                </td>
                <td style={{ padding: '8px' }}>
                  {onEdit && (
                    <button 
                      onClick={() => onEdit(account)}
                      style={{ marginRight: '8px' }}
                    >
                      Edit
                    </button>
                  )}
                  <button 
                    onClick={() => handleDelete(account.id)}
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

export default AccountsTable;