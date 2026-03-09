# Tài liệu hướng dẫn xây dựng Bot đăng bài Boardgame tự động

## 📋 Tổng quan dự án

### Mục tiêu

Xây dựng bot Python tự động đăng bài về boardgame lên Facebook với khả năng:

- Tự động research thông tin boardgame từ nguồn trực tuyến
- Tạo content phân tích/hướng dẫn bằng AI
- Tìm và xử lý hình ảnh minh họa
- Đăng bài tự động theo lịch

### Kiến trúc hệ thống

```
┌─────────────────────────────────────────────────────────────┐
│                      BOT CONTROLLER                         │
│                    (main.py/scheduler)                      │
└────────────┬────────────────────────────────────────────────┘
             │
             ├──► [1] RESEARCH MODULE
             │        └─► BoardGameGeek API/Scraper
             │        └─► Game Selection Logic
             │
             ├──► [2] AI CONTENT MODULE
             │        └─► Claude/GPT API
             │        └─► Content Templates
             │        └─► Vietnamese Language Processing
             │
             ├──► [3] IMAGE MODULE
             │        └─► Image Finder (BGG, Unsplash)
             │        └─► Image Downloader
             │        └─► Image Validator
             │
             └──► [4] FACEBOOK MODULE
                      └─► Facebook Graph API (Page)
                      └─► Post Scheduler
                      └─► Error Handler & Retry Logic
```

---

## 🎯 Các bước thực thi chi tiết

### BƯỚC 1: Setup dự án ban đầu

**Mục tiêu**: Tạo cấu trúc project và cài đặt môi trường

**Công việc cần làm**:

1. Tạo thư mục dự án với cấu trúc rõ ràng
2. Setup virtual environment Python
3. Tạo file cấu hình (.env, config.yaml)
4. Cài đặt các thư viện cần thiết

**Cấu trúc thư mục đề xuất**:

```
boardgame-bot/
├── src/
│   ├── research/       # Module research boardgame
│   ├── content/        # Module AI content generation
│   ├── images/         # Module xử lý hình ảnh
│   ├── social/         # Module đăng Facebook
│   └── utils/          # Utilities (logger, config loader...)
├── data/
│   ├── boardgames.json     # Database game đã research
│   └── posted_logs.json    # Lịch sử đã đăng
├── images/             # Thư mục lưu ảnh tải về
├── logs/               # Log files
├── config/
│   ├── config.yaml     # Config chính
│   └── .env           # API keys (không commit git)
├── main.py            # Script chính
├── scheduler.py       # Auto scheduling
└── requirements.txt   # Dependencies
```

**Dependencies cần cài**:

- `requests` - HTTP requests
- `anthropic` hoặc `openai` - AI API
- `facebook-sdk` - Facebook API
- `beautifulsoup4` - Web scraping
- `python-dotenv` - Load environment variables
- `pyyaml` - Config file
- `schedule` hoặc `apscheduler` - Scheduling
- `Pillow` - Image processing

**Prompt cho Cursor**:

```
Tạo project Python với cấu trúc như trên. Setup virtual environment,
tạo requirements.txt với các thư viện đã liệt kê, tạo file .env.example
và config.yaml.example với các fields cần thiết cho API keys và cấu hình.
```

---

### BƯỚC 2: Xây dựng Research Module

**Mục tiêu**: Tìm kiếm và lấy thông tin boardgame từ BoardGameGeek

**Luồng hoạt động**:

```
Input: Tên game hoặc random selection
    ↓
Bước 1: Search game trên BGG API
    ↓
Bước 2: Lấy game ID
    ↓
Bước 3: Fetch chi tiết game (rating, mechanics, description, image URL...)
    ↓
Bước 4: Parse và lưu data vào JSON
    ↓
Output: Dictionary chứa thông tin game
```

**Data cần lấy từ BoardGameGeek**:

- Tên game (tiếng Anh và alternate names)
- Năm phát hành
- Số người chơi (min-max)
- Thời gian chơi
- Độ tuổi khuyến nghị
- Rating trung bình
- Độ phức tạp (complexity/weight)
- Mechanics (cơ chế chơi)
- Categories (thể loại)
- Description (mô tả)
- Image URL
- Number of ratings

**API Endpoints quan trọng**:

