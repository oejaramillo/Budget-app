import React, { useState } from "react";
import Currencies from "../components/Currencies";
import AccountsManager from "../components/AccountsManager";
import TransactionsManager from "../components/TransactionsManager";
import CategoriesManager from "../components/CategoriesManager";
import BudgetsManager from "../components/BudgetsManager";

function Home() {
  const [activeTab, setActiveTab] = useState('currencies');

  const tabs = [
    { id: 'currencies', label: 'Currencies' },
    { id: 'accounts', label: 'Accounts' },
    { id: 'transactions', label: 'Transactions' },
    { id: 'categories', label: 'Categories' },
    { id: 'budgets', label: 'Budgets' },
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
    <div style={{ padding: '20px' }}>
      <h1>Personal Finance Manager</h1>
      
      {/* Navigation Tabs */}
      <div style={{ marginBottom: '20px', borderBottom: '1px solid #ccc' }}>
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              padding: '10px 20px',
              marginRight: '10px',
              backgroundColor: activeTab === tab.id ? '#007bff' : '#f8f9fa',
              color: activeTab === tab.id ? 'white' : '#333',
              border: '1px solid #ccc',
              borderBottom: activeTab === tab.id ? '2px solid #007bff' : '1px solid #ccc',
              cursor: 'pointer'
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div>
        {renderContent()}
      </div>
    </div>
  );
}

export default Home;
