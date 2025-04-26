export interface MenuItem {
  name: string
  description: string
  price: number
  rating: number
  food_type: string
}

export interface Restaurant {
  id: string
  name: string
  location: string
  menu: MenuItem[]
}
