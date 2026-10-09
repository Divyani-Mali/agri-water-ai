import { useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { useAuth } from "../context/authContext";
import { errorMessage } from "../api/client";
import AuthShell from "../components/AuthShell";
import Button from "../components/ui/Button";
import FormField from "../components/ui/FormField";
import { Banner } from "../components/ui/Feedback";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function Login() {
  const { user, login, restoreError } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState({});
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  if (user) return <Navigate to="/" replace />;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (loading) return;
    setError("");

    const found = {};
    if (!EMAIL_RE.test(email.trim())) found.email = "Enter a valid email address";
    if (!password) found.password = "Enter your password";
    setErrors(found);
    if (Object.keys(found).length) return;

    setLoading(true);
    try {
      await login(email.trim(), password);
      // AuthProvider now has the user, so this page redirects to Farms
    } catch (err) {
      setError(errorMessage(err));
      setLoading(false);
    }
  };

  return (
    <AuthShell
      title="Welcome back"
      subtitle="Log in to monitor your fields."
      footer={
        <>
          New to Smart Irrigation AI?{" "}
          <Link to="/register" className="font-medium text-forest-700 hover:underline">
            Create an account
          </Link>
        </>
      }
    >
      <form onSubmit={handleSubmit} noValidate className="space-y-4">
        {restoreError && (
          <Banner tone="warning" title="Could not restore your saved session">
            {restoreError} Your saved token was kept; you can retry by refreshing once the server is available.
          </Banner>
        )}
        {error && (
          <Banner tone="error" title="Could not log in">
            {error}
          </Banner>
        )}
        <FormField
          label="Email"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          error={errors.email}
          placeholder="you@example.com"
        />
        <FormField
          label="Password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          error={errors.password}
        />
        <div className="-mt-2 text-right">
          <Link to="/forgot-password" className="text-sm font-medium text-forest-700 hover:underline">
            Forgot password?
          </Link>
        </div>
        <Button type="submit" loading={loading} className="w-full">
          {loading ? "Logging in..." : "Log in"}
        </Button>
      </form>
    </AuthShell>
  );
}
