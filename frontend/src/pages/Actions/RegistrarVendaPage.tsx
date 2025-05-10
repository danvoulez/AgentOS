import React from 'react';
import RegistrarVendaForm from '../../components/mini_apps/RegistrarVenda/RegistrarVendaForm';

const RegistrarVendaPage: React.FC = () => {
  return (
    <div style={{ padding: 'var(--spacing-lg)'}}>
        <h2 style={{color: 'var(--theme-primary-color)', borderBottom: '2px solid var(--theme-primary-color)', paddingBottom: 'var(--spacing-sm)'}}>
            Registrar Nova Venda
        </h2>
        <p style={{color: 'var(--theme-text-muted-color)', marginBottom: 'var(--spacing-lg)'}}>
            Utilize este formulário para registrar uma venda com detalhes precisos. Cada registro gera um LogEvent auditável.
        </p>
        <RegistrarVendaForm />
    </div>
  );
};

export default RegistrarVendaPage;