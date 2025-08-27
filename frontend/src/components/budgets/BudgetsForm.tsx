import React, { useState, useEffect } from 'react';
import { useBudgets } from '../../hooks/useBudgets';
import { useCurrencies } from '../../hooks/useCurrencies';
import { Budget, CreateBudgetData } from '../../types/budgets';

interface BudgetsFormProps {
  editingBudget?: Budget | null;
  onCancel?: () => void;
}

const BudgetsForm: React.FC<BudgetsFormProps> = ({ editingBudget, onCancel }) => {
  const { create, update } = useBudgets();
  const { currencies, isLoading: currenciesLoading } = useCurrencies();

  // Find principal currency
  const principalCurrency = currencies.find(currency => currency.principal);

  const [formData, setFormData] = useState<CreateBudgetData>({
    name: '',
    max_amount: '',
    min_amount: '',
    currency: 0,
    start_date: '',
    end_date: '',
  });

  // Set principal currency as default when currencies load
  useEffect(() => {
    if (principalCurrency && !editingBudget) {
      setFormData(prev => ({
        ...prev,
        currency: principalCurrency.id
      }));
    }
  }, [principalCurrency, editingBudget]);

  useEffect(() => {
    if (editingBudget) {
      setFormData({
        name: editingBudget.name,
        max_amount: editingBudget.max_amount,
        min_amount: editingBudget.min_amount,
        currency: editingBudget.currency,
        start_date: editingBudget.start_date.split('T')[0],
        end_date: editingBudget.end_date.split('T')[0],
      });
    }
  }, [editingBudget]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    // Validate currency selection
    if (!formData.currency || formData.currency === 0) {
      alert('Please select a currency');
      return;
    }

    // Validate that min_amount <= max_amount
    if (parseFloat(formData.min_amount) > parseFloat(formData.max_amount)) {
      alert('Minimum amount cannot be greater than maximum amount');
      return;
    }

    // Validate that start_date < end_date
    if (new Date(formData.start_date) >= new Date(formData.end_date)) {
      alert('Start date must be before end date');
      return;
    }

    console.log('Submitting budget:', formData);
    console.log('JWT Token exists:', !!localStorage.getItem('access'));
    console.log('Principal currency:', principalCurrency);
    console.log('Available currencies:', currencies.length);
    
    if (editingBudget) {
      update.mutate({ id: editingBudget.id, data: formData });
    } else {
      create.mutate(formData);
    }
    
    // Reset form
    setFormData({
      name: '',
      max_amount: '',
      min_amount: '',
      currency: principalCurrency?.id || 0,
      start_date: '',
      end_date: '',
    });
    
    if (onCancel) onCancel();
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: name === 'currency' ? parseInt(value) : value
    }));
  };

  if (currenciesLoading) {
    return <div>Loading currencies...</div>;
  }

  return (
    <div>
      <h2>{editingBudget ? 'Edit Budget' : 'Create Budget'}</h2>
      <form onSubmit={handleSubmit} style={{ maxWidth: '500px' }}>
        <div style={{ marginBottom: '1rem' }}>
          <label htmlFor="name">Budget Name *</label>
          <input
            type="text"
            id="name"
            name="name"
            value={formData.name}
            onChange={handleChange}
            required
            style={{ width: '100%', padding: '8px', marginTop: '4px' }}
          />
        </div>

        <div style={{ marginBottom: '1rem' }}>
          <label htmlFor="currency">Currency *</label>
          <select
            id="currency"
            name="currency"
            value={formData.currency}
            onChange={handleChange}
            required
            style={{ width: '100%', padding: '8px', marginTop: '4px' }}
          >
            {!formData.currency && <option value="">Select a currency</option>}
            {currencies.map(currency => (
              <option key={currency.id} value={currency.id}>
                {currency.code} - {currency.name} {currency.principal ? '(Principal)' : ''}
              </option>
            ))}
          </select>
        </div>

        <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem' }}>
          <div style={{ flex: 1 }}>
            <label htmlFor="min_amount">Minimum Amount *</label>
            <input
              type="number"
              step="0.01"
              id="min_amount"
              name="min_amount"
              value={formData.min_amount}
              onChange={handleChange}
              required
              style={{ width: '100%', padding: '8px', marginTop: '4px' }}
            />
          </div>
          <div style={{ flex: 1 }}>
            <label htmlFor="max_amount">Maximum Amount *</label>
            <input
              type="number"
              step="0.01"
              id="max_amount"
              name="max_amount"
              value={formData.max_amount}
              onChange={handleChange}
              required
              style={{ width: '100%', padding: '8px', marginTop: '4px' }}
            />
          </div>
        </div>

        <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem' }}>
          <div style={{ flex: 1 }}>
            <label htmlFor="start_date">Start Date *</label>
            <input
              type="date"
              id="start_date"
              name="start_date"
              value={formData.start_date}
              onChange={handleChange}
              required
              style={{ width: '100%', padding: '8px', marginTop: '4px' }}
            />
          </div>
          <div style={{ flex: 1 }}>
            <label htmlFor="end_date">End Date *</label>
            <input
              type="date"
              id="end_date"
              name="end_date"
              value={formData.end_date}
              onChange={handleChange}
              required
              style={{ width: '100%', padding: '8px', marginTop: '4px' }}
            />
          </div>
        </div>

        <div style={{ display: 'flex', gap: '1rem' }}>
          <button 
            type="submit"
            style={{ padding: '10px 20px', backgroundColor: '#007bff', color: 'white', border: 'none' }}
          >
            {editingBudget ? 'Update' : 'Create'} Budget
          </button>
          {onCancel && (
            <button 
              type="button" 
              onClick={onCancel}
              style={{ padding: '10px 20px', backgroundColor: '#6c757d', color: 'white', border: 'none' }}
            >
              Cancel
            </button>
          )}
        </div>
      </form>
    </div>
  );
};

export default BudgetsForm;