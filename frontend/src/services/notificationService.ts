import api from './api';

export type NotificationItem = {
  id: string;
  message: string;
  type: 'info' | 'success' | 'warning' | 'error';
  created_at?: string;
  read?: boolean;
};

export const getNotifications = async (): Promise<NotificationItem[]> => {
  const res = await api.get('/notifications');
  return res.data ?? [];
};

export const markAsRead = async (id: string): Promise<void> => {
  await api.post(`/notifications/${id}/read`);
};
