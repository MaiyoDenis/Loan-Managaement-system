import axios from 'axios';
import { LoanProductResponse } from '../schemas/loan';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

const loanProductApi = axios.create({
  baseURL: `${API_URL}/loan-products`,
  withCredentials: true,
});

export const getLoanProducts = async (): Promise<LoanProductResponse[]> => {
  const response = await loanProductApi.get('/');
  return response.data;
};
