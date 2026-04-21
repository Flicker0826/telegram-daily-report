# 📊 Daily Financial Report Telegram Bot

매일 정해진 시간에 경제 뉴스, 환율, 주가, 포트폴리오 분석을 텔레그램으로 받는 자동화 시스템

## 🏗️ 아키텍처

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  데이터 수집      │     │  LLM 분석         │     │  텔레그램 전송    │
│                 │     │                  │     │                 │
│ • pykrx (주가)   │────▶│ Gemini API       │────▶│ Telegram Bot    │
│ • yfinance (해외) │     │ (무료 tier)       │     │ API (무료)       │
│ • 환율 API       │     │                  │     │                 │
│ • 뉴스 RSS       │     │ • 시장 분석        │     │ • 포맷팅 리포트   │
│                 │     │ • 리밸런싱 조언     │     │ • 푸시 알림       │
└─────────────────┘     └──────────────────┘     └─────────────────┘
        ▲                       ▲
        │                       │
┌───────┴─────────┐     ┌───────┴──────────┐
│ Google Sheets   │     │ GitHub Actions   │
│ (포트폴리오)     │     │ (스케줄러, 무료)   │
└─────────────────┘     └──────────────────┘
```

## 💰 비용: 전부 무료

| 서비스 | 무료 조건 |
|--------|----------|
| Gemini API | 15 RPM, 일 100만 토큰 |
| GitHub Actions | Public repo 무제한 / Private 2,000분/월 |
| Google Sheets API | 일 300회 읽기 무료 |
| Telegram Bot API | 완전 무료 |
| pykrx / yfinance | 오픈소스 |

## 🚀 설정 방법 (Step by Step)

### Step 1: Telegram Bot 만들기
1. 텔레그램에서 `@BotFather` 검색 → `/newbot` 명령
2. 봇 이름, username 설정
3. **Bot Token** 저장 (예: `7123456789:AAF...`)
4. 생성된 봇에게 아무 메시지 전송
5. `https://api.telegram.org/bot<TOKEN>/getUpdates` 접속 → **Chat ID** 확인

### Step 2: Google Sheets 연동
1. [Google Cloud Console](https://console.cloud.google.com/) → 프로젝트 생성
2. **Google Sheets API** + **Google Drive API** 활성화
3. 사용자 인증 정보 → **서비스 계정** 생성
4. 키(JSON) 다운로드 → `credentials.json`으로 저장
5. Google Sheets에 포트폴리오 시트 생성 (아래 형식)
6. 시트를 서비스 계정 이메일과 **공유**

#### 📋 포트폴리오 시트 형식
| 종목코드 | 종목명 | 매수가 | 수량 | 매수일 | 시장 |
|---------|--------|-------|------|-------|------|
| 005930 | 삼성전자 | 72000 | 10 | 2024-01-15 | KRX |
| 000660 | SK하이닉스 | 135000 | 5 | 2024-03-20 | KRX |
| AAPL | 애플 | 178.5 | 3 | 2024-02-10 | US |

### Step 3: Gemini API 키
1. [Google AI Studio](https://aistudio.google.com/apikey) 접속
2. API 키 생성 (무료)

### Step 4: GitHub Actions 설정
1. 이 프로젝트를 GitHub에 push
2. Repository → Settings → Secrets and variables → Actions
3. 아래 Secrets 추가:

| Secret Name | 값 |
|-------------|-----|
| `TELEGRAM_BOT_TOKEN` | 봇 토큰 |
| `TELEGRAM_CHAT_ID` | 채팅 ID |
| `GEMINI_API_KEY` | Gemini API 키 |
| `GOOGLE_SHEETS_CREDS` | credentials.json 내용 (전체 JSON) |
| `GOOGLE_SHEET_ID` | 스프레드시트 URL의 ID 부분 |

### Step 5: 실행
- **자동**: GitHub Actions가 매일 오전 7:30 KST에 실행
- **수동**: Actions 탭 → "Run workflow" 클릭
- **로컬 테스트**: `python main.py`

## 📁 파일 구조
```
telegram-daily-report/
├── main.py                  # 메인 실행 파일
├── collectors/
│   ├── __init__.py
│   ├── market_data.py       # 주가/환율 수집
│   └── news_collector.py    # 뉴스 RSS 수집
├── portfolio/
│   ├── __init__.py
│   └── sheets_loader.py     # Google Sheets 포트폴리오 로드
├── analysis/
│   ├── __init__.py
│   └── llm_analyzer.py      # Gemini LLM 분석
├── messenger/
│   ├── __init__.py
│   └── telegram_sender.py   # 텔레그램 전송
├── config.py                # 환경변수 설정
├── requirements.txt
├── .github/
│   └── workflows/
│       └── daily_report.yml # GitHub Actions 스케줄
└── README.md
```

