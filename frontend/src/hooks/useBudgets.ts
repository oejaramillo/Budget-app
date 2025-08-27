import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchBudgets, createBudget, updateBudget, deleteBudget } from '../services/budgetsService';
import { Budget, CreateBudgetData } from '../types/budgets';

export const useBudgets = () => {
  const queryClient = useQueryClient();
  
  const { data, isLoading, error } = useQuery({
    queryKey: ['budgets'],
    queryFn: fetchBudgets,
  });

  const create = useMutation({
    mutationFn: (data: CreateBudgetData) => createBudget(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['budgets'] });
    },
  });

  const update = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<CreateBudgetData> }) => 
      updateBudget(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['budgets'] });
    },
  });

  const remove = useMutation({
    mutationFn: (id: number) => deleteBudget(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['budgets'] });
    },
  });

  return {
    budgets: data?.data ?? [],
    isLoading,
    error,
    create,
    update,
    remove,
  };
};