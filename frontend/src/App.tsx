import { Routes, Route } from "react-router-dom"
import Layout from "./components/layout"
import HomePage from "./pages/home"
import RestaurantPage from "./pages/restaurant"

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="restaurant/:id" element={<RestaurantPage />} />
      </Route>
    </Routes>
  )
}

export default App
