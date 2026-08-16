import { useNavigate } from "react-router-dom";

function Login() {
  const navigate = useNavigate();

  const handleLogin = () => {
    window.location.href = "http://localhost:8000/api/auth/google";
  };

  return (
    <div>
      <h1>Google Drive RAG</h1>

      <p>Chat with your Google Drive documents.</p>

      <button onClick={handleLogin}>Login with Google</button>
    </div>
  );
}

export default Login;
