import { useState } from 'react'

import { useCategories } from '../../hooks/useCategories'
import { useBudgets } from '../../hooks/useBudgets'
import { useForm } from '../../hooks/useForm'
import { Alert, DataTable, EmptyState } from '../ui/Feedback'
import { SelectField, TextField } from '../ui/FormFields'
import FormPanel from '../ui/FormPanel'

const emptyCategory = { name: '', budget: '' }

/** Categories CRUD: free-form labels, optionally tied to one budget. */
export default function CategoriesManager() {
  const { categories, isLoading, create, update, remove } = useCategories()
  const { budgets } = useBudgets()

  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState(null)

  const budgetOptions = budgets.map((budget) => ({ value: budget.id, label: budget.name }))
  const budgetName = (id) => budgets.find((budget) => budget.id === id)?.name ?? '—'

  const form = useForm({
    initialValues: emptyCategory,
    onSubmit: async (values) => {
      const payload = {
        name: values.name.trim(),
        budget: values.budget ? Number(values.budget) : null,
      }
      if (editingId) {
        return update.mutateAsync({ id: editingId, data: payload })
      }
      return create.mutateAsync(payload)
    },
    onSuccess: () => {
      form.reset({ ...emptyCategory })
      setEditingId(null)
      setShowForm(false)
    },
  })

  const startEdit = (category) => {
    setEditingId(category.id)
    setShowForm(true)
    form.reset({
      name: category.name,
      budget: category.budget ? String(category.budget) : '',
    })
  }

  const cancelEdit = () => {
    setEditingId(null)
    setShowForm(false)
    form.reset({ ...emptyCategory })
  }

  const handleDelete = (category) => {
    if (!window.confirm(`Delete category "${category.name}"?`)) return
    remove.mutate(category.id)
  }

  const mutationError = create.error ?? update.error ?? remove.error

  return (
    <div>
      <FormPanel
        title="Categories"
        isOpen={showForm}
        onToggle={() => (showForm ? cancelEdit() : setShowForm(true))}
        openLabel="Add category"
      >
        <form onSubmit={form.handleSubmit}>
          <Alert>{form.formError}</Alert>
          {mutationError && <Alert>{mutationError.message}</Alert>}

          <div className="inline-fields">
            <TextField
              label="Name *"
              name="name"
              value={form.values.name}
              onChange={form.handleChange}
              error={form.errors.name}
              required
            />
            <SelectField
              label="Budget"
              name="budget"
              value={form.values.budget}
              onChange={form.handleChange}
              options={budgetOptions}
              placeholder="No budget assigned"
              error={form.errors.budget}
            />
          </div>

          <div style={{ display: 'flex', gap: '1rem' }}>
            <button type="submit" className="btn btn-primary" disabled={form.isSubmitting}>
              {editingId ? 'Save changes' : 'Create category'}
            </button>
            <button type="button" className="btn btn-outline" onClick={cancelEdit}>
              Cancel
            </button>
          </div>
        </form>
      </FormPanel>

      {categories.length === 0 && !isLoading ? (
        <EmptyState message="No categories yet. Group your spending to make reports useful." />
      ) : (
        <DataTable
          columns={['Name', 'Budget', 'Transactions', 'Actions']}
          isLoading={isLoading}
        >
          {categories.map((category) => (
            <tr key={category.id}>
              <td>{category.name}</td>
              <td>{category.budget ? budgetName(category.budget) : '—'}</td>
              <td className="numeric">{category.transaction_count ?? 0}</td>
              <td>
                <button type="button" className="btn btn-ghost" onClick={() => startEdit(category)}>
                  Edit
                </button>
                <button
                  type="button"
                  className="btn btn-danger btn-sm"
                  onClick={() => handleDelete(category)}
                >
                  Delete
                </button>
              </td>
            </tr>
          ))}
        </DataTable>
      )}
    </div>
  )
}
