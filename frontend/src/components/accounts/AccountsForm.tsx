import React, { useState, useEffect } from 'react';
import { useAccounts } from '../../hooks/useAccounts';
import { useCurrencies } from '../../hooks/useCurrencies';
import { Account } from '../../types/accounts';
import { CreateAccountData } from '../../services/accountsService';

interface AccountsFormProps {
  editingAccount?: Account | null;
  onCancel?: () => void;
}

const AccountsForm: React.FC<AccountsFormProps> = ({ editingAccount, onCancel }) => {
  const { create, update } = useAccounts();
  const { currencies } = useCurrencies();

  // Find principal currency
  const principalCurrency = currencies.find(currency => currency.principal);

  const [formData, setFormData] = useState<CreateAccountData>({
    name: '',
    account_type: 'checking',
    balance: '',
    currency: 0,
    institution: '',
    official_number: '',
  });

  // Set principal currency as default when currencies load
  useEffect(() => {
    if (principalCurrency && !editingAccount && formData.currency === 0) {
      setFormData(prev => ({
        ...prev,
        currency: principalCurrency.id
      }));
    }
  }, [principalCurrency, editingAccount, formData.currency]);

  useEffect(() => {
    if (editingAccount) {
      setFormData({
        name: editingAccount.name,
        account_type: editingAccount.account_type,
        balance: editingAccount.balance,
        currency: parseInt(editingAccount.currency),
        institution: editingAccount.institution || '',
        official_number: editingAccount.official_number || '',
      });
    }
  }, [editingAccount]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    // Validate required fields
    if (!formData.name || !formData.currency || !formData.balance) {
      alert('Please fill in all required fields (Name, Currency, Balance)');
      return;
    }

    console.log('Submitting account:', formData);
    
    if (editingAccount) {
      update.mutate({ id: editingAccount.id, data: formData });
    } else {
      create.mutate(formData);
    }
    
    // Reset form
    setFormData({
      name: '',
      account_type: 'checking',
      balance: '',
      currency: principalCurrency?.id || 0,
      institution: '',
      official_number: '',
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

  return (
    <div>
      <h2>{editingAccount ? 'Edit Account' : 'Create Account'}</h2>
      <form onSubmit={handleSubmit} style={{ maxWidth: '500px' }}>
        <div style={{ marginBottom: '1rem' }}>
          <label htmlFor="name">Account Name *</label>
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
          <label htmlFor="account_type">Account Type *</label>
          <select
            id="account_type"
            name="account_type"
            value={formData.account_type}
            onChange={handleChange}
            required
            style={{ width: '100%', padding: '8px', marginTop: '4px' }}
          >
            <option value="checking">Checking</option>
            <option value="savings">Savings</option>
            <option value="credit">Credit</option>
          </select>
        </div>

        <div style={{ marginBottom: '1rem' }}>
          <label htmlFor="balance">Initial Balance *</label>
          <input
            type="number"
            step="0.01"
            id="balance"
            name="balance"
            value={formData.balance}
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
            <option value="">Select a currency</option>
            {currencies.map(currency => (
              <option key={currency.id} value={currency.id}>
                {currency.code} - {currency.name} {currency.principal ? '(Principal)' : ''}
              </option>
            ))}
          </select>
        </div>

        <div style={{ marginBottom: '1rem' }}>
          <label htmlFor="institution">Institution</label>
          <input
            type="text"
            id="institution"
            name="institution"
            value={formData.institution}
            onChange={handleChange}
            style={{ width: '100%', padding: '8px', marginTop: '4px' }}
          />
        </div>

        <div style={{ marginBottom: '1rem' }}>
          <label htmlFor="official_number">Account Number</label>
          <input
            type="text"
            id="official_number"
            name="official_number"
            value={formData.official_number}
            onChange={handleChange}
            style={{ width: '100%', padding: '8px', marginTop: '4px' }}
          />
        </div>

        <div style={{ display: 'flex', gap: '1rem' }}>
          <button 
            type="submit"
            style={{ padding: '10px 20px', backgroundColor: '#007bff', color: 'white', border: 'none' }}
          >
            {editingAccount ? 'Update' : 'Create'} Account
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

export default AccountsForm;