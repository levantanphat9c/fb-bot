# Hướng dẫn Setup nhanh

## Bước 1: Cài đặt dependencies

```bash
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Bước 2: Cấu hình

### Tạo file `.env`:

```bash
cp env.example .env
```

Chỉnh sửa `.env` và điền:

- `FACEBOOK_PAGE_ID`: ID của Facebook Page
- `FACEBOOK_ACCESS_TOKEN`: Long-lived Page Access Token
- `ANTHROPIC_API_KEY`: API key từ Anthropic
- `UNSPLASH_ACCESS_KEY`: (Optional) API key từ Unsplash

### Tạo file `config/config.yaml`:

```bash
cp config/config.yaml.example config/config.yaml
```

Chỉnh sửa `config/config.yaml` nếu cần (thời gian đăng, loại content, v.v.)

## Bước 3: Test

```bash
# Test mode (không post thật)
python main.py --dry-run

# Chạy thật với manual approval
python main.py --manual-approve
```

## Bước 4: Chạy scheduler

```bash
python scheduler.py
```

## Lấy Facebook Access Token

1. Vào https://developers.facebook.com/
2. Tạo App mới (type: Business)
3. Add product: "Facebook Login"
4. Tools → Graph API Explorer
5. Select app, add permissions: `pages_read_engagement`, `pages_manage_posts`
6. Generate token → Extend thành long-lived token (60 days)
7. Copy token vào `.env`

## Lấy Page ID

1. Vào Facebook Page của bạn
2. Settings → Advanced
3. Copy Page ID vào `.env`
