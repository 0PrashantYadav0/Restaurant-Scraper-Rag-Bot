"use client"

import { Link } from "react-router-dom"
import type { Restaurant } from "@/types/restaurant"
import { Button } from "@/components/ui/button"
import { Utensils, MessageSquare, ExternalLink } from "lucide-react"

interface RestaurantListProps {
  restaurants: Restaurant[]
  onShowMenu: (restaurant: Restaurant) => void
  onAskInChat: (restaurant: Restaurant) => void
  selectedRestaurant: Restaurant | null
}

export default function RestaurantList({
  restaurants,
  onShowMenu,
  onAskInChat,
  selectedRestaurant,
}: RestaurantListProps) {
  return (
    <div className="divide-y">
      {restaurants.length > 0 ? (
        restaurants.map((restaurant) => (
          <div
            key={restaurant.id}
            className={`p-4 hover:bg-muted/50 transition-colors ${
              selectedRestaurant?.id === restaurant.id ? "bg-muted" : ""
            }`}
          >
            <div className="mb-2 flex justify-between items-start">
              <div>
                <h3 className="font-medium">{restaurant.name}</h3>
                <p className="text-sm text-muted-foreground">{restaurant.location}</p>
              </div>
              <Button variant="ghost" size="icon" asChild className="ml-2 -mt-1">
                <Link to={`/restaurant/${restaurant.id}`}>
                  <ExternalLink className="h-4 w-4" />
                </Link>
              </Button>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" className="flex-1" onClick={() => onShowMenu(restaurant)}>
                <Utensils className="mr-2 h-4 w-4" />
                Show Menu
              </Button>
              <Button variant="default" size="sm" className="flex-1 bg-primary" onClick={() => onAskInChat(restaurant)}>
                <MessageSquare className="mr-2 h-4 w-4" />
                Ask in Chat
              </Button>
            </div>
          </div>
        ))
      ) : (
        <div className="p-4 text-center text-muted-foreground">No restaurants found</div>
      )}
    </div>
  )
}
