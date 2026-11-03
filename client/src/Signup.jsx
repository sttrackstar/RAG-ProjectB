import SignupForm from "./SignupForm";

function Signup({ onSignup, onSwitch }) {
  return (
    <main className="app auth">
      <h1>Research Aide</h1>
      <h2>Create Account</h2>

      <SignupForm onSignup={onSignup} />

      <p>
        Already have an account?{" "}
        <button type="button" className="link-button" onClick={onSwitch}>Login</button>
      </p>
    </main>
  );
}

export default Signup;
