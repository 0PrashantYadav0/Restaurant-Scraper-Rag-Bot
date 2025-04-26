import { Outlet } from "react-router-dom"
import { Moon, Sun } from "lucide-react"
import { useTheme } from "./theme-provider"
import { Button } from "@/components/ui/button"

export default function Layout() {
  const { theme, setTheme } = useTheme()

  const toggleTheme = () => {
    setTheme(theme === "dark" ? "light" : "dark")
  }

  return (
    <div className="flex flex-col px-20 w-full fixed h-screen items-center">
      <header className="border-b bg-background flex justify-between items-end w-full">
        <div className="container flex h-14 items-center justify-between bg-[#f72f42] px-12 rounded-xl mt-2 mb-1 w-full">
          <a href="/" className="text-2xl font-bold text-white">
            Zomato Explorer
          </a>
          <Button variant="ghost" size="icon" onClick={toggleTheme}>
            {theme === "dark" ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
          </Button>
        </div>
      </header>
      <main className="flex-1 h-full">
        <Outlet />
      </main>
    </div>
  )
}
