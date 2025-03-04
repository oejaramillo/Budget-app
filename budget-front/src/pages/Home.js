import React, { useState } from "react";
import axios from "axios";
import "/home/edu/edu/repositorios/Budget-app/budget-front/src/styles/Home.css";

const Home = () => {
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [message, setMessage] = useState("");
  
    const handleSubmit = async (e) => {
      e.preventDefault();
      setMessage("");
  
      try {
          const response = await fetch("http://127.0.0.1:8000/api/v1/auth/token/", {
              method: "POST",
              headers: {
                  "Content-Type": "application/json",
              },
              body: JSON.stringify({ username, password }),
          });
  
          const data = await response.json();
  
          if (response.ok) {
              console.log("Access Token:", data.access);
              console.log("Refresh Token:", data.refresh);
              
              localStorage.setItem("access_token", data.access);
              localStorage.setItem("refresh_token", data.refresh);
  
              window.location.href = "/dashboard";
          } else {
              setMessage("Invalid credentials, please try again.");
          }
      } catch (error) {
          setMessage("Something went wrong, please try again later.");
      }
  };
  

    return (
        <div className="home-container">
            <div className="form-container">
                <h1>Budget App</h1>
                <form onSubmit={handleSubmit}>
                    <input 
                    type="text"
                    placeholder="Nombre de usuario"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    required
                    />
                    <input 
                    type="password"
                    placeholder="Contraseña"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    />
                    <button type="submit">Inicio de Sesión</button>
                </form>
                {message && <p className="message">{message}</p>}
            </div>
        </div>
    );
};

export default Home;