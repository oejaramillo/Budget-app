import React, { useState } from 'react';
import { useAuth } from '../../hooks/useAuth';

interface FormData {
  username: string;
  password: string;
}

const LoginForm: React.FC = () => {
  const { login } = useAuth();
  const [formData, setFormData] = useState<FormData>({
    username: '',
    password: ''
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    // Clear error when user starts typing
    if (error) setError('');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    try {
      console.log('Attempting login with:', {
        username: formData.username,
        password: '***'
      });
      await login.mutateAsync(formData);
      console.log('Login successful!');
    } catch (err) {
      console.error('Login error:', err);
      setError('Usuario o contraseña incorrectos. Por favor, inténtalo de nuevo.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div>
      <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
        <h2 style={{ 
          fontSize: '1.8rem', 
          marginBottom: '0.5rem',
          color: 'var(--dark-navy)'
        }}>
          ¡Bienvenido de vuelta! 👋
        </h2>
        <p style={{ color: 'var(--medium-gray)' }}>
          Ingresa a tu cuenta para continuar gestionando tus finanzas
        </p>
      </div>

      {error && (
        <div style={{
          background: 'var(--alert-red)',
          color: 'white',
          padding: '12px 16px',
          borderRadius: 'var(--border-radius)',
          marginBottom: '1.5rem',
          fontSize: '0.9rem'
        }}>
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="username" className="form-label">
            Usuario o Email
          </label>
          <input
            type="text"
            id="username"
            name="username"
            value={formData.username}
            onChange={handleChange}
            className="form-input"
            placeholder="Ingresa tu usuario o email"
            required
            disabled={isLoading}
          />
        </div>

        <div className="form-group">
          <label htmlFor="password" className="form-label">
            Contraseña
          </label>
          <input
            type="password"
            id="password"
            name="password"
            value={formData.password}
            onChange={handleChange}
            className="form-input"
            placeholder="Ingresa tu contraseña"
            required
            disabled={isLoading}
          />
        </div>

        <div style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center',
          marginBottom: '2rem'
        }}>
          <label style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '0.5rem',
            cursor: 'pointer',
            fontSize: '0.9rem',
            color: 'var(--medium-gray)'
          }}>
            <input 
              type="checkbox" 
              style={{ 
                accentColor: 'var(--ocean-blue)',
                transform: 'scale(1.1)'
              }} 
            />
            Recordarme
          </label>
          <a 
            href="#forgot-password" 
            style={{ 
              color: 'var(--ocean-blue)', 
              textDecoration: 'none',
              fontSize: '0.9rem',
              fontWeight: '500'
            }}
          >
            ¿Olvidaste tu contraseña?
          </a>
        </div>

        <button
          type="submit"
          className="btn btn-primary"
          disabled={isLoading}
          style={{ 
            width: '100%', 
            padding: '14px',
            fontSize: '1rem',
            fontWeight: '600',
            opacity: isLoading ? 0.7 : 1,
            cursor: isLoading ? 'not-allowed' : 'pointer'
          }}
        >
          {isLoading ? (
            <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}>
              <div style={{
                width: '16px',
                height: '16px',
                border: '2px solid transparent',
                borderTop: '2px solid white',
                borderRadius: '50%',
                animation: 'spin 1s linear infinite'
              }}></div>
              Iniciando sesión...
            </span>
          ) : (
            'Iniciar Sesión'
          )}
        </button>
      </form>

      <div style={{ 
        textAlign: 'center', 
        marginTop: '2rem',
        padding: '1.5rem 0',
        borderTop: '1px solid #e9ecef'
      }}>
        <p style={{ color: 'var(--medium-gray)', fontSize: '0.9rem' }}>
          ¿Primera vez aquí?{' '}
          <span style={{ color: 'var(--ocean-blue)', fontWeight: '500' }}>
            Crea tu cuenta gratis
          </span>
        </p>
      </div>

      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

export default LoginForm;