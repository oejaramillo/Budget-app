import api from '../api';
import { Account } from '../types/accounts';

export interface CreateAccountData {
  name: string;
  account_type: 'checking' | 'savings' | 'credit';
  balance: string;
  currency: number;
  institution?: string;
  official_number?: string;
}

export const fetchAccounts = () => api.get<Account[]>('/api/accounts/');
export const createAccount = (data: CreateAccountData) => api.post('/api/accounts/', data);
export const updateAccount = (id: number, data: Partial<CreateAccountData>) => api.put(`/api/accounts/${id}/`, data);
export const deleteAccount = (id: number) => api.delete(`/api/accounts/${id}/`);