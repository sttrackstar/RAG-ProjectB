import React from "react";
import { Link } from "react-router-dom";
import SignupForm from "../components/SignupForm";
import "../styles/Signup.css";
function Signup({ onSignup }) {
  return (
    <main>
      <h1>Research Aide</h1>
      <h2>Create Account</h2>

      <SignupForm onSignup={onSignup} />

      <p>
        Already have an account?{" "}
        <Link to="/login">Login</Link>
      </p>
    </main>
  );
}

export default Signup;