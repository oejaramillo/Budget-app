import React, { useState } from 'react';
import CategoriesTable from './categories/CategoriesTable';
import CategoriesForm from './categories/CategoriesForm';
import { Category } from '../types/categories';

const CategoriesManager: React.FC = () => {
  const [editingCategory, setEditingCategory] = useState<Category | null>(null);
  const [showForm, setShowForm] = useState(false);

  const handleEdit = (category: Category) => {
    setEditingCategory(category);
    setShowForm(true);
  };

  const handleCancel = () => {
    setEditingCategory(null);
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
          {showForm ? 'Hide Form' : 'Add New Category'}
        </button>
      </div>

      {showForm && (
        <div style={{ marginBottom: '30px' }}>
          <CategoriesForm 
            editingCategory={editingCategory}
            onCancel={handleCancel}
          />
        </div>
      )}

      <CategoriesTable onEdit={handleEdit} />
    </div>
  );
};

export default CategoriesManager;