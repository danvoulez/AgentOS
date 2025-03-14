// frontend/components/navbar.jsx
import React from 'react';
import { Link } from 'react-router-dom';

const Navbar = () => (
  <nav style={{ 
    padding: '1rem', 
    backgroundColor: '#333', 
    color: '#fff' 
  }}>
    <ul style={{ 
      display: 'flex', 
      listStyle: 'none', 
      margin: 0, 
      padding: 0 
    }}>
      <li style={{ marginRight: '1rem' }}>
        <Link to="/" style={{ color: '#fff', textDecoration: 'none' }}>Home</Link>
      </li>
      <li style={{ marginRight: '1rem' }}>
        <Link to="/dashboard" style={{ color: '#fff', textDecoration: 'none' }}>Dashboard</Link>
      </li>
      <li style={{ marginRight: '1rem' }}>
        <Link to="/rfid" style={{ color: '#fff', textDecoration: 'none' }}>RFID Management</Link>
      </li>
    </ul>
  </nav>
);

export default Navbar;
