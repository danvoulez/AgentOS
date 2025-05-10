import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';

const Navbar: React.FC = () => {
  const { isAuthenticated, user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <nav style={{ display: 'flex', justifyContent: 'space-between', padding: '1rem', background: '#eee' }}>
      <div>
        <Link to="/" style={{ marginRight: '1rem' }}>Dashboard</Link>
        {isAuthenticated && <Link to="/timeline" style={{ marginRight: '1rem' }}>Timeline</Link>}
        {isAuthenticated && <Link to="/inventory" style={{ marginRight: '1rem' }}>Inventory</Link>}
      </div>
      <div>
        {isAuthenticated && user ? (
          <>
            <span style={{ marginRight: '1rem' }}>
              Welcome, {user.profile?.first_name || user.username}! (Roles: {user.roles.join(', ')})
            </span>
            <button onClick={handleLogout}>Logout</button>
          </>
        ) : (
          <Link to="/login">Login</Link>
        )}
      </div>
    </nav>
  );
};

export default Navbar;