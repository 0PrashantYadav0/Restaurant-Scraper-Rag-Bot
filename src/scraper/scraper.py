import requests
from bs4 import BeautifulSoup
import json
import time
import uuid
import random
import re
import os

class RestaurantScraper:
    def __init__(self, urls):
        self.urls = urls
        self.restaurant_data = []
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }

    def scrape(self):
        for url in self.urls:
            try:
                print(f"Scraping: {url}")
                response = requests.get(url, headers=self.headers)
                response.raise_for_status()  # Check for HTTP errors
                
                # Check if HTML file or URL
                if os.path.isfile(url):
                    with open(url, 'r', encoding='utf-8') as f:
                        content = f.read()
                    soup = BeautifulSoup(content, 'html.parser')
                else:
                    soup = BeautifulSoup(response.text, 'html.parser')
                
                self.extract_data(soup, url)
                time.sleep(random.uniform(1, 3))  # Respectful scraping
            except requests.RequestException as e:
                print(f"Error fetching {url}: {e}")
            except Exception as e:
                print(f"Error processing {url}: {e}")

    def extract_data(self, soup, url):
        restaurant_info = {}
        
        restaurant_info['id'] = str(uuid.uuid4())
        restaurant_info['name'] = self.get_restaurant_name(soup, url)
        restaurant_info['location'] = self.get_restaurant_location(soup)
        restaurant_info['menu'] = self.get_menu_items(soup)
        restaurant_info['special_features'] = self.get_special_features(soup)
        restaurant_info['operating_hours'] = self.get_operating_hours(soup)
        restaurant_info['contact_info'] = self.get_contact_info(soup)
        restaurant_info['url'] = url
        
        print(f"Extracted data for restaurant: {restaurant_info['name']}")
        self.restaurant_data.append(restaurant_info)

    def get_restaurant_name(self, soup, url):
        # Try multiple selectors that might contain the restaurant name
        name_selectors = [
            soup.find('h1', class_='restaurant-name'),
            soup.find('h1'),  # Any h1 tag
            soup.find(['h1', 'h2'], class_=lambda c: c and ('title' in c or 'name' in c) if c else False),
            soup.find('title'),  # Page title
            soup.select_one('.logo img'),  # Logo image alt text
        ]
        
        # Try each selector until we find something
        raw_name = None
        for selector in name_selectors:
            if selector:
                # If it's an img tag, use alt attribute
                if selector.name == 'img' and selector.get('alt'):
                    raw_name = selector.get('alt').strip()
                    break
                # Otherwise use text content
                elif hasattr(selector, 'text') and selector.text.strip():
                    raw_name = selector.text.strip()
                    break
        
        # If no name was found in selectors, fall back to URL extraction
        if not raw_name:
            domain = url.split('//')[-1].split('/')[0]
            parts = re.sub(r'www\.|\.com|\.co\.in|\.net', '', domain).split('.')
            raw_name = ' '.join(word.capitalize() for word in parts if word) or "Restaurant"
            print(f"Fallback name from URL: {raw_name}")
        
        clean_name = raw_name.replace("Order ", "").replace(" from EatSure", "").strip()
        return clean_name

    def get_restaurant_location(self, soup):
        # Try multiple selectors for location
        location_selectors = [
            soup.find('p', class_='restaurant-location'),
            soup.find('address'),
            soup.find(['p', 'div'], class_=lambda c: c and 'address' in c if c else False),
            soup.find(['p', 'div'], string=lambda s: s and re.search(r'\d+.*(street|road|avenue|blvd)', str(s), re.I) if s else False),
            soup.find(['p', 'div'], id=lambda i: i and 'address' in i if i else False),
        ]
        
        for selector in location_selectors:
            if selector and hasattr(selector, 'text') and selector.text.strip():
                return selector.text.strip()
        
        return "Location information not available"

    def get_menu_items(self, soup):
        menu_items = []
        
        # Try to find EatSure style menu cards first
        product_cards = soup.select('figure[data-qa="smallProductCard"]')
        
        if product_cards:
            print(f"Found {len(product_cards)} EatSure style menu items")
            
            for card in product_cards:
                try:
                    # Extract name
                    name_element = card.select_one('div[data-qa="productName"]')
                    name = name_element.text.strip() if name_element else "Unknown Item"
                    
                    # Extract description
                    desc_element = card.select_one('p[data-qa="productInfo"]')
                    description = desc_element.text.strip() if desc_element else ""
                    
                    # Extract price
                    price_element = card.select_one('span[data-qa="totalPrice"]')
                    price = price_element.text.strip() if price_element else "Price not available"
                    
                    # Extract rating if available
                    rating_element = card.select_one('div[data-qa="productRating"]')
                    rating = None
                    if rating_element:
                        rating_match = re.search(r'(\d+\.\d+)', rating_element.text.strip())
                        rating = rating_match.group(1) if rating_match else None
                    
                    # Determine if veg or non-veg
                    veg_indicator = card.select_one('div[data-qa="isVeg"]')
                    non_veg_indicator = card.select_one('div[data-qa="isNonVeg"]')
                    
                    food_type = "Not specified"
                    if veg_indicator:
                        food_type = "Vegetarian"
                    elif non_veg_indicator:
                        food_type = "Non-Vegetarian"
                    
                    menu_items.append({
                        'name': clean_text(name),
                        'description': clean_text(description),
                        'price': extract_price(price),
                        'rating': rating,
                        'food_type': food_type
                    })
                except Exception as e:
                    print(f"Error processing menu item: {e}")
                    continue
        
        # If no EatSure style cards found, try generic approach
        if not menu_items:
            # Try alternative approaches
            menu_sections = soup.find_all(['section', 'div'], class_=lambda c: c and ('menu' in c or 'food' in c or 'dish' in c) if c else False)
            menu_items_elements = []
            
            if menu_sections:
                for section in menu_sections:
                    menu_items_elements.extend(section.find_all(['h3', 'h4', 'div', 'li']))
            else:
                # Looking for common menu item patterns
                price_pattern = re.compile(r'[\$₹€£](\d+(\.\d{2})?)')
                menu_items_elements = soup.find_all(['div', 'li'], string=lambda s: s and price_pattern.search(s) if s else False)
                
                if not menu_items_elements:
                    menu_items_elements = soup.find_all(['h3', 'h4'], string=lambda s: s and len(s) > 3 if s else False)
        
            # Process found elements
            for item in menu_items_elements:
                # Try to extract name, description, price
                name = item.text.strip()
                description = ""
                price = ""
                
                # Look for next elements that might be descriptions
                next_elem = item.next_sibling
                if next_elem and hasattr(next_elem, 'text') and next_elem.text.strip():
                    description = next_elem.text.strip()
                
                # Look for price pattern
                price_match = re.search(r'[\$₹€£]\s*(\d+(\.\d{2})?)', item.text)
                if price_match:
                    price = price_match.group(0)
                    # Remove price from name if it's there
                    name = name.replace(price, '').strip()
                
                if name:
                    menu_items.append({
                        'name': clean_text(name)[:50],  # Limit to reasonable length
                        'description': clean_text(description)[:200] if description else "No description available",
                        'price': extract_price(price) if price else "Price not listed",
                        'rating': None,
                        'food_type': "Not specified"
                    })
                    
                    # Limit to reasonable number of items
                    if len(menu_items) >= 30:
                        break
        
        # If we still haven't found any menu items, create placeholder items
        if not menu_items:
            menu_items = [
                {
                    'name': 'Signature Dish', 
                    'description': 'Restaurant\'s special dish', 
                    'price': 'Inquire for price',
                    'rating': None,
                    'food_type': "Not specified"
                }
            ]
        
        return menu_items

    def get_special_features(self, soup):
        features = []
        # Look for specific keywords across the page
        page_text = soup.get_text().lower()
        
        # Check for vegetarian options
        if any(word in page_text for word in ['vegetarian', 'vegan', 'plant-based']):
            features.append('Vegetarian options available')
            
        # Check for gluten-free options
        if any(word in page_text for word in ['gluten-free', 'gluten free', 'gf']):
            features.append('Gluten-free options available')
            
        # Check for other common features
        if 'delivery' in page_text:
            features.append('Delivery service')
        
        if 'takeaway' in page_text or 'take-away' in page_text or 'take out' in page_text:
            features.append('Takeaway available')
        
        if 'reservation' in page_text or 'book a table' in page_text:
            features.append('Reservations accepted')
            
        if 'outdoor' in page_text or 'patio' in page_text or 'terrace' in page_text:
            features.append('Outdoor seating')
            
        # If no features detected, add a generic one
        if not features:
            features.append('Traditional dining experience')
            
        return features

    def get_operating_hours(self, soup):
        # Try multiple selectors
        hours_selectors = [
            soup.find('p', class_='operating-hours'),
            soup.find(['div', 'section', 'p'], class_=lambda c: c and ('hours' in c or 'timing' in c) if c else False),
            soup.find(string=lambda s: s and re.search(r'(mon|tue|wed|thu|fri|sat|sun).*\d+:\d+', str(s), re.I) if s else False),
        ]
        
        for selector in hours_selectors:
            if selector:
                if hasattr(selector, 'text'):
                    return selector.text.strip()
                else:
                    return str(selector).strip()
        
        # Look for common patterns in the page text
        hours_pattern = re.search(r'(open|hours|timing).*?\d{1,2}(:\d{2})?\s*(am|pm|AM|PM)?.*\d{1,2}(:\d{2})?\s*(am|pm|AM|PM)?', soup.get_text())
        if hours_pattern:
            return hours_pattern.group(0)
            
        return "Hours information not available"

    def get_contact_info(self, soup):
        # Try to find contact information
        contact_patterns = {
            'phone': r'(?:Phone|Tel|Call)(?:\s*(?:us|:))?\s*[+]?(?:\d{1,4}[\s-]?)?(?:\d{3}[\s-]?)\d{3}[\s-]?\d{4}',
            'email': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        }
        
        contact_info = ""
        
        # Check for phone numbers
        phone_match = re.search(contact_patterns['phone'], soup.get_text())
        if phone_match:
            contact_info += f"Phone: {phone_match.group(0)} "
            
        # Check for email
        email_match = re.search(contact_patterns['email'], soup.get_text())
        if email_match:
            contact_info += f"Email: {email_match.group(0)}"
            
        if not contact_info:
            contact_info = "Contact information not available"
            
        return contact_info.strip()

    def save_data(self, filename='restaurant_data.json'):
        # Ensure the directory exists
        os.makedirs(os.path.dirname(filename) or '.', exist_ok=True)
        
        print(f"Saving data to {filename}")
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.restaurant_data, f, indent=4, ensure_ascii=False)
        
        print(f"Saved data for {len(self.restaurant_data)} restaurants")

