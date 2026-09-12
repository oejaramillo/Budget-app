import { createResourceHooks } from './createResourceHooks'
import {
  createAccount,
  deleteAccount,
  fetchAccounts,
  updateAccount,
} from '../services/accountsService'

/**
 * Accounts list plus create/update/delete mutations.
 *
 * Mutations invalidate `net-worth` and `currency-summary` too, because both are
 * derived from account balances.
 */
export const useAccounts = createResourceHooks({
  resource: 'accounts',
  list: fetchAccounts,
  create: createAccount,
  update: updateAccount,
  remove: deleteAccount,
  invalidate: ['net-worth', 'currency-summary'],
})
