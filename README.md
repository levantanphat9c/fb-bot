# Boardgame Bot - Tự động đăng bài Boardgame lên Facebook

Bot Python tự động research, tạo content và đăng bài về boardgame lên Facebook Page.

## 📋 Tính năng

- 🔍 **Research tự động**: Lấy thông tin boardgame từ BoardGameGeek API
- ✍️ **Tạo content bằng AI**: Sử dụng Claude AI để tạo nội dung đánh giá/hướng dẫn bằng tiếng Việt
- 🖼️ **Xử lý hình ảnh**: Tải và tối ưu hình ảnh từ BGG hoặc Unsplash
- 📱 **Đăng bài tự động**: Đăng lên Facebook Page qua Graph API
- ⏰ **Lên lịch tự động**: Chạy theo lịch định kỳ với APScheduler

## 🚀 Cài đặt

### 1. Clone repository và tạo virtual environment

```bash
cd fb-bot
python3 -m venv venv
source venv/bin/activate  # Trên Windows: venv\Scripts\activate
```

### 2. Cài đặt dependencies

```bash
pip install -r requirements.txt
```

### 3. Cấu hình

#### Tạo file `.env`:

```bash
cp env.example .env
```

Chỉnh sửa `.env` và điền các thông tin:

```env
FACEBOOK_PAGE_ID=your_page_id_here
FACEBOOK_ACCESS_TOKEN=your_long_lived_access_token_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
UNSPLASH_ACCESS_KEY=your_unsplash_access_key_here  # Optional
BGG_API_TOKEN=your_bgg_api_token_here  # Required - See setup below
```

#### Tạo file `config/config.yaml`:

```bashj
cp config/config.yaml.example config/config.yaml
```

Chỉnh sửa `config/config.yaml` theo nhu cầu (thời gian đăng, loại content, v.v.)

### 4. Setup BoardGameGeek API Token

**Bắt buộc**: BGG API hiện yêu cầu authentication cho tất cả requests.

1. Truy cập https://boardgamegeek.com/applications
2. Đăng ký ứng dụng mới (chọn loại: thương mại hoặc phi thương mại)
3. Chờ phê duyệt (có thể mất 1 tuần hoặc hơn)
4. Sau khi được phê duyệt, tạo token bằng cách click "Tokens" bên cạnh ứng dụng
5. Copy token và thêm vào file `.env` như `BGG_API_TOKEN=your_token_here`

**Lưu ý**:

- Không sử dụng API của BGG để train AI/LLM models (bị nghiêm cấm)
- Tuân thủ rate limits: ~1-2 requests/second

### 5. Setup Facebook App & Access Token

Xem hướng dẫn chi tiết trong file `setup-project.md` phần "Setup Facebook App & Access Token".

Tóm tắt:

1. Tạo Facebook App tại https://developers.facebook.com/
2. Add Facebook Page vào app
3. Get Page Access Token (long-lived)
4. Copy Page ID từ Page Settings

## 📖 Sử dụng

### Chạy một lần (manual)

```bash
python main.py
```

### Chạy với options

```bash
# Test mode (không post thật)
python main.py --dry-run

# Chọn game cụ thể
python main.py --game-name "Catan"

# Chọn loại content
python main.py --content-type review

# Manual approval trước khi post
python main.py --manual-approve
```

### Chạy scheduler (tự động)

```bash
python scheduler.py
```

Scheduler sẽ chạy bot theo lịch đã cấu hình trong `config.yaml` (mặc định: 19:00 hàng ngày).

## 📁 Cấu trúc project

```
fb-bot/
├── src/
│   ├── research/          # Module research boardgame
│   │   └── bgg_scraper.py
│   ├── content/           # Module AI content generation
│   │   └── content_generator.py
│   ├── images/            # Module xử lý hình ảnh
│   │   └── image_handler.py
│   ├── social/            # Module đăng Facebook
│   │   └── facebook_poster.py
│   └── utils/             # Utilities
│       ├── logger.py
│       └── config_loader.py
├── config/
│   ├── config.yaml        # Config chính (tạo từ .example)
│   └── config.yaml.example
├── data/
│   ├── boardgames.json    # Database game đã research
│   └── posted_logs.json   # Lịch sử đã đăng
├── images/                # Thư mục lưu ảnh tải về
├── logs/                  # Log files
├── main.py               # Script chính
├── scheduler.py          # Auto scheduling
├── requirements.txt      # Dependencies
└── README.md
```

## ⚙️ Cấu hình

### Config file (`config/config.yaml`)

```yaml
schedule:
  enabled: true
  post_time: "19:00"
  timezone: "Asia/Ho_Chi_Minh"
  frequency: "daily" # daily/weekly

content:
  types: ["review", "tutorial", "strategy"]
  language: "vi"
  min_length: 250
  max_length: 400

facebook:
  page_id: "${FACEBOOK_PAGE_ID}"
  access_token: "${FACEBOOK_ACCESS_TOKEN}"
  dry_run: false
  api_version: "v24.0"

research:
  min_rating: 7.0
  max_complexity: 4.0
  avoid_recent_days: 30
```

## 🔍 Workflow

1. **Research**: Tìm và lấy thông tin game từ BoardGameGeek
2. **Content**: Generate nội dung bằng Claude AI
3. **Image**: Download và optimize hình ảnh
4. **Post**: Đăng bài lên Facebook Page
5. **Log**: Lưu vào database để tránh trùng lặp

## 🐛 Troubleshooting

### Lỗi "Invalid access token"

- Kiểm tra token còn hạn chưa (long-lived token có thể hết hạn sau 60 ngày)
- Đảm bảo token có đủ permissions: `pages_read_engagement`, `pages_manage_posts`

### Lỗi "Permission denied"

- Kiểm tra Page ID đúng chưa
- Đảm bảo app có quyền quản lý Page

### Lỗi "ANTHROPIC_API_KEY not found"

- Kiểm tra file `.env` có đúng format không
- Đảm bảo đã load environment variables

### Lỗi "401 Unauthorized" khi query BGG API

- **Nguyên nhân**: Thiếu hoặc sai BGG API token
- **Giải pháp**:
  1. Kiểm tra `BGG_API_TOKEN` trong file `.env`
  2. Đảm bảo token hợp lệ (lấy từ https://boardgamegeek.com/applications)
  3. Token phải được tạo sau khi ứng dụng được phê duyệt
  4. Kiểm tra format: `BGG_API_TOKEN=your-token-here` (không có dấu ngoặc kép)

### Bot không tìm được game phù hợp

- Giảm `min_rating` hoặc tăng `max_complexity` trong config
- Kiểm tra kết nối internet và BGG API
- Đảm bảo BGG API token hợp lệ

## 📝 Logs

Logs được lưu trong thư mục `logs/bot.log` với rotation tự động (10MB/file, giữ 5 files).

## ⚠️ Lưu ý

1. **Facebook Terms of Service**: Chỉ post lên Page, không post profile cá nhân
2. **Rate Limits**:
   - BGG: ~1-2 requests/second
   - Facebook: 200 calls/hour/user
3. **API Costs**: Claude API có phí, theo dõi usage
4. **Security**: Không commit file `.env` và `config.yaml` vào Git

## 📚 Tài liệu tham khảo

- BoardGameGeek XML API: https://boardgamegeek.com/wiki/page/BGG_XML_API2
- Claude API: https://docs.anthropic.com/
- Facebook Graph API: https://developers.facebook.com/docs/graph-api
- APScheduler: https://apscheduler.readthedocs.io/

## 📄 License

MIT License
