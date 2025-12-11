export interface LoanProductResponse {
  id: number;
  name: string;
  category_id: number;
  description?: string;
  selling_price: number;
  image_url?: string;
  created_by: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}
