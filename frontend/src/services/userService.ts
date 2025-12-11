import axios from 'axios';
import type { UserResponse, CustomerCreate } from '../schemas/user';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

const userApi = axios.create({
  baseURL: `${API_URL}/users`,
  withCredentials: true,
});

export const getStaffForAssignment = async (): Promise<UserResponse[]> => {
  const response = await userApi.get('/staff-for-assignment');
  return response.data;
};

export const getGroupMembers = async (groupId: number): Promise<UserResponse[]> => {
  const response = await userApi.get(`/groups/${groupId}/members`);
  return response.data;
};

export const createCustomer = async (customerData: CustomerCreate): Promise<UserResponse> => {
  const response = await userApi.post('/customers', customerData);
  return response.data;
};
