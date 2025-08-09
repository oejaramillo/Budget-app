import api from '../api';
import { Currency } from '../types/currencies';

export const fetchCurrencies = () => api.get<Currency[]>('/api/currencies/');
export const createCurrency = (data: Partial<Currency>) => api.post('/api/currencies/', data);
export const deleteCurrency = (id: number) => api.delete(`/api/currencies/${id}/`);