import React, { useState, useEffect } from 'react';
import { useCategories } from '../../hooks/useCategories';
import { useBudgets } from '../../hooks/useBudgets';
import { Category, CreateCategoryData } from '../../types/categories';

interface CategoriesFormProps {
  editingCategory?: Category | null;
  onCancel?: () => void;
}

const CategoriesForm: React.FC<CategoriesFormProps> = ({ editingCategory, onCancel }) => {
  const { create, update } = useCategories();
  const { budgets } = useBudgets();

  const [formData, setFormData] = useState<CreateCategoryData>({
    name: '',
    budget: null,
  });

  useEffect(() => {
    if (editingCategory) {
      setFormData({
        name: editingCategory.name,
        budget: editingCategory.budget,
      });
    }
  }, [editingCategory]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (editingCategory) {
      update.mutate({ id: editingCategory.id, data: formData });
    } else {
      create.mutate(formData);
    }
    
    // Reset form
    setFormData({
      name: '',
      budget: null,
    });
    
    if (onCancel) onCancel();
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: name === 'budget' ? (value ? parseInt(value) : null) : value
    }));
  };

  return (
    <div>
      <h2>{editingCategory ? 'Edit Category' : 'Create Category'}</h2>
      <form onSubmit={handleSubmit} style={{ maxWidth: '400px' }}>
        <div style={{ marginBottom: '1rem' }}>
          <label htmlFor="name">Category Name *</label>
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
          <label htmlFor="budget">Budget (Optional)</label>
          <select
            id="budget"
            name="budget"
            value={formData.budget || ''}
            onChange={handleChange}
            style={{ width: '100%', padding: '8px', marginTop: '4px' }}
          >
            <option value="">No budget assigned</option>
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
            {editingCategory ? 'Update' : 'Create'} Category
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

export default CategoriesForm;