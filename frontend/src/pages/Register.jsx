import { useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { useAuth } from "../context/authContext";
import { errorMessage } from "../api/client";
import AuthShell from "../components/AuthShell";
import Button from "../components/ui/Button";
import FormField from "../components/ui/FormField";
import { Banner } from "../components/ui/Feedback";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function validateRegistration({ name, email, password, confirm }) {
  const e = {};
  if (name.trim().length < 2) e.name = "Name must be at least 2 characters";
  if (!EMAIL_RE.test(email.trim())) e.email = "Enter a valid email address";
  if (password.length < 8) e.password = "Password must be at least 8 characters";
  else if (!/[A-Za-z]/.test(password) || !/\d/.test(password))
    e.password = "Password must include at least one letter and one number";
  if (confirm !== password) e.confirm = "Passwords do not match";
  return e;
}

export default function Register() {
  const { user, register } = useAuth();
  const [form, setForm] = useState({ name: "", email: "", password: "", confirm: "" });
  const [errors, setErrors] = useState({});
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  if (user) return <Navigate to="/" replace />;

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (loading) return;
    setError("");
    const found = validateRegistration(form);
    setErrors(found);
    if (Object.keys(found).length) return;

    setLoading(true);
    try {
      await register(form.name.trim(), form.email.trim(), form.password);
    } catch (err) {
      setError(errorMessage(err));
      setLoading(false);
    }
  };

  return (
    <AuthShell
      title="Create your account"
      subtitle="Start monitoring and forecasting irrigation needs."
      footer={
        <>
          Already registered?{" "}
          <Link to="/login" className="font-medium text-forest-700 hover:underline">
            Log in
          </Link>
        </>
      }
    >
      <form onSubmit={handleSubmit} noValidate className="space-y-4">
        {error && (
          <Banner tone="error" title="Could not create account">
            {error}
          </Banner>
        )}
        <FormField label="Full name" autoComplete="name" value={form.name} onChange={set("name")} error={errors.name} />
        <FormField label="Email" type="email" autoComplete="email" value={form.email} onChange={set("email")} error={errors.email} />
        <FormField
          label="Password"
          type="password"
          autoComplete="new-password"
          value={form.password}
          onChange={set("password")}
          error={errors.password}
          hint="At least 8 characters, with a letter and a number"
        />
        <FormField
          label="Confirm password"
          type="password"
          autoComplete="new-password"
          value={form.confirm}
          onChange={set("confirm")}
          error={errors.confirm}
        />
        <Button type="submit" loading={loading} className="w-full">
          {loading ? "Creating account..." : "Create account"}
        </Button>
      </form>
    </AuthShell>
  );
}
