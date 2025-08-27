import React, { useState } from 'react';
import TransactionsTable from './transactions/TransactionsTable';
import TransactionsForm from './transactions/TransactionsForm';
import { Transaction } from '../types/transactions';

const TransactionsManager: React.FC = () => {
  const [editingTransaction, setEditingTransaction] = useState<Transaction | null>(null);
  const [showForm, setShowForm] = useState(false);

  const handleEdit = (transaction: Transaction) => {
    setEditingTransaction(transaction);
    setShowForm(true);
  };

  const handleCancel = () => {
    setEditingTransaction(null);
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
          {showForm ? 'Hide Form' : 'Add New Transaction'}
        </button>
      </div>

      {showForm && (
        <div style={{ marginBottom: '30px' }}>
          <TransactionsForm 
            editingTransaction={editingTransaction}
            onCancel={handleCancel}
          />
        </div>
      )}

      <TransactionsTable onEdit={handleEdit} />
    </div>
  );
};

export default TransactionsManager;