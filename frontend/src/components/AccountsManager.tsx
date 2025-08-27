import React, { useState } from 'react';
import AccountsTable from './accounts/AccountsTable';
import AccountsForm from './accounts/AccountsForm';
import { Account } from '../types/accounts';

const AccountsManager: React.FC = () => {
  const [editingAccount, setEditingAccount] = useState<Account | null>(null);
  const [showForm, setShowForm] = useState(false);

  const handleEdit = (account: Account) => {
    setEditingAccount(account);
    setShowForm(true);
  };

  const handleCancel = () => {
    setEditingAccount(null);
    setShowForm(false);
  };

  return (
    <div style={{ padding: '20px' }}>
      <div style={{ marginBottom: '20px' }}>
        <button 
          onClick={() => setShowForm(!showForm)}
          style={{ 
            padding: '10px 20px', 
            backgroundColor: '#28a745', 
            color: 'white', 
            border: 'none',
            marginBottom: '20px'
          }}
        >
          {showForm ? 'Hide Form' : 'Add New Account'}
        </button>
      </div>

      {showForm && (
        <div style={{ marginBottom: '30px' }}>
          <AccountsForm 
            editingAccount={editingAccount}
            onCancel={handleCancel}
          />
        </div>
      )}

      <AccountsTable onEdit={handleEdit} />
    </div>
  );
};

export default AccountsManager;