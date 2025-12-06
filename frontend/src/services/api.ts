import axios from 'axios';
import type { AxiosResponse } from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken
          });
          
          const { access_token } = response.data;
          localStorage.setItem('access_token', access_token);
          
          // Retry original request
          error.config.headers.Authorization = `Bearer ${access_token}`;
          return api.request(error.config);
        } catch (refreshError) {
          // Refresh failed, redirect to login
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/login';
        }
      }
    }
    return Promise.reject(error);
  }
);

// Authentication API
export const authAPI = {
  login: (username: string, password: string) =>
    api.post('/auth/login', { username, password }).then(res => res.data),
    
  logout: () =>
    api.post('/auth/logout').then(res => res.data),
    
  getCurrentUser: (token?: string) => {
    const headers = token ? { Authorization: `Bearer ${token}` } : {};
    return api.get('/auth/me', { headers }).then(res => res.data);
  },
    
  changePassword: (currentPassword: string, newPassword: string, confirmPassword: string) =>
    api.post('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
      confirm_password: confirmPassword
    }).then(res => res.data),
    
  verifyToken: () =>
    api.get('/auth/verify-token').then(res => res.data),
};

// Users API
export const usersAPI = {
  getUsers: (params?: any) =>
    api.get('/users', { params }).then(res => res.data),
    
  createUser: (userData: any) =>
    api.post('/users', userData).then(res => res.data),
    
  updateUser: (id: number, userData: any) =>
    api.put(`/users/${id}`, userData).then(res => res.data),
    
  getUser: (id: number) =>
    api.get(`/users/${id}`).then(res => res.data),
    
  transferUser: (transferData: any) =>
    api.post('/users/transfer', transferData).then(res => res.data),
    
  createCustomer: (customerData: any) =>
    api.post('/users/customers', customerData).then(res => res.data),
    
  getOnlineUsers: () =>
    api.get('/users/online/summary').then(res => res.data),
    
  getGroupMembers: (groupId: number) =>
    api.get(`/users/groups/${groupId}/members`).then(res => res.data),
};

// Branches API
export const branchesAPI = {
  getBranches: (params?: any) =>
    api.get('/branches', { params }).then(res => res.data),
    
  createBranch: (branchData: any) =>
    api.post('/branches', branchData).then(res => res.data),
    
  updateBranch: (id: number, branchData: any) =>
    api.put(`/branches/${id}`, branchData).then(res => res.data),
    
  getBranch: (id: number) =>
    api.get(`/branches/${id}`).then(res => res.data),
    
  getBranchStats: (id: number) =>
    api.get(`/branches/${id}/stats`).then(res => res.data),
};

// Loan Products API
export const loanProductsAPI = {
  getProducts: (params?: any) =>
    api.get('/loan-products', { params }).then(res => res.data),
    
  createProduct: (productData: FormData) =>
    api.post('/loan-products', productData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    }).then(res => res.data),
    
  updateProduct: (id: number, productData: any) =>
    api.put(`/loan-products/${id}`, productData).then(res => res.data),
    
  deleteProduct: (id: number) =>
    api.delete(`/loan-products/${id}`).then(res => res.data),
    
  getProductInventory: (id: number) =>
    api.get(`/loan-products/${id}/inventory`).then(res => res.data),
    
  getProfitMargins: () =>
    api.get('/loan-products/analytics/profit-margins').then(res => res.data),
};

// Product Categories API
export const productCategoriesAPI = {
  getCategories: () =>
    api.get('/loan-products/categories').then(res => res.data),
    
  createCategory: (categoryData: any) =>
    api.post('/loan-products/categories', categoryData).then(res => res.data),
};

// Loan Types API
export const loanTypesAPI = {
  getLoanTypes: (params?: any) =>
    api.get('/loan-types', { params }).then(res => res.data),
    
  createLoanType: (loanTypeData: any) =>
    api.post('/loan-types', loanTypeData).then(res => res.data),
    
  updateLoanType: (id: number, loanTypeData: any) =>
    api.put(`/loan-types/${id}`, loanTypeData).then(res => res.data),
    
  deleteLoanType: (id: number) =>
    api.delete(`/loan-types/${id}`).then(res => res.data),
    
  calculateLoan: (calculationData: any) =>
    api.post('/loan-types/calculate', calculationData).then(res => res.data),
    
  suggestLoanType: (amount: number, branchId?: number) =>
    api.post('/loan-types/suggest-loan-type', null, {
      params: { amount, branch_id: branchId }
    }).then(res => res.data),
};

// Accounts API
export const accountsAPI = {
  getSavingsAccounts: (branchId?: number) =>
    api.get('/accounts/savings', { params: { branch_id: branchId } }).then(res => res.data),
    
  getDrawdownAccounts: (branchId?: number) =>
    api.get('/accounts/drawdown', { params: { branch_id: branchId } }).then(res => res.data),
    
  getUserAccountSummary: (userId: number) =>
    api.get(`/accounts/user/${userId}/summary`).then(res => res.data),
    
  transferFunds: (transferData: any) =>
    api.post('/accounts/transfer', transferData).then(res => res.data),
    
  depositFunds: (depositData: any) =>
    api.post('/accounts/deposit', depositData).then(res => res.data),
    
  getTransactions: (params?: any) =>
    api.get('/accounts/transactions', { params }).then(res => res.data),
};

// Loan Applications API
export const loanApplicationsAPI = {
  getApplications: (params?: any) =>
    api.get('/loan-applications', { params }).then(res => res.data),
    
  createApplication: (applicationData: any) =>
    api.post('/loan-applications', applicationData).then(res => res.data),
    
  getApplication: (id: number) =>
    api.get(`/loan-applications/${id}`).then(res => res.data),
    
  updateApplicationStatus: (id: number, statusData: any) =>
    api.put(`/loan-applications/${id}/status`, statusData).then(res => res.data),
    
  cancelApplication: (id: number) =>
    api.delete(`/loan-applications/${id}`).then(res => res.data),
    
  checkEligibility: (userId: number) =>
    api.get(`/loan-applications/eligibility/${userId}`).then(res => res.data),
};

// Analytics API
export const analyticsAPI = {
  getAnalytics: (params?: any) =>
    api.get('/analytics/dashboard', { params }).then(res => res.data),
};

export default api;
