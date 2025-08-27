import { Account } from './accounts';
import { Category } from './categories';
import { Budget } from './budgets';
import { Currency } from './currencies';

export interface Transaction {
  id: number;
  account: Account;
  transaction_type: 'income' | 'expense' | 'transfer';
  transaction_type_display: string;
  transaction_date: string;
  created_date: string;
  amount: string;
  description: string;
  category: Category | null;
  budget: Budget | null;
  currency: Currency;
  user: string;
}

export interface CreateTransactionData {
  account: number;
  transaction_type: 'income' | 'expense' | 'transfer';
  transaction_date: string;
  amount: string;
  description: string;
  category?: number | null;
  budget?: number | null;
  currency: number;
}