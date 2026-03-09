"""
BoardGameGeek API scraper module
"""
import time
import random
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Any
from pathlib import Path
import json
import requests
from datetime import datetime, timedelta

from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class BGGScraper:
    """Scraper for BoardGameGeek API"""
    
    BASE_URL = "https://boardgamegeek.com/xmlapi2"
    RATE_LIMIT_DELAY = 1.5  # seconds between requests
    
    # Headers required by BGG API
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/xml, text/xml, */*',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    def __init__(self, api_token: Optional[str] = None, data_file: str = "data/boardgames.json", posted_logs: str = "data/posted_logs.json"):
        """
        Initialize BGG scraper
        
        Args:
            api_token: BGG API token for authentication (required)
            data_file: Path to store game data
            posted_logs: Path to store posted games log
        """
        self.data_file = Path(data_file)
        self.posted_logs = Path(posted_logs)
        self.data_file.parent.mkdir(parents=True, exist_ok=True)
        self.posted_logs.parent.mkdir(parents=True, exist_ok=True)
        
        # Set up headers with authentication
        self.headers = self.HEADERS.copy()
        if api_token:
            self.headers['Authorization'] = f'Bearer {api_token}'
        else:
            logger.warning("BGG API token not provided. API requests may fail with 401 Unauthorized.")
            logger.warning("Get your API token at: https://boardgamegeek.com/applications")
        
        # Load existing data
        self.games_db = self._load_json(self.data_file, [])
        self.posted_games = self._load_json(self.posted_logs, [])
        
        # Rate limiting
        self.last_request_time = 0
    
    def _load_json(self, file_path: Path, default: Any) -> Any:
        """Load JSON file or return default if not exists"""
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Error loading {file_path}: {e}")
        return default
    
    def _save_json(self, file_path: Path, data: any):
        """Save data to JSON file"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving {file_path}: {e}")
    
    def _rate_limit(self):
        """Enforce rate limiting"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.RATE_LIMIT_DELAY:
            time.sleep(self.RATE_LIMIT_DELAY - elapsed)
        self.last_request_time = time.time()
    
    def search_game(self, name: str) -> Optional[str]:
        """
        Search for a game by name and return game ID
        
        Args:
            name: Game name to search
        
        Returns:
            Game ID if found, None otherwise
        """
        self._rate_limit()
        
        try:
            url = f"{self.BASE_URL}/search"
            params = {
                'query': name,
                'type': 'boardgame',
                'exact': 0
            }
            
            response = requests.get(url, params=params, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            root = ET.fromstring(response.content)
            items = root.findall('.//item')
            
            if items:
                game_id = items[0].get('id')
                logger.info(f"Found game '{name}': ID {game_id}")
                return game_id
            else:
                logger.warning(f"No game found for '{name}'")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error searching game '{name}': {e}")
            return None
        except ET.ParseError as e:
            logger.error(f"Error parsing XML response: {e}")
            return None
    
    def get_game_details(self, game_id: str) -> Optional[Dict]:
        """
        Get detailed information about a game
        
        Args:
            game_id: BGG game ID
        
        Returns:
            Dictionary with game details or None
        """
        self._rate_limit()
        
        try:
            url = f"{self.BASE_URL}/thing"
            params = {
                'id': game_id,
                'stats': 1
            }
            
            response = requests.get(url, params=params, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            root = ET.fromstring(response.content)
            item = root.find('.//item')
            
            if item is None:
                logger.warning(f"No item found for game ID {game_id}")
                return None
            
            # Parse game data
            game_data = {
                'id': game_id,
                'name': self._get_primary_name(item),
                'alternate_names': self._get_alternate_names(item),
                'year_published': self._get_year_published(item),
                'min_players': self._get_int_value(item, 'minplayers'),
                'max_players': self._get_int_value(item, 'maxplayers'),
                'min_playtime': self._get_int_value(item, 'minplaytime'),
                'max_playtime': self._get_int_value(item, 'maxplaytime'),
                'min_age': self._get_int_value(item, 'minage'),
                'rating': self._get_rating(item),
                'complexity': self._get_complexity(item),
                'num_ratings': self._get_num_ratings(item),
                'mechanics': self._get_links(item, 'boardgamemechanic'),
                'categories': self._get_links(item, 'boardgamecategory'),
                'description': self._get_description(item),
                'image_url': self._get_image_url(item),
            }
            
            logger.info(f"Fetched details for game ID {game_id}: {game_data['name']}")
            return game_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching game details for ID {game_id}: {e}")
            return None
        except ET.ParseError as e:
            logger.error(f"Error parsing XML for game ID {game_id}: {e}")
            return None
    
    def _get_primary_name(self, item: ET.Element) -> str:
        """Get primary name of the game"""
        name_elem = item.find(".//name[@type='primary']")
        return name_elem.get('value') if name_elem is not None else "Unknown"
    
    def _get_alternate_names(self, item: ET.Element) -> List[str]:
        """Get alternate names"""
        names = []
        for name_elem in item.findall(".//name[@type='alternate']"):
            names.append(name_elem.get('value'))
        return names
    
    def _get_year_published(self, item: ET.Element) -> Optional[int]:
        """Get year published"""
        year_elem = item.find('yearpublished')
        if year_elem is not None:
            try:
                return int(year_elem.get('value', 0))
            except ValueError:
                return None
        return None
    
    def _get_int_value(self, item: ET.Element, tag: str) -> Optional[int]:
        """Get integer value from element"""
        elem = item.find(tag)
        if elem is not None:
            try:
                return int(elem.get('value', 0))
            except ValueError:
                return None
        return None
    
    def _get_rating(self, item: ET.Element) -> Optional[float]:
        """Get average rating"""
        stats = item.find('statistics')
        if stats is not None:
            ratings = stats.find('ratings')
            if ratings is not None:
                avg_elem = ratings.find('average')
                if avg_elem is not None:
                    try:
                        return float(avg_elem.get('value', 0))
                    except ValueError:
                        return None
        return None
    
    def _get_complexity(self, item: ET.Element) -> Optional[float]:
        """Get complexity/weight rating"""
        stats = item.find('statistics')
        if stats is not None:
            ratings = stats.find('ratings')
            if ratings is not None:
                weight_elem = ratings.find('averageweight')
                if weight_elem is not None:
                    try:
                        return float(weight_elem.get('value', 0))
                    except ValueError:
                        return None
        return None
    
    def _get_num_ratings(self, item: ET.Element) -> int:
        """Get number of ratings"""
        stats = item.find('statistics')
        if stats is not None:
            ratings = stats.find('ratings')
            if ratings is not None:
                usersrated_elem = ratings.find('usersrated')
                if usersrated_elem is not None:
                    try:
                        return int(usersrated_elem.get('value', 0))
                    except ValueError:
                        return 0
        return 0
    
    def _get_links(self, item: ET.Element, link_type: str) -> List[str]:
        """Get links (mechanics, categories, etc.)"""
        links = []
        for link in item.findall(f".//link[@type='{link_type}']"):
            links.append(link.get('value'))
        return links
    
    def _get_description(self, item: ET.Element) -> str:
        """Get game description"""
        desc_elem = item.find('description')
        if desc_elem is not None:
            # Remove HTML tags
            import re
            text = desc_elem.text or ""
            text = re.sub(r'<[^>]+>', '', text)
            return text.strip()
        return ""
    
    def _get_image_url(self, item: ET.Element) -> Optional[str]:
        """
        Get game image URL - prefer full size over thumbnail
        BGG API returns thumbnail URLs, we can convert them to full size
        """
        image_elem = item.find('image')
        if image_elem is not None and image_elem.text:
            image_url = image_elem.text
            # BGG thumbnail URLs can be converted to full size
            # Format: https://cf.geekdo-images.com/thumb/img-xxx.jpg -> https://cf.geekdo-images.com/img-xxx.jpg
            # Or: https://images.geekdo-images.com/xxx_thumb.jpg -> https://images.geekdo-images.com/xxx.jpg
            if 'thumb' in image_url:
                # Remove 'thumb' from URL to get full size
                image_url = image_url.replace('_thumb', '').replace('/thumb/', '/')
            elif '/thumb/' in image_url:
                image_url = image_url.replace('/thumb/', '/')
            return image_url
        return None
    
    def get_random_game(
        self,
        min_rating: float = 7.0,
        max_complexity: float = 4.0,
        min_players: int = 1,
        max_players: int = 8,
        avoid_recent_days: int = 30
    ) -> Optional[Dict]:
        """
        Get a random game that matches filters and hasn't been posted recently
        
        Args:
            min_rating: Minimum rating
            max_complexity: Maximum complexity
            min_players: Minimum players
            max_players: Maximum players
            avoid_recent_days: Don't select games posted in last N days
        
        Returns:
            Game data dictionary or None
        """
        # Get top games list (we'll use a range of popular games)
        # BGG doesn't have a direct API for this, so we'll search for popular terms
        # or use a predefined list of popular game names
        
        # For now, we'll try searching for some popular games
        popular_searches = [
            "Catan", "Ticket to Ride", "Pandemic", "Wingspan", "Azul",
            "Splendor", "7 Wonders", "Carcassonne", "Terraforming Mars",
            "Gloomhaven", "Spirit Island", "Everdell", "Brass", "Concordia"
        ]
        
        max_attempts = 20
        for attempt in range(max_attempts):
            # Try to get a game from our database first
            if self.games_db:
                filtered_games = [
                    g for g in self.games_db
                    if self._matches_filters(g, min_rating, max_complexity, min_players, max_players)
                    and not self._was_posted_recently(g['id'], avoid_recent_days)
                ]
                
                if filtered_games:
                    game = random.choice(filtered_games)
                    logger.info(f"Selected game from database: {game['name']}")
                    return game
            
            # If no suitable game in database, search for a new one
            search_term = random.choice(popular_searches)
            game_id = self.search_game(search_term)
            
            if game_id:
                game_data = self.get_game_details(game_id)
                if game_data and self._matches_filters(game_data, min_rating, max_complexity, min_players, max_players):
                    if not self._was_posted_recently(game_id, avoid_recent_days):
                        # Save to database
                        self.save_to_database(game_data)
                        logger.info(f"Selected new game: {game_data['name']}")
                        return game_data
            
            time.sleep(0.5)  # Small delay between attempts
        
        logger.warning("Could not find a suitable game after multiple attempts")
        return None
    
    def _matches_filters(
        self,
        game: Dict,
        min_rating: float,
        max_complexity: float,
        min_players: int,
        max_players: int
    ) -> bool:
        """Check if game matches filter criteria"""
        if game.get('rating', 0) < min_rating:
            return False
        if game.get('complexity', 10) > max_complexity:
            return False
        if game.get('min_players', 0) > max_players:
            return False
        if game.get('max_players', 0) < min_players:
            return False
        return True
    
    def _was_posted_recently(self, game_id: str, days: int) -> bool:
        """Check if game was posted in the last N days"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        for posted in self.posted_games:
            if posted.get('game_id') == game_id:
                posted_date = datetime.fromisoformat(posted.get('posted_at', ''))
                if posted_date > cutoff_date:
                    return True
        return False
    
    def save_to_database(self, game_data: Dict):
        """Save game data to database"""
        # Check if game already exists
        existing_index = None
        for i, game in enumerate(self.games_db):
            if game.get('id') == game_data.get('id'):
                existing_index = i
                break
        
        if existing_index is not None:
            # Update existing
            self.games_db[existing_index] = game_data
        else:
            # Add new
            self.games_db.append(game_data)
        
        self._save_json(self.data_file, self.games_db)
        logger.info(f"Saved game to database: {game_data['name']}")

