import { useState, useCallback } from 'react';
import apiClient from '../apiClient';
import { AcionarLogEventActionAPIPayload, ActionResponseAPI } from '../types/api';
import { useAuth } from './useAuth';

interface UseLogActionsReturn {
  acionarLog: (payload: AcionarLogEventActionAPIPayload) => Promise<ActionResponseAPI>;
  isAcionando: boolean;
  errorAcionamento: string | null;
}

export const useLogActions = (): UseLogActionsReturn => {
  const [isAcionando, setIsAcionando] = useState(false);
  const [errorAcionamento, setErrorAcionamento] = useState<string | null>(null);
  const { token } = useAuth();

  const acionarLog = useCallback(
    async (payload: AcionarLogEventActionAPIPayload): Promise<ActionResponseAPI> => {
      if (!token) {
        throw new Error("Usuário não autenticado.");
      }
      setIsAcionando(true);
      setErrorAcionamento(null);
      try {
        const response = await apiClient.post<ActionResponseAPI>('/actions/acionar_log', payload);
        return response.data;
      } catch (err: any) {
        const errorMsg = err.response?.data?.detail || err.message || 'Falha ao acionar o log.';
        setErrorAcionamento(errorMsg);
        throw new Error(errorMsg);
      } finally {
        setIsAcionando(false);
      }
    },
    [token]
  );

  return { acionarLog, isAcionando, errorAcionamento };
};