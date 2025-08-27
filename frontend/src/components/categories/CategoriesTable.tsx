import React from 'react';
import { useCategories } from '../../hooks/useCategories';
import { Category } from '../../types/categories';

interface CategoriesTableProps {
  onEdit?: (category: Category) => void;
}

const CategoriesTable: React.FC<CategoriesTableProps> = ({ onEdit }) => {
  const { categories, isLoading, remove } = useCategories();

  const handleDelete = (id: number) => {
    if (window.confirm('Are you sure you want to delete this category?')) {
      remove.mutate(id);
    }
  };

  if (isLoading) return <p>Loading categories...</p>;

  return (
    <div>
      <h2>Categories</h2>
      {categories.length === 0 ? (
        <p>No categories found.</p>
      ) : (
        <table style={{ borderCollapse: 'collapse', width: '100%' }}>
          <thead>
            <tr>
              <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left', padding: '8px' }}>Name</th>
              <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left', padding: '8px' }}>Budget</th>
              <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left', padding: '8px' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {categories.map((category) => (
              <tr key={category.id}>
                <td style={{ padding: '8px' }}>{category.name}</td>
                <td style={{ padding: '8px' }}>
                  {category.budget ? `Budget ID: ${category.budget}` : 'No budget assigned'}
                </td>
                <td style={{ padding: '8px' }}>
                  {onEdit && (
                    <button 
                      onClick={() => onEdit(category)}
                      style={{ marginRight: '8px' }}
                    >
                      Edit
                    </button>
                  )}
                  <button 
                    onClick={() => handleDelete(category.id)}
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

export default CategoriesTable;