import type { RouteObject } from 'react-router-dom'
import AppLayout from '@/routes/AppLayout'
import Dashboard from '@/pages/Dashboard'
import Login from '@/pages/Login'
import NotFound from '@/pages/NotFound'

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
    ],
  },
  {
    path: '*',
    element: <NotFound />,
  },
]

export default routes
