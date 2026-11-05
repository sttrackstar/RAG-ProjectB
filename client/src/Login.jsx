import LoginForm from "./LoginForm";

function Login({ onLogin, onSwitch }) {
  return (
    <main className="app auth">
      <h1>Research Aide</h1>
      <h2>Login</h2>
      <LoginForm onLogin={onLogin} />
      <p>
        No Account?{" "}
        <button type="button" className="link-button" onClick={onSwitch}>Sign up</button>
      </p>
    </main>
  );
}

export default Login;
