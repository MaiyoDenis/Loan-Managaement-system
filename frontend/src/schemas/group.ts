export interface GroupResponse {
  id: number;
  name: string;
  description?: string;
  max_members: number;
  branch_id: number;
  loan_officer_id: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}
