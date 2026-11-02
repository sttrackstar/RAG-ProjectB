import React from "react";
import {Link} from "react-router-dom";
import LoginForm from "../components/LoginForm";
function Login({ onLogin }) {
  return (
    <main>
      <h1>Research Aide</h1>
      <h2>Login</h2>
      <LoginForm onLogin={onLogin} />
      <p>
        No Account?{" "}
        <Link to ="/signup">Sign up</Link>
        
      </p>
    </main>
  );
}

export default Login;