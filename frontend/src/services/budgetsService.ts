import api from '../api';
import { Budget, CreateBudgetData } from '../types/budgets';

export const fetchBudgets = () => api.get<Budget[]>('/api/budgets/');
export const createBudget = (data: CreateBudgetData) => api.post('/api/budgets/', data);
export const updateBudget = (id: number, data: Partial<CreateBudgetData>) => api.put(`/api/budgets/${id}/`, data);
export const deleteBudget = (id: number) => api.delete(`/api/budgets/${id}/`);