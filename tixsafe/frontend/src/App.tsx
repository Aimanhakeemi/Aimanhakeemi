import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, auth, type User } from "./api";
import { Browse, EventPage } from "./pages/Browse";
import { ListingPage } from "./pages/ListingPage";
import { OrdersPage, OrderPage } from "./pages/Orders";
import { SellPage } from "./pages/Sell";
import { LoginPage } from "./pages/Login";
import { AdminPage } from "./pages/Admin";
import { HowItWorks } from "./pages/HowItWorks";

type Session = { user: User | null; setUser: (u: User | null) => void; refresh: () => Promise<void> };
const SessionContext = createContext<Session>({ user: null, setUser: () => {}, refresh: async () => {} });
export const useSession = () => useContext(SessionContext);

export const go = (path: string) => {
  window.location.hash = path;
};

function useRoute(): string[] {
  const read = () => window.location.hash.replace(/^#\/?/, "").split("/").filter(Boolean);
  const [route, setRoute] = useState(read);
  useEffect(() => {
    const onChange = () => {
      setRoute(read());
      window.scrollTo(0, 0);
    };
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return route;
}

export function App() {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);
  const route = useRoute();

  const refresh = useCallback(async () => {
    if (!auth.token) return setUser(null);
    try {
      setUser(await api<User>("/me"));
    } catch {
      auth.token = null;
      setUser(null);
    }
  }, []);

  useEffect(() => {
    refresh().finally(() => setReady(true));
  }, [refresh]);

  const [page, id] = route;
  const needsLogin = ["orders", "order", "sell", "admin"].includes(page ?? "") && !user;

  let content: React.ReactNode;
  if (!ready) content = null;
  else if (needsLogin) content = <LoginPage next={window.location.hash} />;
  else if (page === "event") content = <EventPage id={Number(id)} />;
  else if (page === "listing") content = <ListingPage id={Number(id)} />;
  else if (page === "orders") content = <OrdersPage />;
  else if (page === "order") content = <OrderPage id={Number(id)} />;
  else if (page === "sell") content = <SellPage />;
  else if (page === "login") content = <LoginPage next="#/" />;
  else if (page === "admin") content = <AdminPage />;
  else if (page === "how") content = <HowItWorks />;
  else content = <Browse />;

  return (
    <SessionContext.Provider value={{ user, setUser, refresh }}>
      <header className="topbar">
        <div className="wrap topbar-inner">
          <a href="#/" className="brand">
            <span className="brand-mark" aria-hidden>
              ✓
            </span>
            TixSafe
          </a>
          <nav>
            <a href="#/">Buy</a>
            <a href="#/sell">Sell</a>
            <a href="#/how">How it works</a>
            {user && <a href="#/orders">My orders</a>}
            {user?.is_admin && <a href="#/admin">Disputes</a>}
            {user ? (
              <button
                className="link"
                onClick={() => {
                  auth.token = null;
                  setUser(null);
                  go("/");
                }}
              >
                Log out
              </button>
            ) : (
              <a href="#/login" className="btn small">
                Log in
              </a>
            )}
          </nav>
        </div>
      </header>
      <main className="wrap">{content}</main>
      <footer className="wrap footer">
        Every payment is held in escrow until after the show. Never pay a seller outside TixSafe.
      </footer>
    </SessionContext.Provider>
  );
}
