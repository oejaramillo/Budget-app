import { useState } from 'react'

import { useAuth } from '../../hooks/useAuth'
import { describeApiError } from '../../api'
import { Alert } from '../ui/Feedback'
import { TextField } from '../ui/FormFields'

const emptyLogin = { username: '', password: '' }
const emptyRegister = {
  username: '',
  email: '',
  password: '',
  password_confirm: '',
}

/**
 * Sign-in / sign-up panel.
 *
 * Registration collects `password_confirm` because the API requires it, and both
 * forms surface field-level errors returned by the backend instead of a generic
 * alert.
 */
export default function AuthPanel() {
  const { login, register } = useAuth()
  const [mode, setMode] = useState('login')
  const [loginValues, setLoginValues] = useState(emptyLogin)
  const [registerValues, setRegisterValues] = useState(emptyRegister)

  const isLogin = mode === 'login'
  const mutation = isLogin ? login : register
  const values = isLogin ? loginValues : registerValues
  const setValues = isLogin ? setLoginValues : setRegisterValues

  const handleChange = (event) => {
    const { name, value } = event.target
    setValues((previous) => ({ ...previous, [name]: value }))
  }

  const handleSubmit = (event) => {
    event.preventDefault()
    mutation.mutate(values, {
      onSuccess: () => {
        setLoginValues(emptyLogin)
        setRegisterValues(emptyRegister)
      },
    })
  }

  const switchMode = (nextMode) => {
    setMode(nextMode)
    mutation.reset()
  }

  const fieldError = (field) => {
    const data = mutation.error?.response?.data
    if (!data || typeof data !== 'object') return undefined
    const value = data[field]
    if (!value) return undefined
    return Array.isArray(value) ? value.join(' ') : String(value)
  }

  return (
    <div className="card" style={{ maxWidth: '420px', width: '100%' }}>
      <div className="tabs mb-3" role="tablist">
        <button
          type="button"
          role="tab"
          className="tab"
          aria-selected={isLogin}
          onClick={() => switchMode('login')}
        >
          Sign in
        </button>
        <button
          type="button"
          role="tab"
          className="tab"
          aria-selected={!isLogin}
          onClick={() => switchMode('register')}
        >
          Create account
        </button>
      </div>

      {mutation.isError && <Alert>{describeApiError(mutation.error)}</Alert>}

      <form onSubmit={handleSubmit}>
        <TextField
          label="Username *"
          name="username"
          value={values.username}
          onChange={handleChange}
          error={fieldError('username')}
          required
        />

        {!isLogin && (
          <TextField
            label="Email"
            name="email"
            type="email"
            value={values.email}
            onChange={handleChange}
            error={fieldError('email')}
          />
        )}

        <TextField
          label="Password *"
          name="password"
          type="password"
          value={values.password}
          onChange={handleChange}
          error={fieldError('password')}
          hint={isLogin ? undefined : 'At least 8 characters, not entirely numeric.'}
          required
        />

        {!isLogin && (
          <TextField
            label="Confirm password *"
            name="password_confirm"
            type="password"
            value={values.password_confirm}
            onChange={handleChange}
            error={fieldError('password_confirm')}
            required
          />
        )}

        <button type="submit" className="btn btn-primary" disabled={mutation.isPending}>
          {mutation.isPending ? 'Please wait…' : isLogin ? 'Sign in' : 'Create account'}
        </button>
      </form>
    </div>
  )
}
