import axios from 'axios';
import { GroupResponse } from '../schemas/group';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

const groupApi = axios.create({
  baseURL: `${API_URL}/groups`,
  withCredentials: true,
});

export const getGroups = async (): Promise<GroupResponse[]> => {
  const response = await groupApi.get('/');
  return response.data;
};

export const getGroup = async (groupId: number): Promise<GroupResponse> => {
  const response = await groupApi.get(`/${groupId}`);
  return response.data;
};
