export interface Budget {
  id: number;
  user: string;
  name: string;
  max_amount: string;
  min_amount: string;
  currency: number;
  start_date: string;
  end_date: string;
}

export interface CreateBudgetData {
  name: string;
  max_amount: string;
  min_amount: string;
  currency: number;
  start_date: string;
  end_date: string;
}