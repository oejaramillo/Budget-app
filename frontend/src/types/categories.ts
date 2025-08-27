export interface Category {
  id: number;
  user: string;
  name: string;
  budget: number | null;
}

export interface CreateCategoryData {
  name: string;
  budget?: number | null;
}