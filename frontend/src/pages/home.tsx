"use client"

import { useState, useEffect } from "react"
import { Search } from "lucide-react"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import RestaurantList from "@/components/restaurant-list"
import ChatInterface from "@/components/chat-interface"
import WebSocketChat from "@/components/websocket-chat"
import type { Restaurant, MenuItem } from "@/types/restaurant"

export default function HomePage() {
  const [restaurants, setRestaurants] = useState<Restaurant[]>([])
  const [filteredRestaurants, setFilteredRestaurants] = useState<Restaurant[]>([])
  const [searchQuery, setSearchQuery] = useState("")
  const [selectedRestaurant, setSelectedRestaurant] = useState<Restaurant | null>(null)
  const [menuItems, setMenuItems] = useState<MenuItem[]>([])
  const [showMenu, setShowMenu] = useState(false)
  const [_, setChatType] = useState<"rest" | "websocket">("rest")

  useEffect(() => {
    // Fetch restaurants from API
    const fetchRestaurants = async () => {
      try {
        const response = await fetch(`/api/restaurants`)
        const data = await response.json()
        setRestaurants(data)
        setFilteredRestaurants(data)
      } catch (error) {
        console.error("Error fetching restaurants:", error)
      }
    }

    fetchRestaurants()
  }, [])

  useEffect(() => {
    // Filter restaurants based on search query
    if (searchQuery.trim() === "") {
      setFilteredRestaurants(restaurants)
    } else {
      const filtered = restaurants.filter(
        (restaurant) =>
          restaurant.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
          restaurant.location.toLowerCase().includes(searchQuery.toLowerCase()),
      )
      setFilteredRestaurants(filtered)
    }
  }, [searchQuery, restaurants])

  const handleShowMenu = async (restaurant: Restaurant) => {
    setSelectedRestaurant(restaurant)
    setShowMenu(true)

    try {
      const response = await fetch(`/api/restaurant/menu/${restaurant.id}`)
      const data = await response.json()
      setMenuItems(data)
    } catch (error) {
      console.error("Error fetching menu:", error)
      setMenuItems([])
    }
  }

  const handleAskInChat = (restaurant: Restaurant) => {
    setSelectedRestaurant(restaurant)
    setShowMenu(false)
  }

  return (
    <div className="container flex flex-1 gap-4 py-2 w-full">
      <div className="flex w-full flex-col md:flex-row gap-4">
        <Card className="w-full md:w-1/3">
          <CardHeader className="pb-2">
            <CardTitle>Restaurants</CardTitle>
            <div className="relative">
              <Search className="absolute left-2 top-3 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search restaurants..."
                className="pl-8"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
          </CardHeader>
          <CardContent className="p-0">
            <ScrollArea className="h-[calc(100vh-220px)]">
              <RestaurantList
                restaurants={filteredRestaurants}
                onShowMenu={handleShowMenu}
                onAskInChat={handleAskInChat}
                selectedRestaurant={selectedRestaurant}
              />
            </ScrollArea>
          </CardContent>
        </Card>

        <Card className="w-full md:w-2/3">
          {showMenu && selectedRestaurant ? (
            <>
              <CardHeader>
                <CardTitle>{selectedRestaurant.name} - Menu</CardTitle>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-[calc(100vh-220px)]">
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
            </>
          ) : (
            <Tabs defaultValue="rest" onValueChange={(value) => setChatType(value as "rest" | "websocket")}>
              <CardHeader className="pb-0">
                <div className="flex justify-between items-center">
                  <TabsList>
                    <TabsTrigger value="rest">Ask Question</TabsTrigger>
                    <TabsTrigger value="websocket">ChatBot</TabsTrigger>
                  </TabsList>
                </div>
              </CardHeader>
              <TabsContent value="rest">
                <ChatInterface selectedRestaurant={selectedRestaurant} />
              </TabsContent>
              <TabsContent value="websocket">
                <WebSocketChat selectedRestaurant={selectedRestaurant} />
              </TabsContent>
            </Tabs>
          )}
        </Card>
      </div>
    </div>
  )
}