- Search: `https://boardgamegeek.com/xmlapi2/search?query={game_name}&type=boardgame`
- Details: `https://boardgamegeek.com/xmlapi2/thing?id={game_id}&stats=1`

**Logic lựa chọn game**:

- Random từ top 100-500 games (tránh quá phổ biến)
- Filter theo rating (>= 7.0)
- Filter theo complexity (không quá phức tạp)
- Kiểm tra đã đăng chưa (tránh trùng)

**Prompt cho Cursor**:

```
Tạo module research với class BGGScraper. Module này cần có các methods:
- search_game(name): tìm game và trả về ID
- get_game_details(id): lấy full details từ BGG API (XML response)
- get_random_game(): chọn random 1 game từ top list theo filter
- save_to_database(): lưu game data vào JSON file

API response là XML, cần parse đúng các fields như rating, mechanics, categories.
Xử lý error và retry logic khi API timeout.
```

---

### BƯỚC 3: Xây dựng AI Content Generation Module

**Mục tiêu**: Tạo nội dung bài viết phân tích/hướng dẫn bằng AI

**Luồng hoạt động**:

```
Input: Game data từ Research Module
    ↓
Bước 1: Chọn content type (review/tutorial/strategy)
    ↓
Bước 2: Tạo prompt cho AI với game data
    ↓
Bước 3: Call AI API (Claude/GPT)
    ↓
Bước 4: Parse và format output
    ↓
Bước 5: Validate content (độ dài, tone, format)
    ↓
Output: Content bài viết hoàn chỉnh
```

**Content types**:

1. **Review/Đánh giá**: Phân tích điểm mạnh, điểm yếu, phù hợp với ai
2. **Tutorial/Hướng dẫn**: Cách chơi cơ bản, setup, quy tắc quan trọng
3. **Strategy Guide**: Chiến thuật, tips & tricks, common mistakes

**Cấu trúc content đề xuất**:

```
[Hook - 1-2 câu thu hút]

[Giới thiệu game - 2-3 câu]

[Phần chính - phụ thuộc content type]
- Review: Mechanics → Gameplay → Điểm mạnh/yếu → Phù hợp ai
- Tutorial: Setup → Mục tiêu → Luật cơ bản → Flow 1 turn
- Strategy: Mechanics key → Chiến thuật cơ bản → Tips nâng cao

[Kết luận - recommendation]

#boardgame #boardgamesvietnam #[tên_game]
```

**System prompt template**:

```
Bạn là chuyên gia boardgame Việt Nam. Nhiệm vụ: viết {content_type}
về boardgame "{game_name}" bằng tiếng Việt.

Game info:
- Rating: {rating}
- Players: {players}
- Playtime: {playtime}
- Mechanics: {mechanics}
- Description: {description}

Yêu cầu:
- Độ dài: 250-350 từ
- Tone: thân thiện, dễ hiểu, nhiệt huyết
- Format: đoạn văn, không dùng bullet points
- Thêm hashtags phù hợp ở cuối
- Tránh spoiler nếu là strategy guide
```

**Prompt cho Cursor**:

```
Tạo module content_generator với class AIContentGenerator.
Module cần:
- Method generate_content(game_data, content_type): call Claude API
- Template system cho các loại content khác nhau
- Validation: check độ dài, format, tone
- Retry logic nếu output không đạt yêu cầu
- Save generated content vào cache để review trước khi post

Sử dụng Anthropic Claude API với model claude-sonnet-4-20250514.
Content phải bằng tiếng Việt.
```

---

### BƯỚC 4: Xây dựng Image Handler Module

**Mục tiêu**: Tìm, tải và xử lý hình ảnh minh họa

**Luồng hoạt động**:

```
Input: Game data (có image_url từ BGG)
    ↓
Bước 1: Lấy image URL từ BGG
    ↓
Bước 2: Download image
    ↓
Bước 3: Validate (size, format, dimensions)
    ↓
Bước 4: Resize/optimize nếu cần
    ↓
Bước 5: Save vào thư mục images/
    ↓
Output: Local image path
```

**Nguồn hình ảnh (priority order)**:

1. **BoardGameGeek** (primary) - Official game images
2. **Unsplash API** (fallback) - Search với keywords từ game name
3. **Placeholder** (last resort) - Ảnh generic boardgame

**Image requirements**:

