import { Navigate, Route, Routes } from 'react-router-dom';
import Login from './pages/Login';
import AdminLayout from './components/AdminLayout';
import UserManagement from './pages/UserManagement';
import LanguageManagement from './pages/LanguageManagement';
import PersonaManagement from './pages/PersonaManagement';
import PlanManagement from './pages/PlanManagement';
import ReportsLogs from './pages/ReportsLogs';
import { useAuth } from './hooks/useAuth';
import { ReactNode } from 'react';

function RequireAuth({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <RequireAuth>
            <AdminLayout />
          </RequireAuth>
        }
      >
        <Route index element={<Navigate to="/users" replace />} />
        <Route path="users" element={<UserManagement />} />
        <Route path="languages" element={<LanguageManagement />} />
        <Route path="personas" element={<PersonaManagement />} />
        <Route path="plans" element={<PlanManagement />} />
        <Route path="reports" element={<ReportsLogs />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
