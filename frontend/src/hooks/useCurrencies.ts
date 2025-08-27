import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchCurrencies, createCurrency, deleteCurrency } from '../services/currenciesService';
import { Currency } from '../types/currencies';

export const useCurrencies = () => {
  const queryClient = useQueryClient();
  const { data, isLoading, error } = useQuery({
    queryKey: ['currencies'],
    queryFn: fetchCurrencies,
  });

  const create = useMutation({
    mutationFn: (data: Partial<Currency>) => createCurrency(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['currencies'] });
    },
  });

  const remove = useMutation({
    mutationFn: (id: number) => deleteCurrency(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['currencies'] });
    },
  });

  // Debug logging
  console.log('Currencies hook:', { 
    currencies: data?.data, 
    isLoading, 
    error: error?.message,
    principalCurrency: data?.data?.find(c => c.principal)
  });

  return {
    currencies: data?.data ?? [],
    isLoading,
    error,
    create,
    remove,
  };
};