import { Account } from './accounts';
import { Category } from './categories';
import { Budget } from './budgets';
import { Currency } from './currencies';

export interface Transaction {
  id: number;
  account: number;
  account_detail?: Account;
  transaction_type: 'income' | 'expense' | 'transfer';
  transaction_type_display: string;
  transaction_date: string;
  created_date: string;
  amount: string;
  description: string;
  category: number | null;
  category_detail?: Category | null;
  budget: number | null;
  budget_detail?: Budget | null;
  currency: number;
  currency_detail?: Currency;
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