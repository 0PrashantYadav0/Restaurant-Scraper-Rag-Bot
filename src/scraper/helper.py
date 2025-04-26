import re
from typing import Dict, List, Any

def clean_text(text: str) -> str:
    """Clean text by removing extra spaces, special characters, etc."""
    if not text:
        return ""
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_features(restaurant_data: Dict) -> Dict[str, Any]:
    """Extract features from the new restaurant data format"""
    features = {
        "cuisine_types": restaurant_data.get("cuisine_types", []),
        "has_vegetarian": False,
        "has_vegan": False,
        "has_gluten_free": False,
        "price_range": restaurant_data.get("price_range", ""),
        "rating": restaurant_data.get("rating", {}).get("average", 0),
        "review_count": restaurant_data.get("rating", {}).get("count", 0)
    }
    
    # Extract dietary features from menu items
    menu = restaurant_data.get("menu", {})
    all_items = []
    for category in menu.get("categories", []):
        all_items.extend(category.get("items", []))
    
    # Check if any menu items have special dietary options
    for item in all_items:
        if "vegetarian" in [tag.lower() for tag in item.get("dietary_info", [])]:
            features["has_vegetarian"] = True
        if "vegan" in [tag.lower() for tag in item.get("dietary_info", [])]:
            features["has_vegan"] = True
        if "gluten-free" in [tag.lower() for tag in item.get("dietary_info", [])]:
            features["has_gluten_free"] = True
    
    return features

def format_restaurant_info(restaurant: Dict) -> str:
    """Format restaurant information for use in the chatbot context"""
    info = [
        f"Restaurant: {restaurant['name']}",
        f"Location: {restaurant['location']}",
        f"Cuisine: {', '.join(restaurant.get('features', {}).get('cuisine_types', []))}",
        f"Price Range: {restaurant.get('features', {}).get('price_range', '')}"
    ]
    
    # Add dietary information
    dietary_features = []
    if restaurant.get('features', {}).get('has_vegetarian'):
        dietary_features.append("Vegetarian options available")
    if restaurant.get('features', {}).get('has_vegan'):
        dietary_features.append("Vegan options available")
    if restaurant.get('features', {}).get('has_gluten_free'):
        dietary_features.append("Gluten-free options available")
    
    if dietary_features:
        info.append("Dietary Options: " + ", ".join(dietary_features))
    
    return "\n".join(info)