- Format: JPG hoặc PNG
- Size: Tối đa 5MB
- Min dimensions: 720x720px
- Aspect ratio: Ưu tiên 1:1 hoặc 4:3

**Error handling**:

- URL invalid/broken
- Download timeout
- File corrupted
- Size quá lớn

**Prompt cho Cursor**:

```
Tạo module image_handler với class ImageHandler:
- Method download_from_url(url, save_path): download và validate
- Method search_unsplash(keywords): fallback image search
- Method validate_image(path): check size, format, dimensions
- Method optimize_image(path): resize/compress nếu cần

Xử lý các edge cases: timeout, invalid format, corrupted file.
Log tất cả actions để debug.
```

---

### BƯỚC 5: Xây dựng Facebook Posting Module

**Mục tiêu**: Đăng bài lên Facebook Page tự động

**Lựa chọn phương pháp**:

#### Option A: Facebook Graph API (Khuyên dùng)

**Pros**: Chính thống, stable, không vi phạm ToS
**Cons**: Chỉ post lên Page (không post lên profile cá nhân)

**Workflow**:

```
Bước 1: Tạo Facebook App tại developers.facebook.com
Bước 2: Add Facebook Page và get permissions
Bước 3: Generate Page Access Token (long-lived)
Bước 4: Test với Graph API Explorer
Bước 5: Implement posting logic
```

**API Endpoint**:

```
POST https://graph.facebook.com/v24.0/{page-id}/photos
Parameters:
- message: Content text
- url: Image URL hoặc
- Upload binary image
- access_token: Page access token
```

#### Option B: Browser Automation (Selenium/Playwright)

**Pros**: Post được lên profile cá nhân
**Cons**: Vi phạm ToS, dễ bị khóa account, unstable

**LƯU Ý**: Facebook cấm automation trên profile cá nhân. Nếu bạn muốn post lên profile, hãy cân nhắc rủi ro.

**Luồng hoạt động (Graph API)**:

```
Input: Content text + Image path
    ↓
Bước 1: Upload image to Facebook servers
    ↓
Bước 2: Tạo post với image_id và caption
    ↓
Bước 3: Get post ID từ response
    ↓
Bước 4: Log thành công vào database
    ↓
Output: Post URL
```

**Error handling & retry**:

- Access token expired → Refresh token
- Rate limit → Wait and retry
- Network error → Retry with exponential backoff
- Invalid image → Use fallback image

**Prompt cho Cursor**:

```
Tạo module facebook_poster với class FacebookPoster:
- Method post_with_image(message, image_path, page_id, access_token)
- Method upload_photo(image_path): upload và return photo_id
- Method create_post(photo_id, message): tạo post
- Retry logic với exponential backoff (max 3 retries)
- Log mọi action và error vào file

Sử dụng Facebook Graph API v24.0.
Xử lý các error codes phổ biến của Facebook.
```

---

### BƯỚC 6: Xây dựng Main Controller & Scheduler

**Mục tiêu**: Orchestrate toàn bộ workflow và tự động hóa

**Main workflow**:

```
main.py - Single execution:
    ↓
1. Load config từ files
    ↓
2. Initialize tất cả modules
    ↓
3. Research: Get random game data
    ↓
4. Content: Generate post content
    ↓
5. Image: Download và process image
    ↓
6. Review: (Optional) Manual approval
    ↓
7. Facebook: Post to page
    ↓
8. Log: Save to posted_logs.json
    ↓
Done
```

**Scheduler workflow**:

```
scheduler.py - Automated execution:
    ↓
1. Load schedule config (time, frequency)
    ↓
2. Setup scheduler (daily at 19:00)
    ↓
3. Run main workflow theo schedule
    ↓
4. Handle errors và retry
    ↓
5. Send notification (optional - email/telegram)
    ↓
Loop forever
```

**Config cần thiết (config.yaml)**:

```yaml
schedule:
  enabled: true
  post_time: "19:00"
  timezone: "Asia/Ho_Chi_Minh"
  frequency: "daily" # daily/weekly/custom

content:
  types: ["review", "tutorial", "strategy"]
  language: "vi"
  min_length: 250
  max_length: 400

facebook:
  page_id: "YOUR_PAGE_ID"
  dry_run: false # true = test mode, không post thật

research:
  min_rating: 7.0
  max_complexity: 4.0
  avoid_recent_days: 30 # Không lặp game trong 30 ngày
```

