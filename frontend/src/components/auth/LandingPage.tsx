import React, { useState } from 'react';
import LoginForm from './LoginForm';
import RegisterForm from './RegisterForm';
import '../../styles/globals.css';

const LandingPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'login' | 'register'>('login');

  return (
    <div style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #8ecae6 0%, #219ebc 100%)' }}>
      {/* Header */}
      <header style={{ padding: '1rem 2rem', background: 'rgba(255, 255, 255, 0.1)', backdropFilter: 'blur(10px)' }}>
        <div style={{ maxWidth: '1200px', margin: '0 auto', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <div style={{ 
              width: '40px', 
              height: '40px', 
              background: 'var(--deep-orange)', 
              borderRadius: '8px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'white',
              fontWeight: 'bold',
              fontSize: '1.2rem'
            }}>
              💰
            </div>
            <h1 style={{ color: 'white', fontSize: '1.5rem', fontFamily: 'var(--font-heading)' }}>
              FinanceApp
            </h1>
          </div>
          <nav style={{ display: 'flex', gap: '2rem' }}>
            <a href="#features" style={{ color: 'white', textDecoration: 'none', fontWeight: '500' }}>Características</a>
            <a href="#about" style={{ color: 'white', textDecoration: 'none', fontWeight: '500' }}>Acerca de</a>
            <a href="#contact" style={{ color: 'white', textDecoration: 'none', fontWeight: '500' }}>Contacto</a>
          </nav>
        </div>
      </header>

      {/* Main Content */}
      <main style={{ padding: '4rem 2rem' }}>
        <div style={{ maxWidth: '1200px', margin: '0 auto', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4rem', alignItems: 'center' }}>
          
          {/* Left Side - Marketing Content */}
          <div style={{ color: 'white' }}>
            <h1 style={{ 
              fontSize: '3.5rem', 
              fontFamily: 'var(--font-heading)', 
              fontWeight: '700', 
              marginBottom: '1.5rem',
              lineHeight: '1.2'
            }}>
              Controla tus <span style={{ color: 'var(--sunshine-yellow)' }}>finanzas</span> como nunca antes
            </h1>
            
            <p style={{ 
              fontSize: '1.2rem', 
              marginBottom: '2rem', 
              opacity: '0.9',
              lineHeight: '1.6'
            }}>
              Gestiona tus ingresos, gastos y presupuestos de manera inteligente. 
              Toma decisiones financieras informadas con nuestras herramientas avanzadas de análisis.
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginBottom: '3rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                <div style={{ 
                  width: '24px', 
                  height: '24px', 
                  background: 'var(--sunshine-yellow)', 
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}>
                  ✓
                </div>
                <span>Seguimiento automático de gastos e ingresos</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                <div style={{ 
                  width: '24px', 
                  height: '24px', 
                  background: 'var(--sunshine-yellow)', 
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}>
                  ✓
                </div>
                <span>Presupuestos inteligentes y alertas personalizadas</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                <div style={{ 
                  width: '24px', 
                  height: '24px', 
                  background: 'var(--sunshine-yellow)', 
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}>
                  ✓
                </div>
                <span>Reportes detallados y análisis de tendencias</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                <div style={{ 
                  width: '24px', 
                  height: '24px', 
                  background: 'var(--sunshine-yellow)', 
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}>
                  ✓
                </div>
                <span>Múltiples cuentas y monedas soportadas</span>
              </div>
            </div>

            <div style={{ 
              background: 'rgba(255, 255, 255, 0.1)', 
              padding: '1.5rem', 
              borderRadius: 'var(--border-radius)',
              backdropFilter: 'blur(10px)'
            }}>
              <h3 style={{ marginBottom: '0.5rem', color: 'var(--sunshine-yellow)' }}>
                🚀 ¡Comienza gratis hoy!
              </h3>
              <p style={{ opacity: '0.9', fontSize: '0.95rem' }}>
                Sin compromisos, sin tarjetas de crédito. Empieza a organizar tus finanzas en menos de 2 minutos.
              </p>
            </div>
          </div>

          {/* Right Side - Auth Forms */}
          <div>
            <div className="card card-large" style={{ maxWidth: '400px', margin: '0 auto' }}>
              {/* Tab Navigation */}
              <div style={{ 
                display: 'flex', 
                marginBottom: '2rem',
                background: 'var(--light-gray)',
                borderRadius: 'var(--border-radius)',
                padding: '4px'
              }}>
                <button
                  onClick={() => setActiveTab('login')}
                  style={{
                    flex: 1,
                    padding: '12px',
                    border: 'none',
                    borderRadius: 'calc(var(--border-radius) - 2px)',
                    background: activeTab === 'login' ? 'white' : 'transparent',
                    color: activeTab === 'login' ? 'var(--dark-navy)' : 'var(--medium-gray)',
                    fontWeight: activeTab === 'login' ? '600' : '400',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                    boxShadow: activeTab === 'login' ? 'var(--shadow-soft)' : 'none'
                  }}
                >
                  Iniciar Sesión
                </button>
                <button
                  onClick={() => setActiveTab('register')}
                  style={{
                    flex: 1,
                    padding: '12px',
                    border: 'none',
                    borderRadius: 'calc(var(--border-radius) - 2px)',
                    background: activeTab === 'register' ? 'white' : 'transparent',
                    color: activeTab === 'register' ? 'var(--dark-navy)' : 'var(--medium-gray)',
                    fontWeight: activeTab === 'register' ? '600' : '400',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                    boxShadow: activeTab === 'register' ? 'var(--shadow-soft)' : 'none'
                  }}
                >
                  Registrarse
                </button>
              </div>

              {/* Form Content */}
              {activeTab === 'login' ? <LoginForm /> : <RegisterForm />}
            </div>

            {/* Trust Indicators */}
            <div style={{ 
              textAlign: 'center', 
              marginTop: '2rem',
              color: 'white',
              opacity: '0.8'
            }}>
              <p style={{ fontSize: '0.9rem', marginBottom: '1rem' }}>
                🔒 Tus datos están protegidos con encriptación de nivel bancario
              </p>
              <div style={{ display: 'flex', justifyContent: 'center', gap: '2rem', fontSize: '0.8rem' }}>
                <span>✓ SSL Certificado</span>
                <span>✓ Datos Encriptados</span>
                <span>✓ Respaldo Automático</span>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Features Section */}
      <section id="features" style={{ 
        background: 'rgba(255, 255, 255, 0.95)', 
        padding: '4rem 2rem',
        backdropFilter: 'blur(10px)'
      }}>
        <div style={{ maxWidth: '1200px', margin: '0 auto', textAlign: 'center' }}>
          <h2 style={{ 
            fontSize: '2.5rem', 
            marginBottom: '1rem',
            color: 'var(--dark-navy)'
          }}>
            Todo lo que necesitas para gestionar tu dinero
          </h2>
          <p style={{ 
            fontSize: '1.1rem', 
            color: 'var(--medium-gray)', 
            marginBottom: '3rem',
            maxWidth: '600px',
            margin: '0 auto 3rem'
          }}>
            Herramientas poderosas y fáciles de usar que te ayudarán a tomar el control total de tus finanzas personales.
          </p>

          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', 
            gap: '2rem',
            marginTop: '3rem'
          }}>
            <div className="card" style={{ textAlign: 'center' }}>
              <div style={{ 
                fontSize: '3rem', 
                marginBottom: '1rem',
                background: 'linear-gradient(135deg, var(--sky-blue), var(--ocean-blue))',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent'
              }}>
                📊
              </div>
              <h3 style={{ marginBottom: '1rem' }}>Dashboard Inteligente</h3>
              <p style={{ color: 'var(--medium-gray)' }}>
                Visualiza todos tus datos financieros en un solo lugar con gráficos interactivos y métricas clave.
              </p>
            </div>

            <div className="card" style={{ textAlign: 'center' }}>
              <div style={{ 
                fontSize: '3rem', 
                marginBottom: '1rem',
                background: 'linear-gradient(135deg, var(--sunshine-yellow), var(--deep-orange))',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent'
              }}>
                🎯
              </div>
              <h3 style={{ marginBottom: '1rem' }}>Metas Financieras</h3>
              <p style={{ color: 'var(--medium-gray)' }}>
                Establece objetivos de ahorro y recibe recordatorios para mantener tus finanzas en el camino correcto.
              </p>
            </div>

            <div className="card" style={{ textAlign: 'center' }}>
              <div style={{ 
                fontSize: '3rem', 
                marginBottom: '1rem',
                background: 'linear-gradient(135deg, var(--ocean-blue), var(--deep-orange))',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent'
              }}>
                🔄
              </div>
              <h3 style={{ marginBottom: '1rem' }}>Sincronización Automática</h3>
              <p style={{ color: 'var(--medium-gray)' }}>
                Conecta tus cuentas bancarias y tarjetas para importar transacciones automáticamente.
              </p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};

export default LandingPage;