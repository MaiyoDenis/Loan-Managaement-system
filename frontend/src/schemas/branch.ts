export interface BranchBase {
  name: string;
  code: string;
  address?: string;
  phone_number?: string;
}

export interface BranchCreate extends BranchBase {
  manager_id?: number;
  procurement_officer_id?: number;
}

export interface BranchUpdate {
  name?: string;
  address?: string;
  phone_number?: string;
  manager_id?: number;
  procurement_officer_id?: number;
  is_active?: boolean;
}

export interface BranchResponse extends BranchBase {
  id: number;
  is_active: boolean;
  manager_id?: number;
  procurement_officer_id?: number;
}