# Function to make it importable from main.py
def scrape_restaurant_data(urls, output_filename='restaurant_data.json'):
    """
    Scrape data from restaurant websites and save it to a JSON file.
    
    Args:
        urls: List of restaurant website URLs to scrape
        output_filename: Path where the JSON data will be saved
        
    Returns:
        List of dictionaries containing restaurant data
    """
    scraper = RestaurantScraper(urls)
    scraper.scrape()
    scraper.save_data(output_filename)
    return scraper.restaurant_data

def retrieve_restaurant_data(query, restaurant_data, top_k=3):
    """
    Retrieve relevant restaurant menu items based on user query
    
    Args:
        query: User query string
        restaurant_data: List of restaurant data dictionaries
        top_k: Number of results to return
        
    Returns:
        List of relevant menu items with restaurant info
    """
    # Flatten the restaurant data - extract all menu items with restaurant context
    menu_items = []
    
    for restaurant in restaurant_data:
        for item in restaurant.get('menu', []):
            # Create enriched menu item with restaurant context
            enriched_item = {
                'restaurant_name': restaurant['name'],
                'restaurant_location': restaurant.get('location', 'Unknown location'),
                'dish_name': item['name'],
                'description': item['description'],
                'price': item['price'],
                'rating': item.get('rating', 'Not rated'),
                'food_type': item.get('food_type', 'Not specified')
            }
            menu_items.append(enriched_item)
    
    # Simple keyword matching for demo purposes
    # In a real implementation, you'd use vector embeddings or a proper search algorithm
    query_terms = query.lower().split()
    scored_items = []
    
    for item in menu_items:
        score = 0
        item_text = f"{item['dish_name']} {item['description']}".lower()
        
        for term in query_terms:
            if term in item_text:
                score += 1
        
        if score > 0:
            scored_items.append((score, item))
    
    # Sort by score and return top_k results
    scored_items.sort(reverse=True, key=lambda x: x[0])
    return [item for _, item in scored_items[:top_k]]

def clean_text(text):
    """Cleans the input text by removing unnecessary whitespace and special characters."""
    import re
    if not text:
        return ""
    text = text.strip()
    text = re.sub(r'\s+', ' ', text)  # Replace multiple spaces with a single space
    return text  # Keeping punctuation for better descriptions

def extract_price(price_text):
    """Extracts numerical price from text with currency symbols"""
    import re
    if not price_text:
        return None
    match = re.search(r'[\$₹€£]?\s*(\d+(?:\.\d{2})?)', price_text)
    if match:
        return float(match.group(1))
    return None