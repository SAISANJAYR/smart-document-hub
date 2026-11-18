import { lazy, Suspense } from 'react';
import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { AuthProvider, useAuth } from './context/AuthContext';
import { LangProvider } from './lib/i18n';
import Header from './components/Header';
import { Loading } from './components/ui';
import Landing from './pages/Landing';
import { Login, Register } from './pages/Auth';

const Dashboard = lazy(() => import('./pages/Dashboard'));
const Library = lazy(() => import('./pages/Library'));
const DocumentDetail = lazy(() => import('./pages/DocumentDetail'));
const Ask = lazy(() => import('./pages/Ask'));
const Search = lazy(() => import('./pages/Search'));
const Calendar = lazy(() => import('./pages/Calendar'));
const Graph = lazy(() => import('./pages/Graph'));
const History = lazy(() => import('./pages/History'));

function Protected({ children }) {
  const { isAuthenticated, ready } = useAuth();
  const loc = useLocation();
  if (!ready) return <Loading />;
  if (!isAuthenticated) return <Navigate to="/login" replace state={{ from: loc.pathname + loc.search }} />;
  return children;
}

function GuestOnly({ children }) {
  const { isAuthenticated, ready } = useAuth();
  if (!ready) return <Loading />;
  return isAuthenticated ? <Navigate to="/dashboard" replace /> : children;
}

function NotFound() {
  return (
    <div className="page">
      <h1>Page not found</h1>
      <p className="muted mt-12">The page you were looking for doesn’t exist.</p>
    </div>
  );
}

export default function App() {
  const p = (el) => <Protected>{el}</Protected>;
  return (
    <LangProvider>
      <AuthProvider>
        <BrowserRouter>
          <Header />
          <Toaster
            position="bottom-right"
            toastOptions={{
              style: { fontFamily: 'var(--sans)', fontSize: 13, border: '1px solid var(--line)', boxShadow: '0 8px 24px rgba(0,0,0,.08)', borderRadius: 8 },
              success: { iconTheme: { primary: '#2f7a4d', secondary: '#fff' } },
            }}
          />
          <Suspense fallback={<Loading />}>
            <Routes>
              <Route path="/" element={<Landing />} />
              <Route path="/login" element={<GuestOnly><Login /></GuestOnly>} />
              <Route path="/register" element={<GuestOnly><Register /></GuestOnly>} />
              <Route path="/dashboard" element={p(<Dashboard />)} />
              <Route path="/library" element={p(<Library />)} />
              <Route path="/library/:id" element={p(<DocumentDetail />)} />
              <Route path="/ask" element={p(<Ask />)} />
              <Route path="/search" element={p(<Search />)} />
              <Route path="/calendar" element={p(<Calendar />)} />
              <Route path="/graph" element={p(<Graph />)} />
              <Route path="/history" element={p(<History />)} />
              <Route path="*" element={<NotFound />} />
            </Routes>
          </Suspense>
        </BrowserRouter>
      </AuthProvider>
    </LangProvider>
  );
}
