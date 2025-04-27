from typing import List, Dict
import json

class KnowledgeBaseIndexer:
    def __init__(self, data: List[Dict]):
        self.data = data
        self.index = {}
        self.name_to_id = {}

    def create_index(self):
        for entry in self.data:
            restaurant_id = entry.get('id')
            restaurant_name = entry.get('name')
            
            if restaurant_id:
                self.index[restaurant_id] = entry
                
                # Create name-to-id mapping for name-based lookups
                if restaurant_name:
                    self.name_to_id[restaurant_name] = restaurant_id
            # Fallback to name-based indexing if no ID is available
            elif restaurant_name:
                self.index[restaurant_name] = entry

    def search(self, query: str) -> List[Dict]:
        results = []
        # Check ID-based index
        for restaurant_id, details in self.index.items():
            restaurant_name = details.get('name', '')
            
            # Check if query is in any field values or in the restaurant name
            if (query.lower() in restaurant_name.lower() or 
                query.lower() in restaurant_id.lower() or 
                any(query.lower() in str(value).lower() for value in details.values())):
                results.append(details)
        return results

    def save_index(self, file_path: str):
        index_data = {
            "index": self.index,
            "name_to_id": self.name_to_id
        }
        with open(file_path, 'w') as f:
            json.dump(index_data, f)

    def load_index(self, file_path: str):
        with open(file_path, 'r') as f:
            index_data = json.load(f)
            self.index = index_data.get("index", {})
            self.name_to_id = index_data.get("name_to_id", {})
            