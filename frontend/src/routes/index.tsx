import type { RouteObject } from 'react-router-dom'
import AppLayout from '@/routes/AppLayout'
import Dashboard from '@/pages/Dashboard'
import Login from '@/pages/Login'
import NotFound from '@/pages/NotFound'
import Products from '@/pages/Products'
import ProductForm from '@/pages/ProductForm'
import Customers from '@/pages/Customers'
import CustomerForm from '@/pages/CustomerForm'

const routes: RouteObject[] = [
  {
    path: '/login',
    element: <Login />,
  },
  {
    path: '/',
    element: <AppLayout />,
    children: [
      { index: true, element: <Dashboard /> },
      { path: 'products', element: <Products /> },
      { path: 'products/new', element: <ProductForm /> },
      { path: 'products/:id/edit', element: <ProductForm /> },
      { path: 'customers', element: <Customers /> },
      { path: 'customers/new', element: <CustomerForm /> },
      { path: 'customers/:id/edit', element: <CustomerForm /> },
    ],
  },
  {
    path: '*',
    element: <NotFound />,
  },
]

export default routes
