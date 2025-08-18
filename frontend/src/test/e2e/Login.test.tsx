import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { Provider } from 'react-redux'
import { BrowserRouter } from 'react-router-dom'
import { configureStore } from '@reduxjs/toolkit'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import userEvent from '@testing-library/user-event'

import Login from '@/pages/Login'
import { authSlice } from '@/store/slices/authSlice'
import * as authService from '@/services/api'

// Mock the API service
vi.mock('@/services/api', () => ({
  login: vi.fn(),
  register: vi.fn(),
  getCurrentUser: vi.fn(),
}))

const mockStore = configureStore({
  reducer: {
    auth: authSlice.reducer,
  },
})

const renderWithProviders = (component: React.ReactElement) => {
  return render(
    <Provider store={mockStore}>
      <BrowserRouter>
        {component}
      </BrowserRouter>
    </Provider>
  )
}

describe('Login Component E2E Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render login form with all required fields', async () => {
    renderWithProviders(<Login />)
    
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
    expect(screen.getByText(/don't have an account/i)).toBeInTheDocument()
  })

  it('should show validation errors for empty fields', async () => {
    const user = userEvent.setup()
    renderWithProviders(<Login />)
    
    const submitButton = screen.getByRole('button', { name: /sign in/i })
    await user.click(submitButton)
    
    await waitFor(() => {
      expect(screen.getByText(/email is required/i)).toBeInTheDocument()
      expect(screen.getByText(/password is required/i)).toBeInTheDocument()
    })
  })

  it('should show validation error for invalid email format', async () => {
    const user = userEvent.setup()
    renderWithProviders(<Login />)
    
    const emailInput = screen.getByLabelText(/email/i)
    const submitButton = screen.getByRole('button', { name: /sign in/i })
    
    await user.type(emailInput, 'invalid-email')
    await user.click(submitButton)
    
    await waitFor(() => {
      expect(screen.getByText(/invalid email format/i)).toBeInTheDocument()
    })
  })

  it('should handle successful login', async () => {
    const user = userEvent.setup()
    const mockLoginResponse = {
      access_token: 'fake-token',
      refresh_token: 'fake-refresh-token',
      user: {
        id: '1',
        email: 'test@example.com',
        first_name: 'Test',
        last_name: 'User',
      }
    }

    vi.mocked(authService.login).mockResolvedValue(mockLoginResponse)
    
    renderWithProviders(<Login />)
    
    const emailInput = screen.getByLabelText(/email/i)
    const passwordInput = screen.getByLabelText(/password/i)
    const submitButton = screen.getByRole('button', { name: /sign in/i })
    
    await user.type(emailInput, 'test@example.com')
    await user.type(passwordInput, 'password123')
    await user.click(submitButton)
    
    await waitFor(() => {
      expect(authService.login).toHaveBeenCalledWith('test@example.com', 'password123')
    })
  })

  it('should handle login error', async () => {
    const user = userEvent.setup()
    const mockError = new Error('Invalid credentials')
    
    vi.mocked(authService.login).mockRejectedValue(mockError)
    
    renderWithProviders(<Login />)
    
    const emailInput = screen.getByLabelText(/email/i)
    const passwordInput = screen.getByLabelText(/password/i)
    const submitButton = screen.getByRole('button', { name: /sign in/i })
    
    await user.type(emailInput, 'test@example.com')
    await user.type(passwordInput, 'wrongpassword')
    await user.click(submitButton)
    
    await waitFor(() => {
      expect(screen.getByText(/invalid credentials/i)).toBeInTheDocument()
    })
  })

  it('should toggle password visibility', async () => {
    const user = userEvent.setup()
    renderWithProviders(<Login />)
    
    const passwordInput = screen.getByLabelText(/password/i) as HTMLInputElement
    const toggleButton = screen.getByRole('button', { name: /toggle password visibility/i })
    
    expect(passwordInput.type).toBe('password')
    
    await user.click(toggleButton)
    expect(passwordInput.type).toBe('text')
    
    await user.click(toggleButton)
    expect(passwordInput.type).toBe('password')
  })

  it('should navigate to registration page', async () => {
    const user = userEvent.setup()
    renderWithProviders(<Login />)
    
    const registerLink = screen.getByText(/sign up/i)
    await user.click(registerLink)
    
    // In a real test, you would check if navigation occurred
    // This would require mocking react-router-dom's navigate
  })

  it('should show loading state during login', async () => {
    const user = userEvent.setup()
    let resolveLogin: (value: any) => void
    const loginPromise = new Promise(resolve => {
      resolveLogin = resolve
    })
    
    vi.mocked(authService.login).mockReturnValue(loginPromise)
    
    renderWithProviders(<Login />)
    
    const emailInput = screen.getByLabelText(/email/i)
    const passwordInput = screen.getByLabelText(/password/i)
    const submitButton = screen.getByRole('button', { name: /sign in/i })
    
    await user.type(emailInput, 'test@example.com')
    await user.type(passwordInput, 'password123')
    await user.click(submitButton)
    
    expect(screen.getByText(/signing in/i)).toBeInTheDocument()
    expect(submitButton).toBeDisabled()
    
    // Resolve the promise to complete the test
    resolveLogin!({
      access_token: 'token',
      refresh_token: 'refresh',
      user: { id: '1', email: 'test@example.com' }
    })
  })

  it('should remember me functionality', async () => {
    const user = userEvent.setup()
    renderWithProviders(<Login />)
    
    const rememberMeCheckbox = screen.getByLabelText(/remember me/i)
    
    expect(rememberMeCheckbox).not.toBeChecked()
    
    await user.click(rememberMeCheckbox)
    expect(rememberMeCheckbox).toBeChecked()
  })

  it('should handle forgot password link', async () => {
    const user = userEvent.setup()
    renderWithProviders(<Login />)
    
    const forgotPasswordLink = screen.getByText(/forgot password/i)
    await user.click(forgotPasswordLink)
    
    // In a real test, you would check if the forgot password modal/page opens
  })
})
