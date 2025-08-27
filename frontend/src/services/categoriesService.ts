import api from '../api';
import { Category, CreateCategoryData } from '../types/categories';

export const fetchCategories = () => api.get<Category[]>('/api/categories/');
export const createCategory = (data: CreateCategoryData) => api.post('/api/categories/', data);
export const updateCategory = (id: number, data: Partial<CreateCategoryData>) => api.put(`/api/categories/${id}/`, data);
export const deleteCategory = (id: number) => api.delete(`/api/categories/${id}/`);