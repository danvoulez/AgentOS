import React, { useEffect, useState } from 'react';
import apiClient from '../apiClient';
import { CurrentStateInventoryItem } from '../types/api';

const InventoryList: React.FC = () => {
  const [inventory, setInventory] = useState<CurrentStateInventoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchInventory = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await apiClient.get<CurrentStateInventoryItem[]>('/query/inventory?limit=20');
        setInventory(response.data);
      } catch (err: any) {
        setError(err.message || 'Failed to fetch inventory');
      } finally {
        setLoading(false);
      }
    };
    fetchInventory();
  }, []);

  if (loading) return <p>Loading inventory...</p>;
  if (error) return <p style={{ color: 'red' }}>Error fetching inventory: {error}</p>;
  if (inventory.length === 0) return <p>No inventory items found.</p>;

  return (
    <div>
      <h3>Inventory Items (Current State)</h3>
      <ul style={{ listStyle: 'none', padding: 0 }}>
        {inventory.map(item => (
          <li key={item.id} style={{ border: '1px solid #eee', marginBottom: '0.5rem', padding: '0.5rem' }}>
            <strong>{item.name || item.id}</strong> (SKU: {item.sku || 'N/A'})
            <br />
            Stock: {item.current_stock} {item.unit_of_measure || 'units'}
            <br />
            Last Updated: {new Date(item.last_updated_at).toLocaleDateString()}
            {item.low_stock_threshold && item.current_stock < item.low_stock_threshold && (
                <p style={{color: 'orange'}}>Warning: Low Stock!</p>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
};

export default InventoryList;