**Safety features**:

- **Dry run mode**: Test mà không post thật
- **Manual approval**: Review content trước khi post
- **Duplicate check**: Tránh post trùng game
- **Error recovery**: Retry failed posts
- **Logging**: Track mọi action để debug

**Prompt cho Cursor**:

```
Tạo 2 files:

1. main.py - Orchestrator chính:
   - Function run_bot(): execute toàn bộ workflow
   - Load config từ yaml và .env
   - Initialize tất cả modules
   - Execute từng bước với error handling
   - Log chi tiết từng bước
   - Return status (success/failure)

2. scheduler.py - Automation:
   - Setup APScheduler với timezone
   - Schedule job theo config
   - Wrap main.py trong scheduler
   - Error notification system
   - Graceful shutdown

Thêm CLI arguments: --dry-run, --manual-approve, --game-name
```

---

### BƯỚC 7: Testing & Quality Assurance

**Mục tiêu**: Đảm bảo bot hoạt động ổn định và chính xác

**Test checklist**:

1. **Unit Tests**:

   - [ ] BGG API search và fetch
   - [ ] AI content generation
   - [ ] Image download và validation
   - [ ] Facebook API posting

2. **Integration Tests**:

   - [ ] End-to-end workflow
   - [ ] Error handling ở mỗi bước
   - [ ] Retry logic
   - [ ] Config loading

3. **Manual Tests**:

   - [ ] Dry run mode: Không post thật
   - [ ] Review generated content quality
   - [ ] Check image quality
   - [ ] Verify Facebook post format

4. **Edge Cases**:
   - [ ] BGG API timeout
   - [ ] AI generates inappropriate content
   - [ ] Image không tải được
   - [ ] Facebook API rate limit
   - [ ] Trùng game đã post

**Prompt cho Cursor**:

```
Tạo thư mục tests/ với test files:
- test_research.py: Test BGG scraper
- test_content.py: Test AI generation
- test_images.py: Test image handler
- test_facebook.py: Test posting (mock)
- test_integration.py: Test full workflow

Sử dụng pytest framework.
Mock external APIs để test nhanh.
```

---

### BƯỚC 8: Deployment & Monitoring

**Mục tiêu**: Deploy bot và theo dõi hoạt động

**Deployment options**:

1. **Local machine** (đơn giản nhất):

   - Chạy trên máy tính cá nhân
   - Cần bật máy 24/7
   - Dùng Task Scheduler (Windows) hoặc cron (Linux)

2. **VPS/Cloud server** (khuyên dùng):

   - Rent VPS (DigitalOcean, Linode, AWS EC2)
   - Setup Python environment
   - Run bot as background service
   - Setup auto-restart nếu crash

3. **Docker container** (professional):
   - Containerize bot
   - Easy deploy anywhere
   - Easy version control

**Monitoring cần có**:

- **Logging**: Save logs vào file, rotate daily
- **Health check**: Ping bot định kỳ
- **Error alerts**: Email/Telegram khi có lỗi
- **Success metrics**: Track posts đăng thành công
- **Performance**: Monitor API response times

**Prompt cho Cursor**:

```
Tạo production setup:
1. Dockerfile để containerize bot
2. systemd service file cho Linux
3. Monitoring script check_health.py
4. Setup script setup.sh tự động cài đặt dependencies
5. README.md với hướng dẫn deployment chi tiết
```

---

## 🔐 Setup Facebook App & Access Token

**Bước chi tiết**:

### 1. Tạo Facebook App

1. Đi tới https://developers.facebook.com/
2. "My Apps" → "Create App"
3. Chọn app type: "Business"
4. Điền thông tin app
5. Add product: "Facebook Login"

### 2. Setup Facebook Page

1. Có sẵn 1 Facebook Page (tạo nếu chưa có)
2. Trong App Settings, add Page

### 3. Get Access Token

1. Tools → Graph API Explorer
2. Select your app
3. Add permissions: `pages_read_engagement`, `pages_manage_posts`
4. Generate token
5. Extend token thành long-lived (60 days)

### 4. Get Page ID

1. Vào Page của bạn
2. Settings → Advanced
3. Copy Page ID

**LƯU Ý BẢO MẬT**:

- Không commit access token vào Git
- Lưu trong file .env
- Đặt .env vào .gitignore
- Refresh token khi hết hạn

---

