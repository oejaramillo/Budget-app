export interface Account {
    id: number;
    user: number;
    name: string;
    account_type: 'checking' | 'savings' | 'credit';
    created_date: string;
    balance: string;
    currency: string; 
    institution?: string | null;
    official_number?: string | null;
    last_updated: string;
}