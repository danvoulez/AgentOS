import React, { useState } from 'react';
import { AppShell, Header, Navbar, UnstyledButton, Group, Text, ThemeIcon, createStyles, Divider } from '@mantine/core';
import { Routes, Route, Link, Navigate, useLocation } from 'react-router-dom';
import { 
  IconDashboard, 
  IconBrandWhatsapp, 
  IconUsers, 
  IconCalendar, 
  IconSettings,
  IconDeviceNfc
} from '@tabler/icons-react';

// Pages
import Dashboard from './pages/Dashboard';
import WhatsAppDashboard from './pages/WhatsAppDashboard';
import RFIDManagement from './pages/RFIDManagement';

// Estilos para os itens de navegação
const useStyles = createStyles((theme) => ({
  link: {
    display: 'block',
    width: '100%',
    padding: theme.spacing.xs,
    borderRadius: theme.radius.sm,
    color: theme.colors.dark[0],
    '&:hover': {
      backgroundColor: theme.colors.dark[6],
    },
  },
  linkActive: {
    '&, &:hover': {
      backgroundColor: theme.fn.variant({ variant: 'light', color: theme.primaryColor }).background,
      color: theme.fn.variant({ variant: 'light', color: theme.primaryColor }).color,
    },
  },
}));

// Componente para os itens de navegação
const NavItem = ({ icon, color, label, path, active, onClick }) => {
  const { classes, cx } = useStyles();
  
  return (
    <UnstyledButton
      className={cx(classes.link, { [classes.linkActive]: active })}
      onClick={onClick}
      component={Link}
      to={path}
    >
      <Group>
        <ThemeIcon color={color} variant="light">
          {icon}
        </ThemeIcon>
        <Text size="sm">{label}</Text>
      </Group>
    </UnstyledButton>
  );
};

function App() {
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);
  
  // Navigation links
  const navLinks = [
    { label: 'Dashboard', icon: <IconDashboard size={16} />, path: '/', color: 'blue' },
    { label: 'WhatsApp', icon: <IconBrandWhatsapp size={16} />, path: '/whatsapp', color: 'green' },
    { label: 'Users', icon: <IconUsers size={16} />, path: '/users', color: 'violet' },
    { label: 'RFID Management', icon: <IconDeviceNfc size={16} />, path: '/rfid', color: 'orange' },
    { label: 'Calendar', icon: <IconCalendar size={16} />, path: '/calendar', color: 'teal' },
    { label: 'Settings', icon: <IconSettings size={16} />, path: '/settings', color: 'gray' },
  ];
  
  const navItems = navLinks.map((item) => (
    <NavItem
      key={item.path}
      {...item}
      active={location.pathname === item.path}
    />
  ));

  return (
    <AppShell
      padding="md"
      navbar={
        <Navbar width={{ base: 300 }} p="xs">
          <Navbar.Section mt="xs" mb="xl">
            <Group position="apart" px="sm">
              <Text size="xl" weight={700}>AgentOS</Text>
            </Group>
          </Navbar.Section>
          
          <Divider mb="xs" />
          
          <Navbar.Section grow>
            {navItems}
          </Navbar.Section>
          
          <Navbar.Section>
            <Divider my="xs" />
            <Text size="xs" color="dimmed" px="sm" pb="sm">
              AgentOS v0.1.0 - Developed by VoulezVous
            </Text>
          </Navbar.Section>
        </Navbar>
      }
      header={
        <Header height={60} p="xs">
          <Group position="apart">
            <Text size="lg" weight={700}>VoulezVous</Text>
          </Group>
        </Header>
      }
      styles={(theme) => ({
        main: {
          backgroundColor: theme.colors.dark[8],
          color: theme.colors.gray[0]
        },
      })}
    >
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/whatsapp" element={<WhatsAppDashboard />} />
        <Route path="/users" element={<div>Users Page (Under development)</div>} />
        <Route path="/rfid" element={<RFIDManagement />} />
        <Route path="/calendar" element={<div>Calendar Page (Under development)</div>} />
        <Route path="/settings" element={<div>Settings Page (Under development)</div>} />
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </AppShell>
  );
}

export default App;
