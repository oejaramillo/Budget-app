export interface Currency {
  id: number;
  name: string;
  code: string;
  exchange_rate: number;
  principal: boolean;
  is_active: boolean;
}