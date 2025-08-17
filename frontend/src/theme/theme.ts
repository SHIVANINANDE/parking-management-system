import { createTheme } from '@mui/material/styles';

declare module '@mui/material/styles' {
  interface Theme {
    custom: {
      parking: {
        available: string;
        occupied: string;
        reserved: string;
        disabled: string;
      };
    };
  }

  interface ThemeOptions {
    custom?: {
      parking?: {
        available?: string;
        occupied?: string;
        reserved?: string;
        disabled?: string;
      };
    };
  }
}

export const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
      light: '#42a5f5',
      dark: '#1565c0',
    },
    secondary: {
      main: '#dc004e',
      light: '#ff5983',
      dark: '#9a0036',
    },
    background: {
      default: '#f5f5f5',
      paper: '#ffffff',
    },
  },
  typography: {
    fontFamily: 'Roboto, Arial, sans-serif',
    h1: {
      fontSize: '2.5rem',
      fontWeight: 600,
    },
    h2: {
      fontSize: '2rem',
      fontWeight: 600,
    },
    h3: {
      fontSize: '1.75rem',
      fontWeight: 500,
    },
  },
  shape: {
    borderRadius: 8,
  },
  custom: {
    parking: {
      available: '#4caf50',
      occupied: '#f44336',
      reserved: '#ff9800',
      disabled: '#9e9e9e',
    },
  },
});

export default theme;