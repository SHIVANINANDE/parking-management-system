import { Routes, Route } from 'react-router-dom'
import Layout from './layouts/Layout'
import Dashboard from './pages/Dashboard'
import ParkingLots from './pages/ParkingLots'
import Reservations from './pages/Reservations'
import Login from './pages/Login'

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="parking-lots" element={<ParkingLots />} />
        <Route path="reservations" element={<Reservations />} />
      </Route>
    </Routes>
  )
}

export default App
