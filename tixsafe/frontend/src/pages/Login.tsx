import { useState } from "react";
import { api, auth, type User } from "../api";
import { useSession } from "../App";
import { ErrorNote } from "../components";

export function LoginPage({ next }: { next: string }) {
  const { setUser } = useSession();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    try {
      const res = await api<{ token: string; user: User }>(`/auth/${mode}`, { body: form });
      auth.token = res.token;
      setUser(res.user);
      window.location.hash = next === "#/login" ? "#/" : next;
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <form className="card narrow" onSubmit={submit}>
      <h1>{mode === "login" ? "Log in" : "Create an account"}</h1>
      {mode === "register" && (
        <label>
          Name
          <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required minLength={2} />
        </label>
      )}
      <label>
        Email
        <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
      </label>
      <label>
        Password
        <input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required minLength={8} />
      </label>
      <button className="btn wide">{mode === "login" ? "Log in" : "Sign up"}</button>
      <ErrorNote error={error} />
      <p className="small">
        {mode === "login" ? "New here? " : "Have an account? "}
        <button type="button" className="link" onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(null); }}>
          {mode === "login" ? "Create an account" : "Log in"}
        </button>
      </p>
      <p className="small muted">Demo accounts: buyer@demo.my, seller@demo.my, admin@tixsafe.my · password123</p>
    </form>
  );
}
