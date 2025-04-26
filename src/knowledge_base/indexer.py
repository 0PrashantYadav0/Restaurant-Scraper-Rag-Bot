from typing import List, Dict
import json

class KnowledgeBaseIndexer:
    def __init__(self, data: List[Dict]):
        self.data = data
        self.index = {}

    def create_index(self):
        for entry in self.data:
            restaurant_name = entry.get('name')
            if restaurant_name:
                self.index[restaurant_name] = entry

    def search(self, query: str) -> List[Dict]:
        results = []
        for restaurant_name, details in self.index.items():
            if query.lower() in restaurant_name.lower() or any(query.lower() in str(value).lower() for value in details.values()):
                results.append(details)
        return results

    def save_index(self, file_path: str):
        with open(file_path, 'w') as f:
            json.dump(self.index, f)

    def load_index(self, file_path: str):
        with open(file_path, 'r') as f:
            self.index = json.load(f)