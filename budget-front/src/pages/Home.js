import React, { useState } from "react";
import axios from "axios";
import "./Home.css";

const Home = () => {
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [message, setMessage] = useState("");
  
    const handleSubmit = async (e) => {
      e.preventDefault();
      setMessage("");
      try {
        const response = await axios.post("http://localhost:8000/api/login/", {
          username,
          password,
        });
        setMessage("Login successful!");
        console.log("Token:", response.data.token);
        
        // Save token in localStorage or manage state
        localStorage.setItem("authtoken", response.data.token);

        // Redirect user
        window.location.href = "/dashboard";
      } catch (error) {
        if (error.response && error.response.status == 400) {
          setMessage("Invalid credentials, please try again.");
        } else {
          setMessage("Something went wrong, please try again later.");
        }
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