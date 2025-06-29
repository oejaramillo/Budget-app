import React, { useEffect, useState } from "react";
import api from "../api";

type Currency = {
  id: number;
  name: string;
  code: string;
  exchange_rate: string;
  principal: boolean;
  is_active: boolean;
};

const Currencies: React.FC = () => {
  const [currencies, setCurrencies] = useState<Currency[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchCurrencies();
  }, []);

  const fetchCurrencies = () => {
    api
      .get("/api/currencies/")
      .then((res) => {
        setCurrencies(res.data);
        setLoading(false);
      })
      .catch((err) => {
        alert("Error loading currencies");
        setLoading(false);
      });
  };

  if (loading) return <p>Loading currencies...</p>;

  return (
    <div>
      <h2>Currencies</h2>
      {currencies.length === 0 && <p>No currencies found.</p>}

      <table style={{ borderCollapse: "collapse", width: "100%" }}>
        <thead>
          <tr>
            <th style={{ borderBottom: "1px solid #ccc", textAlign: "left" }}>Name</th>
            <th style={{ borderBottom: "1px solid #ccc", textAlign: "left" }}>Code</th>
            <th style={{ borderBottom: "1px solid #ccc", textAlign: "left" }}>Exchange Rate</th>
            <th style={{ borderBottom: "1px solid #ccc", textAlign: "left" }}>Principal</th>
            <th style={{ borderBottom: "1px solid #ccc", textAlign: "left" }}>Active</th>
          </tr>
        </thead>
        <tbody>
          {currencies.map((currency) => (
            <tr key={currency.id}>
              <td>{currency.name}</td>
              <td>{currency.code}</td>
              <td>{currency.exchange_rate}</td>
              <td>{currency.principal ? "Yes" : "No"}</td>
              <td>{currency.is_active ? "Yes" : "No"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default Currencies;
