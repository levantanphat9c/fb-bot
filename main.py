#!/usr/bin/env python3
"""
Main controller for Boardgame Bot
"""
import argparse
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

from src.research.bgg_scraper import BGGScraper
from src.content.content_generator import AIContentGenerator
from src.images.image_handler import ImageHandler
from src.social.facebook_poster import FacebookPoster
from src.utils.config_loader import load_config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def run_bot(
    game_name: Optional[str] = None,
    content_type: Optional[str] = None,
    dry_run: Optional[bool] = None,
    manual_approve: bool = False
) -> bool:
    """
    Run the complete bot workflow
    
    Args:
        game_name: Optional specific game name to post
        content_type: Optional content type (review/tutorial/strategy)
        dry_run: If True, don't actually post to Facebook. If None, use config value.
        manual_approve: If True, wait for manual approval before posting
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Load configuration
        logger.info("Loading configuration...")
        config = load_config()
        
        # Set dry_run: use explicit value if provided, otherwise use config
        if dry_run is None:
            dry_run = config.get('facebook', {}).get('dry_run', False)
        
        # Initialize modules
        logger.info("Initializing modules...")
        
        # Research module - only initialize if token is available
        research_config = config.get('research', {})
        bgg_token = config.get('bgg', {}).get('api_token')
        scraper = None
        use_bgg = bool(bgg_token)
        
        if use_bgg:
            scraper = BGGScraper(api_token=bgg_token)
            logger.info("BGG API token found - will use BGG for game data")
        else:
            logger.warning("BGG_API_TOKEN not found - will skip BGG and let Claude handle game research")
            logger.warning("Get your token at: https://boardgamegeek.com/applications")
        
        # Content module
        anthropic_key = config.get('anthropic', {}).get('api_key')
        if not anthropic_key:
            logger.error("ANTHROPIC_API_KEY not found in environment or config")
            return False
        
        content_config = config.get('content', {})
        content_gen = AIContentGenerator(
            api_key=anthropic_key,
            model=content_config.get('ai_model', 'claude-sonnet-4-20250514')
        )
        
        # Image module
        image_config = config.get('images', {})
        image_handler = ImageHandler(
            max_size_mb=image_config.get('max_size_mb', 5.0),
            min_width=image_config.get('min_width', 720),
            min_height=image_config.get('min_height', 720),
            preferred_format=image_config.get('preferred_format', 'jpg')
        )
        
        # Facebook module
        facebook_config = config.get('facebook', {})
        facebook_poster = FacebookPoster(
            page_id=facebook_config.get('page_id'),
            access_token=facebook_config.get('access_token'),
            api_version=facebook_config.get('api_version', 'v24.0'),
            dry_run=dry_run
        )
        
        # Step 1: Research game
        logger.info("=" * 50)
        logger.info("STEP 1: Researching game...")
        logger.info("=" * 50)
        
        game_data = None
        selected_game_name = None
        
        if use_bgg and scraper:
            # Use BGG API if token is available
            if game_name:
                game_id = scraper.search_game(game_name)
                if not game_id:
                    logger.error(f"Game '{game_name}' not found on BGG")
                    return False
                game_data = scraper.get_game_details(game_id)
            else:
                game_data = scraper.get_random_game(
                    min_rating=research_config.get('min_rating', 7.0),
                    max_complexity=research_config.get('max_complexity', 4.0),
                    min_players=research_config.get('min_players', 1),
                    max_players=research_config.get('max_players', 8),
                    avoid_recent_days=research_config.get('avoid_recent_days', 30)
                )
            
            if not game_data:
                logger.error("Failed to get game data from BGG")
                return False
            
            selected_game_name = game_data['name']
            logger.info(f"Selected game from BGG: {selected_game_name} (ID: {game_data['id']})")
            logger.info(f"Rating: {game_data.get('rating', 'N/A')}/10")
            logger.info(f"Complexity: {game_data.get('complexity', 'N/A')}/5")
        else:
            # No BGG token - use game_name or generate a popular game name
            if game_name:
                selected_game_name = game_name
                logger.info(f"Using provided game name: {selected_game_name}")
                logger.info("Claude will research game information")
            else:
                # Generate a random popular game name for Claude to research
                import random
                popular_games = [
                    "Catan", "Ticket to Ride", "Pandemic", "Wingspan", "Azul",
                    "Splendor", "7 Wonders", "Carcassonne", "Terraforming Mars",
                    "Gloomhaven", "Spirit Island", "Everdell", "Brass", "Concordia"
                ]
                selected_game_name = random.choice(popular_games)
                logger.info(f"Randomly selected game name: {selected_game_name}")
                logger.info("Claude will research game information")
        
        # Step 2: Generate content
        logger.info("=" * 50)
        logger.info("STEP 2: Generating content...")
        logger.info("=" * 50)
        
        if not content_type:
            content_types = content_config.get('types', ['review', 'tutorial', 'strategy'])
            import random
            content_type = random.choice(content_types)
        
        if game_data:
            content = content_gen.generate_content(
                game_data=game_data,
                content_type=content_type,
                min_length=content_config.get('min_length', 250),
                max_length=content_config.get('max_length', 400)
            )
        else:
            content = content_gen.generate_content(
                game_name=selected_game_name,
                content_type=content_type,
                min_length=content_config.get('min_length', 250),
                max_length=content_config.get('max_length', 400)
            )
        
        if not content:
            logger.error("Failed to generate content")
            return False
        
        logger.info(f"Generated {content_type} content ({len(content)} characters)")
        if manual_approve or dry_run:
            print("\n" + "=" * 50)
            print("GENERATED CONTENT:")
            print("=" * 50)
            print(content)
            print("=" * 50 + "\n")
        
        # Step 3: Get image
        logger.info("=" * 50)
        logger.info("STEP 3: Getting image...")
        logger.info("=" * 50)
        
        image_path = None
        
        # Try BGG image first (only if we have game_data)
        if game_data:
            image_url = game_data.get('image_url')
            if image_url:
                image_path = image_handler.download_from_url(image_url)
        
        # Fallback to Unsplash if needed
        if not image_path and image_config.get('fallback_to_unsplash', True):
            unsplash_key = config.get('unsplash', {}).get('access_key')
            if unsplash_key:
                search_name = game_data.get('name') if game_data else selected_game_name
                # More specific boardgame search keywords
                unsplash_url = image_handler.search_unsplash(
                    keywords=f"{search_name}",
                    access_key=unsplash_key
                )
                if unsplash_url:
                    image_path = image_handler.download_from_url(unsplash_url)
        
        if not image_path:
            logger.warning("No image available, proceeding without image")
        else:
            # Validate and optimize
            if not image_handler.validate_image(image_path):
                logger.warning("Image validation failed, attempting to optimize...")
                image_handler.optimize_image(image_path)
            
            logger.info(f"Image ready: {image_path}")
        
        # Manual approval
        if manual_approve and not dry_run:
            response = input("\nApprove and post? (y/n): ")
            if response.lower() != 'y':
                logger.info("Post cancelled by user")
                return False
        
        # Step 4: Post to Facebook
        logger.info("=" * 50)
        logger.info("STEP 4: Posting to Facebook...")
        logger.info("=" * 50)
        
        if not image_path:
            logger.error("Cannot post without image")
            return False
        
        post_url = facebook_poster.post_with_image(
            message=content,
            image_path=image_path
        )
        
        if not post_url:
            logger.error("Failed to post to Facebook")
            return False
        
        # Step 5: Log success
        logger.info("=" * 50)
        logger.info("STEP 5: Logging...")
        logger.info("=" * 50)
        
        posted_logs_path = Path("data/posted_logs.json")
        posted_logs_path.parent.mkdir(parents=True, exist_ok=True)
        
        posted_logs = []
        if posted_logs_path.exists():
            with open(posted_logs_path, 'r', encoding='utf-8') as f:
                posted_logs = json.load(f)
        
        log_entry = {
            'game_name': selected_game_name,
            'content_type': content_type,
            'post_url': post_url,
            'posted_at': datetime.now().isoformat(),
            'dry_run': dry_run
        }
        
        # Add game_id if available from BGG
        if game_data and 'id' in game_data:
            log_entry['game_id'] = game_data['id']
        else:
            log_entry['game_id'] = None
            log_entry['source'] = 'claude_research'
        
        posted_logs.append(log_entry)
        
        with open(posted_logs_path, 'w', encoding='utf-8') as f:
            json.dump(posted_logs, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Successfully logged post: {post_url}")
        logger.info("=" * 50)
        logger.info("BOT EXECUTION COMPLETED SUCCESSFULLY!")
        logger.info("=" * 50)
        
        return True
        
    except Exception as e:
        logger.error(f"Error in bot execution: {e}", exc_info=True)
        return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Boardgame Bot - Auto post to Facebook')
    parser.add_argument('--game-name', type=str, help='Specific game name to post')
    parser.add_argument('--content-type', type=str, choices=['review', 'tutorial', 'strategy'],
                       help='Content type to generate')
    parser.add_argument('--dry-run', action='store_true',
                       help='Test mode - do not actually post to Facebook (overrides config)')
    parser.add_argument('--live', action='store_true',
                       help='Force live mode - actually post to Facebook (overrides config dry_run setting)')
    parser.add_argument('--manual-approve', action='store_true',
                       help='Wait for manual approval before posting')
    
    args = parser.parse_args()
    
    # Validate: cannot use both --live and --dry-run
    if args.live and args.dry_run:
        logger.error("Cannot use both --live and --dry-run flags. Choose one.")
        sys.exit(1)
    
    # Determine dry_run value: --live takes precedence, then --dry-run, then config
    if args.live:
        dry_run = False
        logger.info("LIVE MODE: Will actually post to Facebook")
    elif args.dry_run:
        dry_run = True
        logger.info("DRY RUN MODE: Will NOT post to Facebook")
    else:
        dry_run = None  # Will use config value
    
    success = run_bot(
        game_name=args.game_name,
        content_type=args.content_type,
        dry_run=dry_run,
        manual_approve=args.manual_approve
    )
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

