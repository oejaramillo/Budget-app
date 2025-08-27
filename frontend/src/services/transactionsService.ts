import api from '../api';
import { Transaction, CreateTransactionData } from '../types/transactions';

export const fetchTransactions = () => api.get<Transaction[]>('/api/transactions/');
export const createTransaction = (data: CreateTransactionData) => api.post('/api/transactions/', data);
export const updateTransaction = (id: number, data: Partial<CreateTransactionData>) => api.put(`/api/transactions/${id}/`, data);
export const deleteTransaction = (id: number) => api.delete(`/api/transactions/${id}/`);