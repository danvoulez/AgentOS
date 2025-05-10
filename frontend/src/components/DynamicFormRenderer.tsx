import React, { useState, useEffect, useCallback } from 'react';
import { LLMFormSchema, LLMFormSchemaField } from '../types/api';
import { motion } from 'framer-motion';

interface DynamicFormRendererProps {
  formSchema: LLMFormSchema;
  onSubmit: (formData: Record<string, any>, formId: string) => Promise<void>;
  onCancel?: () => void;
  isSubmittingGlobal: boolean;
}

const DynamicFormRenderer: React.FC<DynamicFormRendererProps> = ({
  formSchema,
  onSubmit,
  onCancel,
  isSubmittingGlobal,
}) => {
  const [formData, setFormData] = useState<Record<string, any>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSelfSubmitting, setIsSelfSubmitting] = useState(false);

  useEffect(() => {
    const initialData = formSchema.fields.reduce((acc, field) => {
      acc[field.name] = field.default_value !== undefined ? field.default_value :
                        field.type === 'boolean' ? false :
                        (field.type === 'multi_select' || field.type === 'checkbox_group') ? [] : '';
      return acc;
    }, {} as Record<string, any>);
    setFormData(initialData);
    setErrors({});
  }, [formSchema]);

  const validateField = useCallback((field: LLMFormSchemaField, value: any): string | null => {
    if (field.required && (
        value === '' || value === undefined || value === null ||
        (field.type === 'boolean' && typeof value !== 'boolean') ||
        ((field.type === 'multi_select' || field.type === 'checkbox_group') && (!Array.isArray(value) || value.length === 0))
    )) {
      return `${field.label} é obrigatório.`;
    }

    if (value === null || value === undefined || value === '') return null;

    if (field.validation) {
      const { pattern, min_length, max_length, min_value, max_value, error_message } = field.validation;
      if (typeof value === 'string') {
        if (pattern && !new RegExp(pattern).test(value)) {
          return error_message || `Formato inválido para ${field.label}.`;
        }
        if (min_length !== undefined && value.length < min_length) {
          return error_message || `${field.label} deve ter no mínimo ${min_length} caracteres.`;
        }
        if (max_length !== undefined && value.length > max_length) {
          return error_message || `${field.label} deve ter no máximo ${max_length} caracteres.`;
        }
      }
      if ((field.type === 'number' || field.type === 'integer') && typeof value !== 'boolean') {
        const numValue = Number(value);
        if (isNaN(numValue)) return error_message || `${field.label} deve ser um número.`;
        if (min_value !== undefined && numValue < Number(min_value)) {
          return error_message || `${field.label} deve ser no mínimo ${min_value}.`;
        }
        if (max_value !== undefined && numValue > Number(max_value)) {
          return error_message || `${field.label} deve ser no máximo ${max_value}.`;
        }
      }
    }
    return null;
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value, type } = e.target;
    const currentField = formSchema.fields.find(f => f.name === name);

    if (type === 'checkbox' && currentField) {
      const checkbox = e.target as HTMLInputElement;
      if (currentField.type === 'multi_select' || currentField.type === 'checkbox_group') {
        const currentValues = (formData[name] || []) as string[];
        const newValues = checkbox.checked
          ? [...currentValues, value]
          : currentValues.filter(v => v !== value);
        setFormData(prev => ({ ...prev, [name]: newValues }));
      } else {
        setFormData(prev => ({ ...prev, [name]: checkbox.checked }));
      }
    } else if (currentField?.type === 'number' || currentField?.type === 'integer') {
      setFormData(prev => ({ ...prev, [name]: value === '' ? '' : Number(value) }));
    }
    else {
      setFormData(prev => ({ ...prev, [name]: value }));
    }
    if (errors[name]) {
      setErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[name];
        return newErrors;
      });
    }
  };

  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const newErrors: Record<string, string> = {};
    let isValid = true;

    formSchema.fields.forEach(field => {
      const error = validateField(field, formData[field.name]);
      if (error) {
        newErrors[field.name] = error;
        isValid = false;
      }
    });

    setErrors(newErrors);
    if (isValid) {
      setIsSelfSubmitting(true);
      try {
        await onSubmit(formData, formSchema.form_id);
      } finally {
        setIsSelfSubmitting(false);
      }
    } else {
      const firstErrorField = formSchema.fields.find(f => newErrors[f.name]);
      if (firstErrorField) {
        const fieldElement = document.getElementById(firstErrorField.name);
        fieldElement?.focus();
      }
    }
  };

  const renderField = (field: LLMFormSchemaField) => {
    const inputBaseStyle: React.CSSProperties = {
        width: '100%', padding: 'var(--spacing-sm)', marginBottom: 'var(--spacing-xs)',
        border: `var(--border-width) solid ${errors[field.name] ? 'var(--theme-accent-color)' : 'var(--theme-border-color)'}`,
        borderRadius: 'var(--border-radius-sm)',
        backgroundColor: 'var(--theme-surface-color)',
        color: 'var(--theme-text-color)',
        boxSizing: 'border-box'
    };
    const labelBaseStyle: React.CSSProperties = {
        display: 'block', marginBottom: 'var(--spacing-xs)', fontWeight: 'var(--font-weight-bold)',
        color: 'var(--theme-text-color)'
    };

    if (field.depends_on_field && formData[field.depends_on_field] !== field.depends_on_value_is) {
      if (field.depends_on_value_is !== undefined) return null;
    }
    if (field.depends_on_field && field.depends_on_value_is_not !== undefined && formData[field.depends_on_field] === field.depends_on_value_is_not) {
        return null;
    }

    switch (field.type) {
      case 'string': case 'email': case 'password': case 'number': case 'integer':
      case 'date': case 'datetime_local': case 'time':
        return <input style={inputBaseStyle} id={field.name} name={field.name} type={field.type} value={formData[field.name] ?? ''} onChange={handleChange} placeholder={field.placeholder} required={field.required} min={field.validation?.min_value as any} max={field.validation?.max_value as any} minLength={field.validation?.min_length} maxLength={field.validation?.max_length} pattern={field.validation?.pattern} />;
      case 'text_area':
        return <textarea style={inputBaseStyle} id={field.name} name={field.name} value={formData[field.name] ?? ''} onChange={handleChange} placeholder={field.placeholder} required={field.required} rows={4} minLength={field.validation?.min_length} maxLength={field.validation?.max_length} />;
      case 'boolean':
        return (
          <label style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-sm)', padding: 'var(--spacing-sm) 0' }}>
            <input type="checkbox" id={field.name} name={field.name} checked={!!formData[field.name]} onChange={handleChange} style={{width: 'auto'}}/>
            <span style={labelBaseStyle}>{field.label} {field.required && '*'}</span>
          </label>
        );
      case 'select':
        return (
          <select style={inputBaseStyle} id={field.name} name={field.name} value={formData[field.name] ?? ''} onChange={handleChange} required={field.required}>
            {field.placeholder && <option value="">{field.placeholder}</option>}
            {field.options?.map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
          </select>
        );
      case 'radio_group':
        return (
          <div role="radiogroup" aria-labelledby={`${field.name}-label`}>
            {field.options?.map(opt => (
              <label key={opt.value} style={{ marginRight: 'var(--spacing-md)', display: 'inline-flex', alignItems: 'center', gap: 'var(--spacing-xs)' }}>
                <input type="radio" name={field.name} value={opt.value} checked={formData[field.name] === opt.value} onChange={handleChange} required={field.required} />
                {opt.label}
              </label>
            ))}
          </div>
        );
      case 'multi_select':
      case 'checkbox_group':
        return (
          <div>
            {field.options?.map(opt => (
              <label key={opt.value} style={{ marginRight: 'var(--spacing-md)', display: 'inline-flex', alignItems: 'center', gap: 'var(--spacing-xs)' }}>
                <input type="checkbox" name={field.name} value={opt.value} checked={(formData[field.name] || []).includes(opt.value)} onChange={handleChange} />
                {opt.label}
              </label>
            ))}
          </div>
        );
      case 'hidden':
        return <input type="hidden" id={field.name} name={field.name} value={formData[field.name] ?? ''} />;
      default:
        return <input style={inputBaseStyle} id={field.name} name={field.name} type="text" value={formData[field.name] ?? ''} onChange={handleChange} placeholder={field.placeholder} required={field.required} />;
    }
  };

  const actualIsSubmitting = isSubmittingGlobal || isSelfSubmitting;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}
      style={{
        border: `var(--border-width) solid var(--theme-primary-color)`,
        padding: 'var(--spacing-lg)', borderRadius: 'var(--border-radius-md)', marginTop: 'var(--spacing-md)',
        backgroundColor: 'var(--theme-surface-color)', boxShadow: 'var(--shadow-md)'
      }}
    >
      <h4 style={{ marginTop: 0, color: 'var(--theme-primary-color)' }}>{formSchema.title}</h4>
      {formSchema.description && <p style={{color: 'var(--theme-text-muted-color)', fontSize: 'var(--font-size-sm)'}}>{formSchema.description}</p>}
      <form onSubmit={handleFormSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-md)' }}>
        {formSchema.fields.map(field => (
          <div key={field.name} className={`form-field-type-${field.type}`}>
            {field.type !== 'boolean' && field.type !== 'hidden' && (
                <label htmlFor={field.name} style={{ display: 'block', marginBottom: 'var(--spacing-xs)', fontWeight: 700 }}>
                    {field.label} {field.required && <span style={{color: 'var(--theme-accent-color)'}}>*</span>}
                </label>
            )}
            {renderField(field)}
            {errors[field.name] && <p style={{ color: 'var(--theme-accent-color)', fontSize: '0.8rem', marginTop: 'var(--spacing-xs)' }}>{errors[field.name]}</p>}
            {field.description && field.type !== 'boolean' && field.type !== 'hidden' && (
                <small style={{display: 'block', color: 'var(--theme-text-muted-color)', fontSize: 'var(--font-size-sm)', marginTop: 'var(--spacing-xs)'}}>
                    {field.description}
                </small>
            )}
          </div>
        ))}
        <div style={{ display: 'flex', gap: 'var(--spacing-md)', marginTop: 'var(--spacing-md)', justifyContent: 'flex-end' }}>
          {onCancel && formSchema.cancel_button_text && (
            <motion.button
              type="button" onClick={onCancel} disabled={actualIsSubmitting}
              whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
              style={{ padding: 'var(--spacing-sm) var(--spacing-lg)', background: 'var(--theme-background-color)', color: 'var(--theme-text-color)', border: `var(--border-width) solid var(--theme-border-color)`, borderRadius: 'var(--border-radius-sm)'}}
            >
              {formSchema.cancel_button_text}
            </motion.button>
          )}
          <motion.button
            type="submit" disabled={actualIsSubmitting}
            whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
            style={{ padding: 'var(--spacing-sm) var(--spacing-lg)', background: 'var(--theme-primary-color)', color: 'white', border: 'none', borderRadius: 'var(--border-radius-sm)'}}
          >
            {actualIsSubmitting ? 'Enviando...' : formSchema.submit_button_text}
          </motion.button>
        </div>
      </form>
    </motion.div>
  );
};

export default DynamicFormRenderer;