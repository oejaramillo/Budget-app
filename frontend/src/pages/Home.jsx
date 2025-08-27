import React, { useState } from 'react';
import { useAuthContext } from '../hooks/useAuth';
import Currencies from "../components/Currencies";
import AccountsManager from "../components/AccountsManager";
import TransactionsManager from "../components/TransactionsManager";
import CategoriesManager from "../components/CategoriesManager";
import BudgetsManager from "../components/BudgetsManager";

const Home = () => {
  const [activeTab, setActiveTab] = useState('currencies');
  const { user, logout } = useAuthContext();

  const tabs = [
    { id: 'currencies', label: 'Monedas', component: Currencies },
    { id: 'accounts', label: 'Cuentas', component: AccountsManager },
    { id: 'transactions', label: 'Transacciones', component: TransactionsManager },
    { id: 'categories', label: 'Categorías', component: CategoriesManager },
    { id: 'budgets', label: 'Presupuestos', component: BudgetsManager },
  ];

  const renderContent = () => {
    switch (activeTab) {
      case 'currencies':
        return <Currencies />;
      case 'accounts':
        return <AccountsManager />;
      case 'transactions':
        return <TransactionsManager />;
      case 'categories':
        return <CategoriesManager />;
      case 'budgets':
        return <BudgetsManager />;
      default:
        return <Currencies />;
    }
  };

  return (
    <div style={{ minHeight: '100vh', background: 'var(--light-gray)' }}>
      {/* Header */}
      <header style={{ 
        background: 'white', 
        boxShadow: 'var(--shadow-soft)',
        padding: '1rem 2rem'
      }}>
        <div style={{ 
          maxWidth: '1200px', 
          margin: '0 auto', 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center' 
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <div style={{ 
              width: '40px', 
              height: '40px', 
              background: 'var(--deep-orange)', 
              borderRadius: 'var(--border-radius)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'white',
              fontWeight: 'bold',
              fontSize: '1.2rem'
            }}>
              💰
            </div>
            <h1 style={{ 
              color: 'var(--dark-navy)', 
              fontSize: '1.5rem', 
              fontFamily: 'var(--font-heading)' 
            }}>
              FinanceApp
            </h1>
          </div>
          
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <span style={{ color: 'var(--medium-gray)' }}>
              ¡Hola, {user?.username}! 👋
            </span>
            <button
              onClick={logout}
              className="btn btn-outline"
              style={{ padding: '8px 16px', fontSize: '0.9rem' }}
            >
              Cerrar Sesión
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main style={{ padding: '2rem' }}>
        <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
          
          {/* Welcome Section */}
          <div className="card" style={{ marginBottom: '2rem', textAlign: 'center' }}>
            <h2 style={{ 
              fontSize: '2rem', 
              marginBottom: '0.5rem',
              color: 'var(--dark-navy)'
            }}>
              Panel de Control Financiero
            </h2>
            <p style={{ color: 'var(--medium-gray)', fontSize: '1.1rem' }}>
              Gestiona tus finanzas de manera inteligente y toma decisiones informadas
            </p>
          </div>

          {/* Tab Navigation */}
          <div className="card" style={{ marginBottom: '2rem' }}>
            <div style={{ 
              display: 'flex', 
              gap: '0.5rem',
              background: 'var(--light-gray)',
              borderRadius: 'var(--border-radius)',
              padding: '4px'
            }}>
              {tabs.map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  style={{
                    flex: 1,
                    padding: '12px 16px',
                    border: 'none',
                    borderRadius: 'calc(var(--border-radius) - 2px)',
                    background: activeTab === tab.id ? 'white' : 'transparent',
                    color: activeTab === tab.id ? 'var(--dark-navy)' : 'var(--medium-gray)',
                    fontWeight: activeTab === tab.id ? '600' : '400',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                    boxShadow: activeTab === tab.id ? 'var(--shadow-soft)' : 'none',
                    fontFamily: 'var(--font-body)'
                  }}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

          {/* Active Tab Content */}
          <div className="card">
            {renderContent()}
          </div>
        </div>
      </main>
    </div>
  );
};

export default Home;
