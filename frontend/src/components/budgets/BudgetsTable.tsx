import React from 'react';
import { useBudgets } from '../../hooks/useBudgets';
import { Budget } from '../../types/budgets';

interface BudgetsTableProps {
  onEdit?: (budget: Budget) => void;
}

const BudgetsTable: React.FC<BudgetsTableProps> = ({ onEdit }) => {
  const { budgets, isLoading, remove } = useBudgets();

  const handleDelete = (id: number) => {
    if (window.confirm('Are you sure you want to delete this budget?')) {
      remove.mutate(id);
    }
  };

  if (isLoading) return <p>Loading budgets...</p>;

  return (
    <div>
      <h2>Budgets</h2>
      {budgets.length === 0 ? (
        <p>No budgets found.</p>
      ) : (
        <table style={{ borderCollapse: 'collapse', width: '100%' }}>
          <thead>
            <tr>
              <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left', padding: '8px' }}>Name</th>
              <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left', padding: '8px' }}>Min Amount</th>
              <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left', padding: '8px' }}>Max Amount</th>
              <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left', padding: '8px' }}>Start Date</th>
              <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left', padding: '8px' }}>End Date</th>
              <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left', padding: '8px' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {budgets.map((budget) => (
              <tr key={budget.id}>
                <td style={{ padding: '8px' }}>{budget.name}</td>
                <td style={{ padding: '8px' }}>{budget.min_amount}</td>
                <td style={{ padding: '8px' }}>{budget.max_amount}</td>
                <td style={{ padding: '8px' }}>
                  {new Date(budget.start_date).toLocaleDateString()}
                </td>
                <td style={{ padding: '8px' }}>
                  {new Date(budget.end_date).toLocaleDateString()}
                </td>
                <td style={{ padding: '8px' }}>
                  {onEdit && (
                    <button 
                      onClick={() => onEdit(budget)}
                      style={{ marginRight: '8px' }}
                    >
                      Edit
                    </button>
                  )}
                  <button 
                    onClick={() => handleDelete(budget.id)}
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

export default BudgetsTable;