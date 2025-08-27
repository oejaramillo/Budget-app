import React, { useState } from 'react';
import BudgetsTable from './budgets/BudgetsTable';
import BudgetsForm from './budgets/BudgetsForm';
import { Budget } from '../types/budgets';

const BudgetsManager: React.FC = () => {
  const [editingBudget, setEditingBudget] = useState<Budget | null>(null);
  const [showForm, setShowForm] = useState(false);

  const handleEdit = (budget: Budget) => {
    setEditingBudget(budget);
    setShowForm(true);
  };

  const handleCancel = () => {
    setEditingBudget(null);
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
          {showForm ? 'Hide Form' : 'Add New Budget'}
        </button>
      </div>

      {showForm && (
        <div style={{ marginBottom: '30px' }}>
          <BudgetsForm 
            editingBudget={editingBudget}
            onCancel={handleCancel}
          />
        </div>
      )}

      <BudgetsTable onEdit={handleEdit} />
    </div>
  );
};

export default BudgetsManager;