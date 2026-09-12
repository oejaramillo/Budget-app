import { createResourceHooks } from './createResourceHooks'
import {
  createBudget,
  deleteBudget,
  fetchBudgets,
  updateBudget,
} from '../services/budgetsService'

/**
 * Budgets list plus mutations. Writes invalidate the transaction summary because
 * spend is calculated from transactions linked to the budget.
 */
export const useBudgets = createResourceHooks({
  resource: 'budgets',
  list: fetchBudgets,
  create: createBudget,
  update: updateBudget,
  remove: deleteBudget,
  invalidate: ['transaction-summary', 'budget-status'],
})
