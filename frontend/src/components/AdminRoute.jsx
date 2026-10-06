import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../context/authContext'

export default function AdminRoute() {
  const { user } = useAuth()
  return user?.role === 'admin' ? <Outlet /> : <Navigate to="/" replace />
}