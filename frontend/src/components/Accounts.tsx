import React, { useState, useEffect } from "react";
import api from "../api";  

type Account = {
  id: number;
  name: string;
  account_type: string;
  balance: string;
  currency: number;
  institution?: string;
  official_number?: string;
  created_date: string;
  last_updated: string;
};

type Currency = {
  id: number;
  code: string;
  name: string;
};

const Accounts: React.FC = () => {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [currencies, setCurrencies] = useState<Currency[]>([]);

  const [name, setName] = useState("");
  const [accountType, setAccountType] = useState("checking");
  const [balance, setBalance] = useState("");
  const [currency, setCurrency] = useState<number | null>(null);
  const [institution, setInstitution] = useState("");
  const [officialNumber, setOfficialNumber] = useState("");

  useEffect(() => {
    fetchAccounts();
    fetchCurrencies();
  }, []);

  const fetchAccounts = () => {
    api.get("/api/accounts/")
      .then((res) => setAccounts(res.data))
      .catch((err) => alert("Error loading accounts"));
  };

  const fetchCurrencies = () => {
    api.get("/api/currencies/")
      .then((res) => setCurrencies(res.data))
      .catch((err) => alert("Error loading currencies"));
  };

  const createAccount = (e: React.FormEvent) => {
    e.preventDefault();
    if (!currency) {
      alert("Please select a currency.");
      return;
    }
    api.post("/api/accounts/", {
      name,
      account_type: accountType,
      balance,
      currency,
      institution: institution || null,
      official_number: officialNumber || null,
    })
      .then((res) => {
        if (res.status === 201) {
          alert("Account created successfully");
          resetForm();
          fetchAccounts();
        } else {
          alert("Something went wrong creating the account");
        }
      })
      .catch((err) => alert("Error creating account"));
  };

  const deleteAccount = (id: number) => {
    if (!window.confirm("Are you sure you want to delete this account?")) return;
    api.delete(`/api/accounts/${id}/`)
      .then((res) => {
        if (res.status === 204) {
          alert("Account deleted");
          fetchAccounts();
        } else {
          alert("Could not delete account");
        }
      })
      .catch((err) => alert("Error deleting account"));
  };

  const resetForm = () => {
    setName("");
    setAccountType("checking");
    setBalance("");
    setCurrency(null);
    setInstitution("");
    setOfficialNumber("");
  };

  return (
    <div>
      <h2>Accounts</h2>
      {accounts.length === 0 && <p>No accounts found.</p>}
      {accounts.map((acc) => (
        <div
          key={acc.id}
          style={{
            border: "1px solid #ccc",
            padding: "1rem",
            marginBottom: "1rem",
          }}
        >
          <p><strong>{acc.name}</strong></p>
          <p>Type: {acc.account_type}</p>
          <p>Balance: {acc.balance}</p>
          <p>Currency ID: {acc.currency}</p>
          {acc.institution && <p>Institution: {acc.institution}</p>}
          {acc.official_number && <p>Official #: {acc.official_number}</p>}
          <button onClick={() => deleteAccount(acc.id)}>Delete</button>
        </div>
      ))}

      <h2>Create New Account</h2>
      <form onSubmit={createAccount}>
        <label>
          Name
          <input
            type="text"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </label>
        <br />

        <label>
          Account Type
          <select
            value={accountType}
            onChange={(e) => setAccountType(e.target.value)}
          >
            <option value="checking">Checking</option>
            <option value="savings">Savings</option>
            <option value="credit">Credit</option>
          </select>
        </label>
        <br />

        <label>
          Balance
          <input
            type="number"
            required
            value={balance}
            onChange={(e) => setBalance(e.target.value)}
          />
        </label>
        <br />

        <label>
          Currency
          <select
            required
            value={currency ?? ""}
            onChange={(e) => setCurrency(Number(e.target.value))}
          >
            <option value="">--Select Currency--</option>
            {currencies.map((cur) => (
              <option key={cur.id} value={cur.id}>
                {cur.name} ({cur.code})
              </option>
            ))}
          </select>
        </label>
        <br />

        <label>
          Institution
          <input
            type="text"
            value={institution}
            onChange={(e) => setInstitution(e.target.value)}
          />
        </label>
        <br />

        <label>
          Official Number
          <input
            type="text"
            value={officialNumber}
            onChange={(e) => setOfficialNumber(e.target.value)}
          />
        </label>
        <br />

        <button type="submit">Create Account</button>
      </form>
    </div>
  );
};

export default Accounts;
