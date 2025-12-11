import { useCallback } from 'react';
import { toast } from 'react-toastify';

interface ApiError {
  response?: {
    data?: {
      message?: string;
      detail?: string;
    };
    status?: number;
  };
  message?: string;
}

export const useApiError = () => {
  const showError = useCallback((error: ApiError) => {
    const errorMessage = 
      error?.response?.data?.message || 
      error?.response?.data?.detail || 
      error?.message || 
      'An unexpected error occurred';
    
    toast.error(errorMessage, {
      position: 'top-right',
      autoClose: 5000,
      hideProgressBar: false,
      closeOnClick: true,
      pauseOnHover: true,
      draggable: true,
    });
  }, []);

  const showSuccess = useCallback((message: string) => {
    toast.success(message, {
      position: 'top-right',
      autoClose: 3000,
      hideProgressBar: false,
      closeOnClick: true,
      pauseOnHover: true,
      draggable: true,
    });
  }, []);

  const showWarning = useCallback((message: string) => {
    toast.warning(message, {
      position: 'top-right',
      autoClose: 4000,
      hideProgressBar: false,
      closeOnClick: true,
      pauseOnHover: true,
      draggable: true,
    });
  }, []);

  const showInfo = useCallback((message: string) => {
    toast.info(message, {
      position: 'top-right',
      autoClose: 3000,
      hideProgressBar: false,
      closeOnClick: true,
      pauseOnHover: true,
      draggable: true,
    });
  }, []);

  return { showError, showSuccess, showWarning, showInfo };
};

export default useApiError;