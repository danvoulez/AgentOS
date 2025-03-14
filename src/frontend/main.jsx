import React from 'react';
import ReactDOM from 'react-dom/client';
import { MantineProvider } from '@mantine/core';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import './styles/main.scss';

// Tema escuro inspirado no GitKraken
const darkTheme = {
  colorScheme: 'dark',
  colors: {
    dark: [
      '#C1C2C5',
      '#A6A7AB',
      '#909296',
      '#5C5F66',
      '#373A40',
      '#2C2E33',
      '#25262B',
      '#1A1B1E',
      '#141517',
      '#101113',
    ],
    blue: [
      '#DBE4FF',
      '#B3C4FF',
      '#8AA3FF',
      '#6282FF',
      '#3A61FF',
      '#1240FF',
      '#0031F5',
      '#0029D1',
      '#0022AD',
      '#001B89',
    ],
  },
  primaryColor: 'blue',
  defaultRadius: 'md',
  fontFamily: 'Roboto, sans-serif',
  components: {
    Button: {
      styles: (theme) => ({
        root: {
          backgroundColor: theme.colors.dark[6],
          '&:hover': {
            backgroundColor: theme.colors.dark[5],
          },
        },
      }),
    },
  },
};

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <MantineProvider theme={darkTheme} withGlobalStyles withNormalizeCSS>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </MantineProvider>
  </React.StrictMode>
);
