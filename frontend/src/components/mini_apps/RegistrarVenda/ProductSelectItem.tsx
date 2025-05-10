import React, { useState, useEffect, useRef } from 'react';
import apiClient from '../../../apiClient';
import { CurrentStateInventoryItem } from '../../../types/api';

interface ProductSelectItemProps {
  selectedProductId: string;
  onProductSelect: (product: CurrentStateInventoryItem | null) => void;
  label?: string;
  disabled?: boolean;
  itemIndex: number;
}

const ProductSelectItem: React.FC<ProductSelectItemProps> = ({ selectedProductId, onProductSelect, label, disabled, itemIndex }) => {
  const [products, setProducts] = useState<CurrentStateInventoryItem[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const fetch = async () => {
      if (searchTerm.length > 0) {
        setIsLoading(true);
        try {
          const response = await apiClient.get<CurrentStateInventoryItem[]>(`/query/inventory?name_contains=${encodeURIComponent(searchTerm)}&limit=10&sort_by=name`);
          setProducts(response.data);
        } catch (err) {
          setProducts([]);
        } finally {
          setIsLoading(false);
        }
      } else {
        setProducts([]);
      }
    };
    const debounceFetch = setTimeout(() => fetch(), 300);
    return () => clearTimeout(debounceFetch);
  }, [searchTerm]);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target as Node)) {
        setShowDropdown(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [wrapperRef]);

  const handleSelect = (product: CurrentStateInventoryItem) => {
    onProductSelect(product);
    setSearchTerm(product.name || product.id);
    setShowDropdown(false);
  };

  useEffect(() => {
      if (selectedProductId && products.length === 0 && !searchTerm) {
          apiClient.get<CurrentStateInventoryItem>(`/query/inventory/${selectedProductId}`)
              .then(res => {
                  setSearchTerm(res.data.name || res.data.id);
              })
              .catch(() => {});
      }
  }, [selectedProductId, products.length, searchTerm]);

  return (
    <div ref={wrapperRef} className="product-select-item mosaic-input-group" style={{ position: 'relative', marginBottom: 'var(--spacing-sm)' }}>
      {label && <label htmlFor={`product-search-${itemIndex}`} className="mosaic-label">{label}</label>}
      <input
        type="text"
        id={`product-search-${itemIndex}`}
        className="mosaic-input"
        value={searchTerm}
        onChange={(e) => { setSearchTerm(e.target.value); setShowDropdown(true); if (selectedProductId) onProductSelect(null); }}
        onFocus={() => setShowDropdown(true)}
        placeholder="Buscar produto por nome ou SKU..."
        disabled={disabled}
      />
      {isLoading && <small className="mosaic-form-text">Buscando...</small>}
      {showDropdown && products.length > 0 && (
        <ul className="mosaic-dropdown-list" style={{
          position: 'absolute', top: '100%', left: 0, right: 0,
          background: 'var(--theme-surface-color)', border: '1px solid var(--theme-border-color)',
          borderRadius: 'var(--border-radius-sm)', maxHeight: '200px', overflowY: 'auto',
          listStyle: 'none', padding: 0, margin: 'var(--spacing-xs) 0 0 0', zIndex: 1050
        }}>
          {products.map(p => (
            <li
              key={p.id}
              onClick={() => handleSelect(p)}
              className="mosaic-dropdown-item"
              style={{ padding: 'var(--spacing-sm)', cursor: 'pointer' }}
            >
              {p.name} (SKU: {p.sku || 'N/A'}) - Estoque: {p.current_stock} - Preço: R$ {p.selling_price_str || 'N/A'}
            </li>
          ))}
        </ul>
      )}
       {showDropdown && !isLoading && products.length === 0 && searchTerm.length > 1 && (
        <small className="mosaic-form-text">Nenhum produto encontrado para "{searchTerm}".</small>
       )}
    </div>
  );
};

export default ProductSelectItem;