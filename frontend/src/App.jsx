import { Link, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import SystemBuilder from './pages/SystemBuilder'
import ProductList from './pages/ProductList'
import ProductDetail from './pages/ProductDetail'
import Stores from './pages/Stores'
import StoreDetail from './pages/StoreDetail'
import Login from './pages/Login'
import MyBuilds from './pages/MyBuilds'
import Admin from './pages/admin/Admin'
import AdminProducts from './pages/admin/AdminProducts'
import AdminListings from './pages/admin/AdminListings'
import AdminStores from './pages/admin/AdminStores'
import AdminUsers from './pages/admin/AdminUsers'
import { PageTitle } from './components/ui'

function NotFound() {
  return (
    <div>
      <PageTitle>Page not found</PageTitle>
      <p>
        <Link to="/" className="link">Back to build</Link>
      </p>
    </div>
  )
}

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<SystemBuilder />} />
        <Route path="products" element={<ProductList />} />
        <Route path="products/:slug" element={<ProductList />} />
        <Route path="product/:id" element={<ProductDetail />} />
        <Route path="stores" element={<Stores />} />
        <Route path="stores/:id" element={<StoreDetail />} />
        <Route path="login" element={<Login />} />
        <Route path="builds" element={<MyBuilds />} />
        <Route path="admin" element={<Admin />}>
          <Route index element={<AdminProducts />} />
          <Route path="listings" element={<AdminListings />} />
          <Route path="stores" element={<AdminStores />} />
          <Route path="users" element={<AdminUsers />} />
        </Route>
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}
