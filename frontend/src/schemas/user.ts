export interface UserResponse {
  id: number;
  username: string;
  phone_number: string;
  email?: string;
  first_name: string;
  last_name: string;
  national_id?: string;
  role_id: number;
  branch_id?: number;
  is_active: boolean;
}

export interface CustomerCreate {
  phone_number: string;
  first_name: string;
  last_name: string;
  national_id?: string;
  group_id: number;
}
