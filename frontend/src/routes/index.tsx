import { Navigate, type RouteObject } from 'react-router-dom';
import MainLayout from '../components/MainLayout';
import LoginPage from '../pages/Login';
import DashboardPage from '../pages/Dashboard';
import ProductsPage from '../pages/Products';
import CustomersPage from '../pages/Customers';
import OrdersPage from '../pages/Orders';
import ProtectedRoute from './ProtectedRoute';

const routes: RouteObject[] = [
  { path: '/login', element: <LoginPage /> },
  {
    path: '/',
    element: (
      <ProtectedRoute>
        <MainLayout />
      </ProtectedRoute>
    ),
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: 'dashboard', element: <DashboardPage /> },
      { path: 'products', element: <ProductsPage /> },
      { path: 'customers', element: <CustomersPage /> },
      { path: 'sales-orders', element: <OrdersPage /> },
    ],
  },
];

export default routes;
