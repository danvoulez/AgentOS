// frontend/components/card.jsx
import React from 'react';

const Card = ({ title, content }) => (
  <div style={{ 
    border: '1px solid #ccc', 
    borderRadius: '4px', 
    padding: '1rem', 
    margin: '1rem', 
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)' 
  }}>
    <h3>{title}</h3>
    <p>{content}</p>
  </div>
);

export default Card;
