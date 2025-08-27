import React, { useState, useEffect } from 'react';
import { useTransactions } from '../../hooks/useTransactions';
import { useAccounts } from '../../hooks/useAccounts';
import { useCategories } from '../../hooks/useCategories';
import { useBudgets } from '../../hooks/useBudgets';
import { useCurrencies } from '../../hooks/useCurrencies';
import { Transaction, CreateTransactionData } from '../../types/transactions';

interface TransactionsFormProps {
    editingTransaction?: Transaction | null;
    onCancel?: () => void;
}

const TransactionsForm: React.FC<TransactionsFormProps> = ({ editingTransaction, onCancel }) => {
    const { create, update } = useTransactions();
    const { accounts } = useAccounts();
    const { categories } = useCategories();
    const { budgets } = useBudgets();
    const { currencies } = useCurrencies();

    // Find principal currency
    const principalCurrency = currencies.find(currency => currency.principal);

    const [formData, setFormData] = useState<CreateTransactionData>({
        account: 0,
        transaction_type: 'expense',
        transaction_date: new Date().toISOString().split('T')[0],
        amount: '',
        description: '',
        category: null,
        budget: null,
        currency: 0,
    });

    // Set principal currency as default when currencies load
    useEffect(() => {
        if (principalCurrency && !editingTransaction) {
            setFormData(prev => ({
                ...prev,
                currency: principalCurrency.id
            }));
        }
    }, [principalCurrency, editingTransaction]);

    useEffect(() => {
        if (editingTransaction) {
            setFormData({
                account: editingTransaction.account.id,
                transaction_type: editingTransaction.transaction_type,
                transaction_date: editingTransaction.transaction_date.split('T')[0],
                amount: editingTransaction.amount,
                description: editingTransaction.description,
                category: editingTransaction.category?.id || null,
                budget: editingTransaction.budget?.id || null,
                currency: editingTransaction.currency.id,
            });
        }
    }, [editingTransaction]);

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();

        // Validate required fields
        if (!formData.account || !formData.currency || !formData.amount) {
            alert('Please fill in all required fields (Account, Currency, Amount)');
            return;
        }



        if (editingTransaction) {
            update.mutate({ id: editingTransaction.id, data: formData });
        } else {
            create.mutate(formData);
        }

        // Reset form
        setFormData({
            account: 0,
            transaction_type: 'expense',
            transaction_date: new Date().toISOString().split('T')[0],
            amount: '',
            description: '',
            category: null,
            budget: null,
            currency: principalCurrency?.id || 0,
        });

        if (onCancel) onCancel();
    };

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
        const { name, value } = e.target;

        setFormData(prev => ({
            ...prev,
            [name]: name === 'category' || name === 'budget' ? (value ? parseInt(value) : null) :
                name === 'account' || name === 'currency' ? (value ? parseInt(value) : 0) : value
        }));
    };

    return (
        <div>
            <h2>{editingTransaction ? 'Edit Transaction' : 'Create Transaction'}</h2>
            {currencies.length === 0 && (
                <div style={{ padding: '10px', backgroundColor: '#fff3cd', border: '1px solid #ffeaa7', marginBottom: '1rem' }}>
                    <strong>Note:</strong> No currencies found. Please add currencies first before creating transactions.
                </div>
            )}


            <form onSubmit={handleSubmit} style={{ maxWidth: '500px' }}>
                <div style={{ marginBottom: '1rem' }}>
                    <label htmlFor="account">Account *</label>
                    <select
                        id="account"
                        name="account"
                        value={formData.account}
                        onChange={handleChange}
                        required
                        style={{ width: '100%', padding: '8px', marginTop: '4px' }}
                    >
                        <option value="">Select an account</option>
                        {accounts.map(account => (
                            <option key={account.id} value={account.id}>
                                {account.name} ({account.account_type})
                            </option>
                        ))}
                    </select>
                </div>

                <div style={{ marginBottom: '1rem' }}>
                    <label htmlFor="transaction_type">Transaction Type *</label>
                    <select
                        id="transaction_type"
                        name="transaction_type"
                        value={formData.transaction_type}
                        onChange={handleChange}
                        required
                        style={{ width: '100%', padding: '8px', marginTop: '4px' }}
                    >
                        <option value="income">Income</option>
                        <option value="expense">Expense</option>
                        <option value="transfer">Transfer</option>
                    </select>
                </div>

                <div style={{ marginBottom: '1rem' }}>
                    <label htmlFor="transaction_date">Date *</label>
                    <input
                        type="date"
                        id="transaction_date"
                        name="transaction_date"
                        value={formData.transaction_date}
                        onChange={handleChange}
                        required
                        style={{ width: '100%', padding: '8px', marginTop: '4px' }}
                    />
                </div>

                <div style={{ marginBottom: '1rem' }}>
                    <label htmlFor="amount">Amount *</label>
                    <input
                        type="number"
                        step="0.01"
                        id="amount"
                        name="amount"
                        value={formData.amount}
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
                    <label htmlFor="description">Description</label>
                    <textarea
                        id="description"
                        name="description"
                        value={formData.description}
                        onChange={handleChange}
                        rows={3}
                        style={{ width: '100%', padding: '8px', marginTop: '4px' }}
                    />
                </div>

                <div style={{ marginBottom: '1rem' }}>
                    <label htmlFor="category">Category</label>
                    <select
                        id="category"
                        name="category"
                        value={formData.category || ''}
                        onChange={handleChange}
                        style={{ width: '100%', padding: '8px', marginTop: '4px' }}
                    >
                        <option value="">No category</option>
                        {categories.map(category => (
                            <option key={category.id} value={category.id}>
                                {category.name}
                            </option>
                        ))}
                    </select>
                </div>

                <div style={{ marginBottom: '1rem' }}>
                    <label htmlFor="budget">Budget</label>
                    <select
                        id="budget"
                        name="budget"
                        value={formData.budget || ''}
                        onChange={handleChange}
                        style={{ width: '100%', padding: '8px', marginTop: '4px' }}
                    >
                        <option value="">No budget</option>
                        {budgets.map(budget => (
                            <option key={budget.id} value={budget.id}>
                                {budget.name}
                            </option>
                        ))}
                    </select>
                </div>

                <div style={{ display: 'flex', gap: '1rem' }}>
                    <button
                        type="submit"
                        style={{ padding: '10px 20px', backgroundColor: '#007bff', color: 'white', border: 'none' }}
                    >
                        {editingTransaction ? 'Update' : 'Create'} Transaction
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

export default TransactionsForm;