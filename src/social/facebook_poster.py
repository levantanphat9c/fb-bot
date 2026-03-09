"""
Facebook Posting Module using Graph API
"""
import os
import time
import requests
from typing import Optional

from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class FacebookPoster:
    """Post content and images to Facebook Page using Graph API"""
    
    def __init__(
        self,
        page_id: str,
        access_token: str,
        api_version: str = "v24.0",
        dry_run: bool = False
    ):
        """
        Initialize Facebook Poster
        
        Args:
            page_id: Facebook Page ID
            access_token: Page Access Token (long-lived)
            api_version: Graph API version (default: v24.0)
            dry_run: If True, simulate posting without actually posting
        """
        self.page_id = page_id
        self.access_token = access_token
        self.api_version = api_version
        self.dry_run = dry_run
        self.base_url = f"https://graph.facebook.com/{api_version}"
        
        if not page_id:
            logger.warning("Facebook Page ID not provided")
        if not access_token:
            logger.warning("Facebook Access Token not provided")
    
    def post_with_image(
        self,
        message: str,
        image_path: str,
        published: bool = True
    ) -> Optional[str]:
        """
        Post message with image to Facebook Page
        
        Theo Facebook Graph API docs:
        - Có 2 cách: upload photo trực tiếp hoặc post với URL
        - Method này sử dụng cách upload photo trực tiếp (recommended)
        
        Args:
            message: Post content/caption
            image_path: Local path to image file
            published: If True, post is published immediately
        
        Returns:
            Post URL if successful, None otherwise
        """
        if self.dry_run:
            logger.info("DRY RUN: Would post to Facebook")
            logger.info(f"Message: {message[:100]}...")
            logger.info(f"Image: {image_path}")
            return "https://facebook.com/dry-run-post"
        
        if not self.page_id or not self.access_token:
            logger.error("Missing page_id or access_token")
            logger.error(f"  Page ID: {self.page_id if self.page_id else 'NOT SET'}")
            logger.error(f"  Access Token: {'SET' if self.access_token else 'NOT SET'} (masked for security)")
            return None
        
        # Log debug info (masked token)
        masked_token = f"{self.access_token[:10]}...{self.access_token[-5:]}" if len(self.access_token) > 15 else "***"
        logger.info(f"Posting to Facebook Page ID: {self.page_id}")
        logger.info(f"Access Token: {masked_token}")
        logger.info(f"API Version: {self.api_version}")
        
        # Verify page access before posting
        if not self.verify_page_access():
            logger.error("Cannot access Facebook Page. Please check your configuration.")
            return None
        
        try:
            # Step 1: Upload photo to Facebook
            photo_id = self._upload_photo(image_path, message)
            if not photo_id:
                logger.error("Failed to upload photo")
                return None
            
            logger.info(f"Photo uploaded successfully: {photo_id}")
            
            # Step 2: Create post with the uploaded photo
            # Note: Khi upload photo với caption, Facebook tự động tạo post
            # Nhưng để có post_id rõ ràng, ta có thể tạo post riêng
            
            # Option A: Photo đã có caption, không cần tạo post riêng
            # Lấy post_id từ photo response
            post_id = photo_id  # Photo ID cũng là post ID trong trường hợp này
            
            # Option B: Nếu muốn tạo post riêng với photo đã upload
            # post_id = self._create_post_with_photo(photo_id, message)
            
            # Build post URL
            post_url = f"https://facebook.com/{post_id}"
            
            logger.info(f"Post created successfully: {post_url}")
            return post_url
            
        except Exception as e:
            logger.error(f"Error posting to Facebook: {e}", exc_info=True)
            return None
    
    def _upload_photo(
        self,
        image_path: str,
        caption: str,
        max_retries: int = 3
    ) -> Optional[str]:
        """
        Upload photo to Facebook Page
        
        Endpoint: POST /{page-id}/photos
        Docs: https://developers.facebook.com/docs/graph-api/reference/page/photos/
        
        Args:
            image_path: Local path to image file
            caption: Photo caption (will appear as post message)
            max_retries: Maximum number of retry attempts
        
        Returns:
            Photo ID if successful, None otherwise
        """
        if not os.path.exists(image_path):
            logger.error(f"Image file not found: {image_path}")
            return None
        
        url = f"{self.base_url}/{self.page_id}/photos"
        
        # Prepare multipart form data
        # Facebook Graph API yêu cầu:
        # - source: binary file data
        # - caption: text message
        # - published: true/false
        # - access_token: page access token
        
        # Detect MIME type from file extension
        mime_type = self._get_mime_type(image_path)
        
        for attempt in range(max_retries):
            try:
                with open(image_path, 'rb') as image_file:
                    files = {
                        'source': (os.path.basename(image_path), image_file, mime_type)
                    }
                    data = {
                        'caption': caption,
                        'published': 'true',  # Publish immediately
                        'access_token': self.access_token
                    }
                    
                    logger.info(f"Uploading photo to Facebook (attempt {attempt + 1}/{max_retries})...")
                    response = requests.post(
                        url,
                        files=files,
                        data=data,
                        timeout=60  # Upload có thể mất thời gian
                    )
                    
                    response.raise_for_status()
                    result = response.json()
                    
                    # Response format: {"id": "photo_id"}
                    if 'id' in result:
                        photo_id = result['id']
                        logger.info(f"Photo uploaded: {photo_id}")
                        return photo_id
                    else:
                        logger.error(f"Unexpected response format: {result}")
                        return None
                        
            except requests.exceptions.HTTPError as e:
                error_data = {}
                error_code = None
                error_message = str(e)
                error_type = None
                error_subcode = None
                
                try:
                    error_data = e.response.json()
                    error_info = error_data.get('error', {})
                    error_code = error_info.get('code', '')
                    error_message = error_info.get('message', str(e))
                    error_type = error_info.get('type', '')
                    error_subcode = error_info.get('error_subcode', '')
                    
                    # Log full error details for debugging
                    logger.error("=" * 50)
                    logger.error("Facebook API Error Details:")
                    logger.error(f"  Error Code: {error_code}")
                    logger.error(f"  Error Type: {error_type}")
                    logger.error(f"  Error Message: {error_message}")
                    if error_subcode:
                        logger.error(f"  Error Subcode: {error_subcode}")
                    logger.error(f"  Full Response: {error_data}")
                    logger.error("=" * 50)
                    
                except Exception as parse_error:
                    logger.error(f"Failed to parse error response: {parse_error}")
                    logger.error(f"Raw response: {e.response.text if hasattr(e, 'response') else 'N/A'}")
                
                # Handle specific Facebook error codes
                if error_code == 190:  # Invalid OAuth access token
                    logger.error("❌ Access token expired or invalid")
                    logger.error("   Solution: Generate a new Page Access Token")
                    logger.error("   Visit: https://developers.facebook.com/tools/explorer/")
                    return None
                elif error_code == 200:  # Permissions error or invalid request
                    logger.error("❌ Permissions error or invalid request")
                    logger.error(f"   Error details: {error_message}")
                    logger.error("   Required permissions:")
                    logger.error("     - pages_manage_posts")
                    logger.error("     - pages_read_engagement (optional)")
                    logger.error("   Solution:")
                    logger.error("     1. Go to https://developers.facebook.com/apps/")
                    logger.error("     2. Select your app")
                    logger.error("     3. Go to 'Tools' > 'Graph API Explorer'")
                    logger.error("     4. Select your Page and generate token with required permissions")
                    logger.error("     5. Make sure you're using a PAGE ACCESS TOKEN, not User Access Token")
                    return None
                elif error_code == 368:  # Temporary blocked
                    wait_time = (attempt + 1) * 60  # Wait longer each retry
                    logger.warning(f"⚠️ Temporarily blocked. Waiting {wait_time}s before retry...")
                    if attempt < max_retries - 1:
                        time.sleep(wait_time)
                        continue
                elif error_code == 4:  # Application request limit reached
                    wait_time = (attempt + 1) * 60
                    logger.warning(f"⚠️ Rate limit reached. Waiting {wait_time}s...")
                    if attempt < max_retries - 1:
                        time.sleep(wait_time)
                        continue
                elif error_code == 100:  # Invalid parameter
                    logger.error(f"❌ Invalid parameter: {error_message}")
                    logger.error("   Check: page_id, image file format, file size")
                    return None
                elif error_code == 10:  # Permission denied
                    logger.error("❌ Permission denied")
                    logger.error(f"   Details: {error_message}")
                    logger.error("   Make sure your Page Access Token has 'pages_manage_posts' permission")
                    return None
                
                # Generic error handling
                logger.error(f"❌ HTTP error uploading photo (Code: {error_code}): {error_message}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.info(f"Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error("Max retries reached. Giving up.")
                    return None
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Network error uploading photo: {e}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    return None
                    
            except Exception as e:
                logger.error(f"Unexpected error uploading photo: {e}", exc_info=True)
                return None
        
        return None
    
    def _create_post_with_photo(
        self,
        photo_id: str,
        message: str
    ) -> Optional[str]:
        """
        Create a post referencing an uploaded photo
        
        Endpoint: POST /{page-id}/feed
        Docs: https://developers.facebook.com/docs/graph-api/reference/page/feed/
        
        Note: Thường không cần method này vì upload photo với caption đã tạo post
        
        Args:
            photo_id: ID of uploaded photo
            message: Post message
        
        Returns:
            Post ID if successful, None otherwise
        """
        url = f"{self.base_url}/{self.page_id}/feed"
        
        data = {
            'message': message,
            'attached_media': f'[{{"media_fbid":"{photo_id}"}}]',
            'access_token': self.access_token
        }
        
        try:
            response = requests.post(url, data=data, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            if 'id' in result:
                return result['id']
            else:
                logger.error(f"Unexpected response: {result}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating post: {e}")
            return None
    
    def post_text_only(self, message: str) -> Optional[str]:
        """
        Post text-only message to Facebook Page
        
        Endpoint: POST /{page-id}/feed
        
        Args:
            message: Post content
        
        Returns:
            Post URL if successful, None otherwise
        """
        if self.dry_run:
            logger.info("DRY RUN: Would post text to Facebook")
            logger.info(f"Message: {message[:100]}...")
            return "https://facebook.com/dry-run-post"
        
        if not self.page_id or not self.access_token:
            logger.error("Missing page_id or access_token")
            return None
        
        url = f"{self.base_url}/{self.page_id}/feed"
        
        data = {
            'message': message,
            'access_token': self.access_token
        }
        
        try:
            response = requests.post(url, data=data, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            if 'id' in result:
                post_id = result['id']
                post_url = f"https://facebook.com/{post_id}"
                logger.info(f"Post created: {post_url}")
                return post_url
            else:
                logger.error(f"Unexpected response: {result}")
                return None
                
        except Exception as e:
            logger.error(f"Error posting text: {e}")
            return None
    
    def verify_token(self) -> bool:
        """
        Verify that access token is valid and has required permissions
        
        Returns:
            True if token is valid, False otherwise
        """
        if not self.access_token:
            logger.error("Access token not provided")
            return False
        
        # First, verify token with /me endpoint
        url = f"{self.base_url}/me"
        params = {
            'access_token': self.access_token,
            'fields': 'id,name'
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            if 'id' in result:
                logger.info(f"✓ Token verified for: {result.get('name', 'Unknown')} (ID: {result.get('id')})")
                
                # Check permissions
                self._check_permissions()
                return True
            else:
                logger.error("Token verification failed - no ID in response")
                return False
                
        except requests.exceptions.HTTPError as e:
            error_data = {}
            try:
                error_data = e.response.json()
                error_info = error_data.get('error', {})
                error_code = error_info.get('code', '')
                error_message = error_info.get('message', '')
                logger.error(f"Token verification failed: {error_message} (Code: {error_code})")
            except:
                logger.error(f"Token verification failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Error verifying token: {e}")
            return False
    
    def _check_permissions(self) -> None:
        """
        Check if access token has required permissions for posting
        """
        if not self.access_token:
            return
        
        url = f"{self.base_url}/me/permissions"
        params = {
            'access_token': self.access_token
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            permissions = result.get('data', [])
            permission_names = [p.get('permission') for p in permissions if p.get('status') == 'granted']
            
            logger.info(f"Granted permissions: {', '.join(permission_names) if permission_names else 'None'}")
            
            required_permissions = ['pages_manage_posts', 'pages_read_engagement']
            missing_permissions = [p for p in required_permissions if p not in permission_names]
            
            if missing_permissions:
                logger.warning(f"⚠️ Missing permissions: {', '.join(missing_permissions)}")
                logger.warning("   These permissions are required to post to Facebook Page")
            else:
                logger.info("✓ All required permissions are granted")
                
        except Exception as e:
            logger.warning(f"Could not check permissions: {e}")
    
    def verify_page_access(self) -> bool:
        """
        Verify that access token can access the specified page
        
        Returns:
            True if page is accessible, False otherwise
        """
        if not self.page_id or not self.access_token:
            logger.error("Missing page_id or access_token")
            return False
        
        url = f"{self.base_url}/{self.page_id}"
        params = {
            'access_token': self.access_token,
            'fields': 'id,name,access_token'
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            if 'id' in result:
                page_name = result.get('name', 'Unknown')
                logger.info(f"✓ Page accessible: {page_name} (ID: {result.get('id')})")
                return True
            else:
                logger.error("Page verification failed - no ID in response")
                return False
                
        except requests.exceptions.HTTPError as e:
            error_data = {}
            try:
                error_data = e.response.json()
                error_info = error_data.get('error', {})
                error_code = error_info.get('code', '')
                error_message = error_info.get('message', '')
                logger.error(f"❌ Cannot access page: {error_message} (Code: {error_code})")
                logger.error(f"   Page ID: {self.page_id}")
                logger.error("   Make sure:")
                logger.error("     1. Page ID is correct")
                logger.error("     2. Access token has access to this page")
                logger.error("     3. You're using a PAGE ACCESS TOKEN, not User Access Token")
            except:
                logger.error(f"Page verification failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Error verifying page access: {e}")
            return False
    
    def _get_mime_type(self, image_path: str) -> str:
        """
        Get MIME type from image file extension
        
        Args:
            image_path: Path to image file
        
        Returns:
            MIME type string (default: image/jpeg)
        """
        ext = os.path.splitext(image_path)[1].lower()
        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp'
        }
        return mime_types.get(ext, 'image/jpeg')

