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
                prompt_payload = self._build_prompt_from_name(
                    game_name,
                    content_type,
                    min_length,
                    max_length
                )
                logger.info(f"Generating {content_type} content for '{game_name}' (Claude will research game info)")
            elif game_data:
                prompt_payload = self._build_prompt(
                    game_data,
                    content_type,
                    min_length,
                    max_length
                )
                logger.info(f"Generating {content_type} content for {game_data.get('name', 'Unknown')}")
            else:
                logger.error("Either game_data or game_name must be provided")
                return None
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=prompt_payload["system"],
                messages=[
                    {
                        "role": "user",
                        "content": prompt_payload["user"]
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
    ) -> Dict[str, str]:
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
        
        system_prompt = self._build_system_prompt(
            game_name,
            content_type,
            min_length,
            max_length
        )
        user_prompt = f"""Viết một bài {content_type_vn} hoàn chỉnh, sẵn sàng đăng ngay.

Thông tin đã xác thực về game:
- Tên game: {game_name}
- Rating: {rating}/10
- Số người chơi: {min_players}-{max_players}
- Thời gian chơi: {playtime}
- Cơ chế chơi nổi bật: {mechanics}
- Mô tả ngắn: {description}

Ưu tiên:
- Bài viết phải hữu ích, dễ đọc và tạo cảm giác đáng tin.
- Tối ưu SEO/discoverability tự nhiên cho từ khóa "{game_name}" và các cụm liên quan đến boardgame.
- Nêu rõ game phù hợp với ai, điểm hấp dẫn khi chơi và lý do nên thử.
- Chỉ dùng thông tin được cung cấp ở trên; nếu thiếu dữ liệu thì diễn đạt thận trọng, không bịa thêm chi tiết.

Dàn ý bắt buộc:
{self._get_content_outline(content_type)}
"""

        return {"system": system_prompt, "user": user_prompt}
    
    def _build_prompt_from_name(
        self,
        game_name: str,
        content_type: str,
        min_length: int,
        max_length: int
    ) -> Dict[str, str]:
        """Build prompt for AI when only game name is available"""
        
        content_type_vn = {
            'review': 'đánh giá',
            'tutorial': 'hướng dẫn chơi',
            'strategy': 'hướng dẫn chiến thuật'
        }.get(content_type, 'đánh giá')
        
        system_prompt = self._build_system_prompt(
            game_name,
            content_type,
            min_length,
            max_length
        )
        user_prompt = f"""Viết một bài {content_type_vn} hoàn chỉnh, sẵn sàng đăng ngay, về boardgame "{game_name}".

Bạn có thể dựa vào kiến thức sẵn có để mô tả game này, nhưng phải tuân thủ các nguyên tắc sau:
- Chỉ nêu chi tiết cụ thể khi bạn thực sự chắc chắn.
- Nếu chưa chắc về rating, số người chơi, thời gian chơi hay cơ chế, hãy viết theo hướng tổng quát và thận trọng.
- Không bịa thêm thành tích, giải thưởng hoặc thông số chi tiết.
- Vẫn phải tối ưu SEO/discoverability tự nhiên cho từ khóa "{game_name}" và các truy vấn liên quan đến review/cách chơi/chiến thuật boardgame.

Dàn ý bắt buộc:
{self._get_content_outline(content_type)}
"""

        return {"system": system_prompt, "user": user_prompt}

    def _build_system_prompt(
        self,
        game_name: str,
        content_type: str,
        min_length: int,
        max_length: int
    ) -> str:
        """Build reusable system prompt with SEO and readability guidance."""

        content_type_vn = {
            'review': 'đánh giá',
            'tutorial': 'hướng dẫn chơi',
            'strategy': 'hướng dẫn chiến thuật'
        }.get(content_type, 'đánh giá')

        return f"""Bạn là content strategist chuyên về boardgame tại Việt Nam, đặc biệt giỏi viết bài Facebook để tăng tương tác tự nhiên.

Mục tiêu:
- Viết bài {content_type_vn} về "{game_name}" bằng tiếng Việt tự nhiên, đáng tin và cuốn hút.
- Ưu tiên tăng tương tác trên Facebook: giữ người đọc ở lại, khiến họ muốn comment, share hoặc tag bạn bè.
- Tối ưu khả năng tiếp cận cho người mới chơi lẫn người đã chơi boardgame một thời gian.

Yêu cầu tối ưu Facebook:
- Câu đầu tiên phải có hook mạnh, gần gũi, tạo cảm giác "đúng insight người chơi" hoặc khơi gợi tò mò.
- Từ khóa chính "{game_name}" phải xuất hiện tự nhiên ở đầu bài, giữa bài và gần cuối bài.
- Viết theo nhịp đọc nhanh trên newsfeed: câu ngắn, ý rõ, 3-5 đoạn ngắn, dễ đọc trên điện thoại.
- Ưu tiên ngôn ngữ gợi cảm xúc và trải nghiệm thực tế: vui ở điểm nào, căng ở điểm nào, vì sao dễ nghiện hoặc đáng thử.
- Lồng ghép tự nhiên các cụm liên quan như: boardgame, luật chơi, cơ chế chơi, số người chơi, thời gian chơi, phù hợp với ai.
- Cuối bài phải có CTA mềm để kéo bình luận, ví dụ hỏi trải nghiệm, hỏi gu chơi, hỏi có muốn review thêm game tương tự không.
- Có thể thêm 1 câu hỏi ngắn ở cuối để kích hoạt comment.
- Thêm 2-5 hashtag ở cuối, ưu tiên ít nhưng đúng; tránh cảm giác spam.

Quy tắc viết:
- Độ dài: {min_length}-{max_length} từ.
- Chỉ viết đoạn văn, không dùng bullet points, không dùng markdown headings.
- Giọng văn thân thiện, gần gũi, có chất hội thoại nhưng vẫn gọn và rõ.
- Không nhồi từ khóa, không lặp ý, không dùng câu quá máy móc hoặc quá quảng cáo.
- Tránh mở bài chung chung kiểu định nghĩa game; vào thẳng cảm giác, vấn đề hoặc điểm thú vị.
- Nội dung phải khiến người đọc cảm thấy "mình nên lưu bài này" hoặc "mình muốn tag bạn chơi cùng".
- Với bài chiến thuật, tránh spoiler sâu hoặc làm mất vui khi tự khám phá.
- Nếu dữ liệu chưa chắc chắn, dùng cách diễn đạt thận trọng thay vì khẳng định tuyệt đối.
"""

    def _get_content_outline(self, content_type: str) -> str:
        """Return required structure for each content type."""

        if content_type == 'review':
            return """1. Hook ngắn gọn và nhắc tự nhiên tên game
2. Giới thiệu nhanh game cùng thông tin cốt lõi
3. Phân tích trải nghiệm chơi, cơ chế nổi bật, điểm mạnh và điểm hạn chế
4. Kết luận game phù hợp với ai, vì sao nên thử và CTA ở cuối"""

        if content_type == 'tutorial':
            return """1. Hook ngắn gọn và giới thiệu vì sao game đáng thử
2. Mục tiêu game, setup cơ bản và cách bắt đầu
3. Luật chơi hoặc flow một lượt chơi theo cách dễ hiểu cho người mới
4. Mẹo nhập môn, đối tượng phù hợp và CTA ở cuối"""

        return """1. Hook ngắn gọn và giới thiệu điểm hấp dẫn của game
2. Các ưu tiên chiến thuật hoặc cơ chế cần tập trung
3. Sai lầm thường gặp, mẹo tối ưu quyết định và cách đọc thế trận
4. Kết luận game hợp với kiểu người chơi nào và CTA ở cuối"""
    
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

