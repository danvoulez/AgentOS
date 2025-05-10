import React, { useEffect, useState, useCallback } from 'react';
import apiClient from '../../../apiClient';
import { CurrentStateDespacho, DESPACHO_STATUS_LITERAL, ActionResponseAPI } from '../../../types/api';
import { useAuth } from '../../../hooks/useAuth';
import DespachoCard from './DespachoCard';
import ResolveDespachoModal from './ResolveDespachoModal';
import { motion, AnimatePresence } from 'framer-motion';

const MosaicSelect: React.FC<any> = (props) => <select className="mosaic-select" {...props} style={{padding: 'var(--spacing-xs)', borderRadius: 'var(--border-radius-sm)', border: '1px solid var(--theme-border-color)'}} />;
const MosaicInput: React.FC<any> = (props) => <input className="mosaic-input" {...props} style={{padding: 'var(--spacing-xs)', borderRadius: 'var(--border-radius-sm)', border: '1px solid var(--theme-border-color)'}} />;
const MosaicButton: React.FC<any> = (props) => <motion.button whileHover={{scale:1.05}} whileTap={{scale:0.95}} className="mosaic-button" {...props} style={{padding: 'var(--spacing-xs) var(--spacing-sm)', border:'none', borderRadius:'var(--border-radius-sm)'}} />;

const DespachoList: React.FC = () => {
  const { user } = useAuth();
  const [despachos, setDespachos] = useState<CurrentStateDespacho[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedDespachoToResolve, setSelectedDespachoToResolve] = useState<CurrentStateDespacho | null>(null);
  
  const [filterStatus, setFilterStatus] = useState<string>("all_pending");
  const [filterAssignedTo, setFilterAssignedTo] = useState<string>("me_and_my_roles");
  const [filterDespachoType, setFilterDespachoType] = useState<string>("");
  const [uniqueDespachoTypes, setUniqueDespachoTypes] = useState<string[]>([]);

  const fetchDespachos = useCallback(async () => {
    if (!user) return;
    setLoading(true);
    setError(null);
    try {
      let queryParams = `limit=50&sortBy=due_at&sortOrder=asc`;
      let statusForQuery: string | undefined = undefined;
      if (filterStatus === "all_pending") { }
      else if (filterStatus === "all_active") { statusForQuery = "pending,assigned,in_progress"; }
      else if (filterStatus !== "all") { statusForQuery = filterStatus; }
      if (statusForQuery) queryParams += `&status=${statusForQuery}`;
      const isPrivileged = user.roles.includes("admin") || user.roles.includes("manager");
      if (filterAssignedTo === "me_and_my_roles" && !isPrivileged) {
        queryParams += `&assignedTo=${user.id}`; 
      } else if (filterAssignedTo && filterAssignedTo !== "all" && filterAssignedTo !== "me_and_my_roles") {
        queryParams += `&assignedTo=${encodeURIComponent(filterAssignedTo)}`;
      }
      if (filterDespachoType) {
        queryParams += `&despachoType=${encodeURIComponent(filterDespachoType)}`;
      }
      const response = await apiClient.get<CurrentStateDespacho[]>(`/query/despachos?${queryParams}`);
      let filteredData = response.data;
      setDespachos(filteredData);
      if (uniqueDespachoTypes.length === 0 && response.data.length > 0) {
        const types = new Set(response.data.map(d => d.despacho_type));
        setUniqueDespachoTypes(Array.from(types).sort());
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Falha ao buscar despachos.');
    } finally {
      setLoading(false);
    }
  }, [user, filterStatus, filterAssignedTo, filterDespachoType, uniqueDespachoTypes.length]);

  useEffect(() => {
    fetchDespachos();
  }, [fetchDespachos]);

  const handleActionSuccess = (response: ActionResponseAPI) => {
    fetchDespachos();
  };
  
  const filterContainerStyle: React.CSSProperties = { display: 'flex', gap: 'var(--spacing-md)', marginBottom: 'var(--spacing-lg)', alignItems: 'flex-end', flexWrap: 'wrap', padding: 'var(--spacing-sm)', background: 'var(--theme-background-color)', borderRadius: 'var(--border-radius-sm)'};
  const filterGroupStyle: React.CSSProperties = { display: 'flex', flexDirection: 'column' };

  if (!user) return <p>Por favor, faça login para ver seus despachos.</p>;
  if (loading) return <p>Carregando despachos...</p>;
  if (error) return <p style={{ color: 'var(--theme-accent-color)' }}>Erro: {error}</p>;

  return (
    <div>
      <div style={filterContainerStyle} className="mosaic-card">
        <div style={filterGroupStyle}>
          <label htmlFor="statusFilter">Status:</label>
          <MosaicSelect id="statusFilter" value={filterStatus} onChange={(e) => setFilterStatus(e.target.value as any)}>
            <option value="all_pending">Todos Pendentes/Ativos</option>
            <option value="all_active">Atribuídos/Em Progresso</option>
            <option value="pending">Pendentes (Não Atribuídos)</option>
            <option value="assigned">Atribuídos</option>
            <option value="in_progress">Em Progresso</option>
            <option value="resolved_manual">Resolvidos Manualmente</option>
            <option value="resolved_auto">Resolvidos Automaticamente</option>
            <option value="cancelled">Cancelados</option>
            <option value="escalated">Escalados</option>
            <option value="all">Todos (Incluindo finalizados)</option>
          </MosaicSelect>
        </div>
        <div style={filterGroupStyle}>
            <label htmlFor="assignedToFilter">Atribuído a:</label>
            <MosaicSelect id="assignedToFilter" value={filterAssignedTo} onChange={(e) => setFilterAssignedTo(e.target.value)}>
                <option value="me_and_my_roles">Meus e Meus Papéis</option>
                {(user.roles.includes("admin") || user.roles.includes("manager")) && <option value="all">Todos</option>}
                <option value="unassigned">Não Atribuídos</option>
            </MosaicSelect>
        </div>
         <div style={filterGroupStyle}>
            <label htmlFor="despachoTypeFilter">Tipo de Despacho:</label>
            <MosaicSelect id="despachoTypeFilter" value={filterDespachoType} onChange={(e) => setFilterDespachoType(e.target.value)}>
                <option value="">Todos os Tipos</option>
                {uniqueDespachoTypes.map(dt => <option key={dt} value={dt}>{dt}</option>)}
            </MosaicSelect>
        </div>
      </div>
      <AnimatePresence>
        {despachos.length === 0 && <motion.p initial={{opacity:0}} animate={{opacity:1}}>Nenhum despacho encontrado com os filtros atuais.</motion.p>}
        {despachos.map(d => (
          <DespachoCard key={d.id} despacho={d} onSelectToResolve={setSelectedDespachoToResolve} />
        ))}
      </AnimatePresence>
      <ResolveDespachoModal
        despacho={selectedDespachoToResolve}
        isOpen={!!selectedDespachoToResolve}
        onClose={() => setSelectedDespachoToResolve(null)}
        onActionSuccess={handleActionSuccess}
      />
    </div>
  );
};

export default DespachoList;