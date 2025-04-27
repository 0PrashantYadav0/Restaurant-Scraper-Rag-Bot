import { useState, useEffect } from "react"
import { useParams, Link } from "react-router-dom"
import { ArrowLeft } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import ChatInterface from "@/components/chat-interface"
import type { Restaurant, MenuItem } from "@/types/restaurant"

export default function RestaurantPage() {
  const { id } = useParams<{ id: string }>()
  const [restaurant, setRestaurant] = useState<Restaurant | null>(null)
  const [menuItems, setMenuItems] = useState<MenuItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchRestaurantDetails = async () => {
      setLoading(true)
      try {
        // Fetch restaurant details
        const restaurantResponse = await fetch(`/api/restaurant/${id}`)
        if (!restaurantResponse.ok) {
          throw new Error("Restaurant not found")
        }
        const restaurantData = await restaurantResponse.json()
        setRestaurant(restaurantData)

        // Fetch menu items
        const menuResponse = await fetch(`/api/restaurant/menu/${id}`)
        const menuData = await menuResponse.json()
        setMenuItems(menuData)
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load restaurant")
        console.error("Error fetching restaurant details:", err)
      } finally {
        setLoading(false)
      }
    }

    if (id) {
      fetchRestaurantDetails()
    }
  }, [id])

  if (loading) {
    return (
      <div className="container py-8 text-center">
        <p>Loading restaurant details...</p>
      </div>
    )
  }

  if (error || !restaurant) {
    return (
      <div className="container py-8 text-center">
        <p className="text-destructive">{error || "Restaurant not found"}</p>
        <Button asChild className="mt-4">
          <Link to="/">Back to Home</Link>
        </Button>
      </div>
    )
  }

  return (
    <div className="container py-2">
      <Button variant="ghost" asChild className="mb-4">
        <Link to="/">
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Restaurants
        </Link>
      </Button>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>{restaurant.name}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex justify-between">
              <div className="mb-4">
                <h3 className="font-medium">Location</h3>
                <p>{restaurant.location}</p>
              </div>
              <div className="mb-4">
                <h3 className="font-medium">Contact Info</h3>
                <p>{restaurant.contact}</p>
              </div>
            </div>
            <div className="mb-4">
              <h3 className="font-medium">URL</h3>
              <div className="text-blue-500 hover:underline">
                <a href={restaurant.url} target="_blank" rel="noopener noreferrer">
                  {restaurant.url}
                </a>
              </div>
            </div>
            <div className="mb-4">
              {restaurant.special_features.length > 0 && (
                <>
                  <h3 className="font-medium">Special Features</h3>
                  <ul className="list-disc pl-5">
                    {restaurant.special_features.map((feature, index) => (
                      <li key={index} className="text-sm text-muted-foreground">
                        {feature}
                      </li>
                    ))}
                  </ul>
                </>
              )}
            </div>
            <h3 className="font-medium mb-2">Menu</h3>
            <ScrollArea className="h-[400px]">
              {menuItems.length > 0 ? (
                <div className="grid gap-4">
                  {menuItems.map((item, index) => (
                    <div key={index} className="border rounded-lg p-4">
                      <div className="flex justify-between">
                        <h3 className="font-medium">{item.name}</h3>
                        <span className="font-bold">₹{item.price}</span>
                      </div>
                      <p className="text-sm text-muted-foreground">{item.description}</p>
                      <div className="mt-2 flex items-center gap-2">
                        <span className="text-xs px-2 py-1 bg-secondary rounded-full">{item.food_type}</span>
                        <span className="text-xs px-2 py-1 bg-secondary rounded-full">Rating: {item.rating}/5</span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p>No menu items available</p>
              )}
            </ScrollArea>
          </CardContent>
        </Card>

        <Card>
          <ChatInterface selectedRestaurant={restaurant} />
        </Card>
      </div>
    </div>
  )
}
