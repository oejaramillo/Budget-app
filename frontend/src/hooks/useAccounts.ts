import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { fetchAccounts, createAccount, deleteAccount } from '../services/accountsService';
import { Account } from '../types/accounts';

export const useAccounts = () => {
    const queryClient = useQueryClient();
    const { data, isLoading, error } = useQuery({
        queryKey: ['accounts'],
        queryFn: fetchAccounts,
    });

    // Type the mutation: <Response, Error, Variables>
    const create = useMutation({
        mutationFn: (data: Partial<Account>) => createAccount(data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['accounts'] });
        },
    });

    const remove = useMutation({
        mutationFn: (id: number) => deleteAccount(id),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['accounts'] });
        },
    });

    return {
        accounts: data,
        isLoading,
        error,
        create,
        remove,
    };
};