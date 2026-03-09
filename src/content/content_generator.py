"""
AI Content Generation Module
"""
import time
from typing import Dict, Optional
from anthropic import Anthropic

from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class AIContentGenerator:
    """Generate content using Claude AI"""
    
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        """
        Initialize AI content generator
        
        Args:
            api_key: Anthropic API key
            model: Claude model to use
        """
        self.client = Anthropic(api_key=api_key)
        self.model = model
    
    def generate_content(
        self,
        game_data: Optional[Dict] = None,
        game_name: Optional[str] = None,
        content_type: str = "review",
        min_length: int = 250,
        max_length: int = 400
    ) -> Optional[str]:
        """
        Generate content for a boardgame
        
        Args:
            game_data: Game data dictionary from BGG scraper (optional)
            game_name: Game name if game_data is not available (optional)
            content_type: Type of content (review, tutorial, strategy)
            min_length: Minimum word count
            max_length: Maximum word count
        
        Returns:
            Generated content string or None
        """
        try:
            # If no game_data, use game_name and let Claude research
            if not game_data and game_name:
                prompt = self._build_prompt_from_name(game_name, content_type, min_length, max_length)
                logger.info(f"Generating {content_type} content for '{game_name}' (Claude will research game info)")
            elif game_data:
                prompt = self._build_prompt(game_data, content_type, min_length, max_length)
                logger.info(f"Generating {content_type} content for {game_data.get('name', 'Unknown')}")
            else:
                logger.error("Either game_data or game_name must be provided")
                return None
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            content = response.content[0].text if response.content else None
            
            if content:
                # Validate content
                if self._validate_content(content, min_length, max_length):
                    logger.info(f"Successfully generated content ({len(content)} chars)")
                    return content
                else:
                    logger.warning("Generated content did not meet validation criteria, retrying...")
                    # Retry once
                    time.sleep(1)
                    if game_data:
                        return self.generate_content(game_data=game_data, content_type=content_type, min_length=min_length, max_length=max_length)
                    elif game_name:
                        return self.generate_content(game_name=game_name, content_type=content_type, min_length=min_length, max_length=max_length)
                    else:
                        logger.error("Cannot retry: missing both game_data and game_name")
                        return None
            else:
                logger.error("Empty response from AI")
                return None
                
        except Exception as e:
            logger.error(f"Error generating content: {e}")
            return None
    
    def _build_prompt(
        self,
        game_data: Dict,
        content_type: str,
        min_length: int,
        max_length: int
    ) -> str:
        """Build prompt for AI"""
        
        game_name = game_data.get('name', 'Unknown')
        rating = game_data.get('rating', 'N/A')
        min_players = game_data.get('min_players', 'N/A')
        max_players = game_data.get('max_players', 'N/A')
        playtime = f"{game_data.get('min_playtime', 'N/A')}-{game_data.get('max_playtime', 'N/A')} phút"
        mechanics = ', '.join(game_data.get('mechanics', [])[:5]) or 'N/A'
        description = game_data.get('description', '')[:500]  # Limit description length
        
        content_type_vn = {
            'review': 'đánh giá',
            'tutorial': 'hướng dẫn chơi',
            'strategy': 'hướng dẫn chiến thuật'
        }.get(content_type, 'đánh giá')
        
        system_prompt = f"""Bạn là chuyên gia boardgame Việt Nam. Nhiệm vụ: viết {content_type_vn} về boardgame "{game_name}" bằng tiếng Việt.

Thông tin game:
- Rating: {rating}/10
- Số người chơi: {min_players}-{max_players}
- Thời gian chơi: {playtime}
- Cơ chế chơi: {mechanics}
- Mô tả: {description}

Yêu cầu:
- Độ dài: {min_length}-{max_length} từ
- Tone: thân thiện, dễ hiểu, nhiệt huyết
- Format: đoạn văn, không dùng bullet points
- Thêm hashtags phù hợp ở cuối (ví dụ: #boardgame #boardgamesvietnam #{game_name.lower().replace(' ', '')})
- Tránh spoiler nếu là hướng dẫn chiến thuật
- Viết bằng tiếng Việt tự nhiên, không dịch máy

Cấu trúc nội dung:
"""
        
        if content_type == 'review':
            system_prompt += """
1. Hook - 1-2 câu thu hút về game
2. Giới thiệu game - 2-3 câu
3. Phân tích cơ chế chơi và gameplay
4. Điểm mạnh và điểm yếu
5. Phù hợp với ai
6. Kết luận và recommendation
"""
        elif content_type == 'tutorial':
            system_prompt += """
1. Hook - giới thiệu game
2. Setup cơ bản
3. Mục tiêu của game
4. Luật chơi cơ bản
5. Flow một lượt chơi
6. Tips cho người mới
"""
        else:  # strategy
            system_prompt += """
1. Hook - giới thiệu game
2. Cơ chế chơi quan trọng
3. Chiến thuật cơ bản
4. Tips và tricks nâng cao
5. Common mistakes cần tránh
6. Kết luận
"""
        
        return system_prompt
    
    def _build_prompt_from_name(
        self,
        game_name: str,
        content_type: str,
        min_length: int,
        max_length: int
    ) -> str:
        """Build prompt for AI when only game name is available"""
        
        content_type_vn = {
            'review': 'đánh giá',
            'tutorial': 'hướng dẫn chơi',
            'strategy': 'hướng dẫn chiến thuật'
        }.get(content_type, 'đánh giá')
        
        system_prompt = f"""Bạn là chuyên gia boardgame Việt Nam. Nhiệm vụ: viết {content_type_vn} về boardgame "{game_name}" bằng tiếng Việt.

Bạn cần tự tìm hiểu thông tin về game này (rating, số người chơi, thời gian chơi, cơ chế chơi, mô tả) dựa trên kiến thức của bạn về boardgame "{game_name}".

Yêu cầu:
- Độ dài: {min_length}-{max_length} từ
- Tone: thân thiện, dễ hiểu, nhiệt huyết
- Format: đoạn văn, không dùng bullet points
- Thêm hashtags phù hợp ở cuối (ví dụ: #boardgame #boardgamesvietnam #{game_name.lower().replace(' ', '')})
- Tránh spoiler nếu là hướng dẫn chiến thuật
- Viết bằng tiếng Việt tự nhiên, không dịch máy
- Nếu bạn không biết rõ về game này, hãy viết dựa trên thông tin chung về boardgame cùng tên hoặc tương tự

Cấu trúc nội dung:
"""
        
        if content_type == 'review':
            system_prompt += """
1. Hook - 1-2 câu thu hút về game
2. Giới thiệu game - 2-3 câu (bao gồm thông tin cơ bản như số người chơi, thời gian, rating nếu biết)
3. Phân tích cơ chế chơi và gameplay
4. Điểm mạnh và điểm yếu
5. Phù hợp với ai
6. Kết luận và recommendation
"""
        elif content_type == 'tutorial':
            system_prompt += """
1. Hook - giới thiệu game
2. Setup cơ bản
3. Mục tiêu của game
4. Luật chơi cơ bản
5. Flow một lượt chơi
6. Tips cho người mới
"""
        else:  # strategy
            system_prompt += """
1. Hook - giới thiệu game
2. Cơ chế chơi quan trọng
3. Chiến thuật cơ bản
4. Tips và tricks nâng cao
5. Common mistakes cần tránh
6. Kết luận
"""
        
        return system_prompt
    
    def _validate_content(self, content: str, min_length: int, max_length: int) -> bool:
        """
        Validate generated content
        
        Args:
            content: Generated content
            min_length: Minimum word count
            max_length: Maximum word count
        
        Returns:
            True if valid, False otherwise
        """
        word_count = len(content.split())
        
        if word_count < min_length:
            logger.warning(f"Content too short: {word_count} words (min: {min_length})")
            return False
        
        if word_count > max_length:
            logger.warning(f"Content too long: {word_count} words (max: {max_length})")
            return False
        
        # Check for basic quality indicators
        if len(content) < 100:
            return False
        
        # Check for hashtags
        if '#' not in content:
            logger.warning("Content missing hashtags")
            # Not critical, just a warning
        
        return True

