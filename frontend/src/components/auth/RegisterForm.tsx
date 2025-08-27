import React, { useState } from 'react';
import { useAuth } from '../../hooks/useAuth';

interface FormData {
  username: string;
  email: string;
  password: string;
  confirmPassword: string;
}

const RegisterForm: React.FC = () => {
  const { register } = useAuth();
  const [formData, setFormData] = useState<FormData>({
    username: '',
    email: '',
    password: '',
    confirmPassword: ''
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [passwordStrength, setPasswordStrength] = useState(0);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    
    // Clear error when user starts typing
    if (error) setError('');
    
    // Calculate password strength
    if (name === 'password') {
      calculatePasswordStrength(value);
    }
  };

  const calculatePasswordStrength = (password: string) => {
    let strength = 0;
    if (password.length >= 8) strength += 25;
    if (/[a-z]/.test(password)) strength += 25;
    if (/[A-Z]/.test(password)) strength += 25;
    if (/[0-9]/.test(password)) strength += 25;
    setPasswordStrength(strength);
  };

  const getPasswordStrengthColor = () => {
    if (passwordStrength < 50) return 'var(--alert-red)';
    if (passwordStrength < 75) return 'var(--sunshine-yellow)';
    return 'var(--success-green)';
  };

  const getPasswordStrengthText = () => {
    if (passwordStrength < 25) return 'Muy débil';
    if (passwordStrength < 50) return 'Débil';
    if (passwordStrength < 75) return 'Buena';
    return 'Excelente';
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    // Validation
    if (formData.password !== formData.confirmPassword) {
      setError('Las contraseñas no coinciden');
      setIsLoading(false);
      return;
    }

    if (formData.password.length < 8) {
      setError('La contraseña debe tener al menos 8 caracteres');
      setIsLoading(false);
      return;
    }

    try {
      console.log('Attempting registration with:', {
        username: formData.username,
        password: '***'
      });
      await register.mutateAsync({
        username: formData.username,
        password: formData.password
      });
      console.log('Registration successful!');
    } catch (err) {
      console.error('Registration error:', err);
      setError('Error al crear la cuenta. Por favor, inténtalo de nuevo.');
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
          Crea tu cuenta gratuita 🚀
        </h2>
        <p style={{ color: 'var(--medium-gray)' }}>
          Únete a miles de usuarios que ya controlan sus finanzas
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
            Nombre de Usuario
          </label>
          <input
            type="text"
            id="username"
            name="username"
            value={formData.username}
            onChange={handleChange}
            className="form-input"
            placeholder="Elige un nombre de usuario único"
            required
            disabled={isLoading}
          />
        </div>

        <div className="form-group">
          <label htmlFor="email" className="form-label">
            Email
          </label>
          <input
            type="email"
            id="email"
            name="email"
            value={formData.email}
            onChange={handleChange}
            className="form-input"
            placeholder="tu@email.com"
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
            placeholder="Crea una contraseña segura"
            required
            disabled={isLoading}
          />
          {formData.password && (
            <div style={{ marginTop: '0.5rem' }}>
              <div style={{
                width: '100%',
                height: '4px',
                background: '#e9ecef',
                borderRadius: '2px',
                overflow: 'hidden'
              }}>
                <div style={{
                  width: `${passwordStrength}%`,
                  height: '100%',
                  background: getPasswordStrengthColor(),
                  transition: 'all 0.3s ease'
                }}></div>
              </div>
              <p style={{
                fontSize: '0.8rem',
                color: getPasswordStrengthColor(),
                marginTop: '0.25rem',
                fontWeight: '500'
              }}>
                Seguridad: {getPasswordStrengthText()}
              </p>
            </div>
          )}
        </div>

        <div className="form-group">
          <label htmlFor="confirmPassword" className="form-label">
            Confirmar Contraseña
          </label>
          <input
            type="password"
            id="confirmPassword"
            name="confirmPassword"
            value={formData.confirmPassword}
            onChange={handleChange}
            className="form-input"
            placeholder="Repite tu contraseña"
            required
            disabled={isLoading}
          />
          {formData.confirmPassword && formData.password !== formData.confirmPassword && (
            <p style={{
              fontSize: '0.8rem',
              color: 'var(--alert-red)',
              marginTop: '0.25rem'
            }}>
              Las contraseñas no coinciden
            </p>
          )}
        </div>

        <div style={{ marginBottom: '2rem' }}>
          <label style={{ 
            display: 'flex', 
            alignItems: 'flex-start', 
            gap: '0.5rem',
            cursor: 'pointer',
            fontSize: '0.9rem',
            color: 'var(--medium-gray)',
            lineHeight: '1.4'
          }}>
            <input 
              type="checkbox" 
              required
              style={{ 
                accentColor: 'var(--ocean-blue)',
                transform: 'scale(1.1)',
                marginTop: '2px'
              }} 
            />
            <span>
              Acepto los{' '}
              <a href="#terms" style={{ color: 'var(--ocean-blue)', textDecoration: 'none' }}>
                términos y condiciones
              </a>{' '}
              y la{' '}
              <a href="#privacy" style={{ color: 'var(--ocean-blue)', textDecoration: 'none' }}>
                política de privacidad
              </a>
            </span>
          </label>
        </div>

        <button
          type="submit"
          className="btn btn-primary"
          disabled={isLoading || formData.password !== formData.confirmPassword}
          style={{ 
            width: '100%', 
            padding: '14px',
            fontSize: '1rem',
            fontWeight: '600',
            opacity: (isLoading || formData.password !== formData.confirmPassword) ? 0.7 : 1,
            cursor: (isLoading || formData.password !== formData.confirmPassword) ? 'not-allowed' : 'pointer'
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
              Creando cuenta...
            </span>
          ) : (
            'Crear Cuenta Gratuita'
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
          ¿Ya tienes una cuenta?{' '}
          <span style={{ color: 'var(--ocean-blue)', fontWeight: '500' }}>
            Inicia sesión aquí
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

export default RegisterForm;