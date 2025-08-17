import { Typography, Box, Paper, Container } from '@mui/material';

const Login = () => {
  return (
    <Container component="main" maxWidth="xs">
      <Box
        sx={{
          marginTop: 8,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
        }}
      >
        <Paper elevation={3} sx={{ p: 4, width: '100%' }}>
          <Typography variant="h4" component="h1" gutterBottom align="center">
            Login
          </Typography>
          <Typography variant="body1" align="center">
            Login form will be implemented here.
          </Typography>
        </Paper>
      </Box>
    </Container>
  );
};

export default Login;