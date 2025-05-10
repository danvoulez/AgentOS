// ...imports...
import DynamicFormRenderer from '../components/DynamicFormRenderer';
// ...outros imports...

// ...dentro do componente...
const handleDynamicFormSubmit = async (formData: Record<string, any>, formId: string) => {
  if (!activeFormSchema) return;

  addTurn({ speaker: 'user', content: <p><strong>Você (Formulário: {activeFormSchema.title}):</strong> Dados enviados.</p> });

  await submitToGateway(
      `Dados do formulário '${activeFormSchema.title}' (ID: ${formId}) foram submetidos.`,
      { form_id: formId, data: formData }
  );
  setActiveFormSchema(null);
};

// ...no render:
{!activeFormSchema ? (
  <GatewayInput onSubmit={handleUserInputSubmit} isProcessing={isProcessing} />
) : (
  <DynamicFormRenderer
    formSchema={activeFormSchema}
    onSubmit={handleDynamicFormSubmit}
    onCancel={() => { 
      setActiveFormSchema(null); 
      addTurn({ speaker: 'system_action', content: <p>Preenchimento de formulário '{activeFormSchema?.title}' cancelado.</p> });
    }}
    isSubmittingGlobal={isProcessing}
  />
)}