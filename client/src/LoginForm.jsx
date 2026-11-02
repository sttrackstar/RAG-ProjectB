import React, { useState } from "react";

function LoginForm({ onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  function handleSubmit(e) {
    e.preventDefault();
    setIsLoading(true);
    setErrors([]);

    fetch("/login", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ username, password }),
    })
      .then((response) => {
        setIsLoading(false);

        if (response.ok) {
          return response.json().then((user) => onLogin(user));
        }

        return response.json().then((errorData) => {
          setErrors(
            errorData.errors || [errorData.error || "Login failed."]
          );
        });
      })
      .catch(() => {
        setIsLoading(false);
        setErrors(["Unable to connect to the server."]);
      });
  }

  return (
    <form onSubmit={handleSubmit}>
      <div>
        <label htmlFor="username">Username</label>
        <input
          type="text"
          id="username"
          autoComplete="off"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />
      </div>

      <div>
        <label htmlFor="password">Password</label>
        <input
          type="password"
          id="password"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
      </div>

      <div>
        <button type="submit" disabled={isLoading}>
          {isLoading ? "Loading..." : "Login"}
        </button>
      </div>

      <div>
        {errors.map((error, index) => (
          <p key={`${error}-${index}`}>{error}</p>
        ))}
      </div>
    </form>
  );
}

export default LoginForm;