## 📊 Workflow tổng thể (Summary)

```
┌─────────────────────────────────────────────────────┐
│  SCHEDULER (19:00 hàng ngày)                        │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│  STEP 1: Research Game                              │
│  - Query BGG API                                    │
│  - Get random game (filtered)                       │
│  - Check not posted recently                        │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│  STEP 2: Generate Content                           │
│  - Select content type                              │
│  - Call Claude API                                  │
│  - Validate output                                  │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│  STEP 3: Get Image                                  │
│  - Download from BGG                                │
│  - Fallback to Unsplash if needed                   │
│  - Validate and optimize                            │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│  STEP 4: Post to Facebook                           │
│  - Upload image                                     │
│  - Create post with content                         │
│  - Handle errors and retry                          │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│  STEP 5: Log & Clean up                             │
│  - Save to posted_logs.json                         │
│  - Archive generated content                        │
│  - Clean up temp files                              │
└─────────────────────────────────────────────────────┘
```

---

## 🎯 Prompt tổng hợp cho Cursor

**Prompt chính để tạo toàn bộ dự án**:

```
Xây dựng bot Python tự động đăng bài boardgame lên Facebook Page với workflow sau:

1. RESEARCH: Lấy thông tin boardgame từ BoardGameGeek API (XML response)
   - Search và get game details
   - Filter theo rating >= 7.0, complexity <= 4.0
   - Lưu vào data/boardgames.json

2. CONTENT: Generate nội dung bằng Claude AI
   - 3 loại content: review, tutorial, strategy_guide
   - Tiếng Việt, 250-350 từ
   - Format đoạn văn với hashtags

3. IMAGES: Download hình ảnh game
   - Primary: BGG image URL
   - Fallback: Unsplash API
   - Validate size, format, optimize

4. FACEBOOK: Post lên Page qua Graph API
   - Upload image + caption
   - Error handling và retry
   - Log thành công/thất bại

5. SCHEDULER: Tự động chạy hàng ngày 19:00
   - APScheduler với timezone Asia/Ho_Chi_Minh
   - Dry-run mode để test
   - Manual approval option

Cấu trúc project:
- src/ chứa 4 modules: research, content, images, social
- config/ chứa .env và config.yaml
- main.py: orchestrator
- scheduler.py: automation

Dependencies: requests, anthropic, facebook-sdk, beautifulsoup4,
python-dotenv, pyyaml, apscheduler, Pillow

Yêu cầu:
- Error handling đầy đủ mọi bước
- Retry logic với exponential backoff
- Logging chi tiết vào files
- CLI arguments: --dry-run, --game-name
- README.md với setup instructions
```

---

## 📚 Resources & Documentation

**APIs cần sử dụng**:

- BoardGameGeek XML API: https://boardgamegeek.com/wiki/page/BGG_XML_API2
- Claude API: https://docs.anthropic.com/
- Facebook Graph API: https://developers.facebook.com/docs/graph-api
- Unsplash API: https://unsplash.com/documentation

**Tutorials hữu ích**:

- Facebook Graph API for Pages: https://developers.facebook.com/docs/pages/
- Python APScheduler: https://apscheduler.readthedocs.io/
- Python dotenv: https://pypi.org/project/python-dotenv/

**Tips để tương tác với Cursor**:

1. Show tài liệu này cho Cursor
2. Yêu cầu tạo từng module riêng lẻ
3. Test từng module trước khi integrate
4. Sử dụng `@docs` để reference documentation
5. Ask Cursor explain code nếu không hiểu
6. Request unit tests cho critical functions

---

## ⚠️ Lưu ý quan trọng

1. **Facebook Terms of Service**:

   - Chỉ post lên Page (không post profile)
   - Tuân thủ rate limits
   - Không spam content

2. **API Rate Limits**:

   - BGG: ~1-2 requests/second
   - Claude: Theo plan của bạn
   - Facebook: 200 calls/hour/user

3. **Content Quality**:

   - Review AI output trước khi post
   - Tránh thông tin sai lệch
   - Respect copyright (không copy nguyên văn review người khác)

4. **Security**:

   - Không commit API keys
   - Rotate tokens định kỳ
   - Monitor unusual activities

5. **Costs**:
   - Claude API: ~$3-15/1000 requests
   - VPS: ~$5-10/month
   - Facebook API: Free (có limits)
