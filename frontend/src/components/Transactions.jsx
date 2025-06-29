import { useState, useEffect } from "react";
import api from "../api";

function Transactions() {
  const [transactions, setTransactions] = useState([]);
  const [account, setAccount] = useState("");
  const [amount, setAmount] = useState("");
  const [description, setDescription] = useState("");

  useEffect(() => {
    getTransactions();
  }, []);

  const getTransactions = () => {
    api.get("/api/transactions/")
      .then((res) => res.data)
      .then((data) => { 
        setTransactions(data);
        console.log(data);
      })
      .catch((error) => alert(error));
  };

  const deleteTransaction = (id) => {
    api.delete(`/api/transactions/delete/${id}/`)
      .then((res) => {
        if (res.status === 204) alert("Transaction deleted successfully");
        else alert("Something went wrong deleting");
        getTransactions(); // Refresh after deletion
      })
      .catch((error) => alert(error));
  };

  const createTransaction = (e) => {
    e.preventDefault();
    api.post("/api/transactions/", { 
        account, 
        amount, 
        description 
      })
      .then((res) => {
        if (res.status === 201) alert("Transaction created successfully");
        else alert("Something went wrong creating");
        // Reset form
        setAccount("");
        setAmount("");
        setDescription("");
        getTransactions(); // Refresh after creation
      })
      .catch((error) => alert(error));
  };

  return (
    <div>
      <h2>Transactions</h2>
      {transactions.map((tx) => (
        <div key={tx.id} style={{ marginBottom: "1rem", borderBottom: "1px solid #ccc" }}>
          <p><strong>Account:</strong> {tx.account?.name || tx.account}</p>
          <p><strong>Amount:</strong> {tx.amount}</p>
          <p><strong>Description:</strong> {tx.description}</p>
          <button onClick={() => deleteTransaction(tx.id)}>Delete</button>
        </div>
      ))}

      <h2>Create Transaction</h2>
      <form onSubmit={createTransaction}>
        <label htmlFor="account">Account</label>
        <input
          type="text"
          id="account"
          name="account"
          required
          onChange={(e) => setAccount(e.target.value)}
          value={account}
        />
        <label htmlFor="amount">Amount</label>
        <input
          type="number"
          id="amount"
          name="amount"
          required
          onChange={(e) => setAmount(e.target.value)}
          value={amount}
        />
        <label htmlFor="description">Description</label>
        <textarea
          id="description"
          name="description"
          required
          onChange={(e) => setDescription(e.target.value)}
          value={description}
        />
        <input type="submit" value="Submit" />
      </form>
    </div>
  );
}

export default Transactions;
