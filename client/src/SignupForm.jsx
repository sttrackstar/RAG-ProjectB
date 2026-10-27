import React, { useState } from "react";

function SignupForm({ onSignup }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirmation, setPasswordConfirmation] =
    useState("");
  const [errors, setErrors] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  function handleSubmit(e) {
    e.preventDefault();
    setErrors([]);

    if (password !== passwordConfirmation) {
      setErrors(["Passwords do not match."]);
      return;
    }

    setIsLoading(true);

    fetch("/signup", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        username,
        password,
      }),
    })
      .then((response) => {
        setIsLoading(false);

        if (response.ok) {
          return response
            .json()
            .then((user) => onSignup(user));
        }

        return response.json().then((errorData) => {
          setErrors(
            errorData.errors || [
              errorData.error || "Signup failed.",
            ]
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
        <label htmlFor="signup-username">
          Username
        </label>

        <input
          type="text"
          autoComplete="username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required
        />
      </div>

      <div>
        <label htmlFor="signup-password">
          Password
        </label>

        <input
          type="password"
          autoComplete="new-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
      </div>

      <div>
        <label htmlFor="password-confirmation">
          Confirm Password
        </label>

        <input
          type="password"
          autoComplete="new-password"
          value={passwordConfirmation}
          onChange={(e) =>
            setPasswordConfirmation(e.target.value)
          }
          required
        />
      </div>

      <div>
        <button type="submit" disabled={isLoading}>
          {isLoading ? "Creating account..." : "Sign Up"}
        </button>
      </div>

      <div className="error-message">
        {errors.map((error, index) => (
          <p key={`${error}-${index}`}>{error}</p>
        ))}
      </div>
    </form>
  );
}

export default SignupForm;