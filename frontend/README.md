# Constellation Frontend

Next.js 16 frontend for the Constellation multi-agent safety system.

## Setup

```bash
npm install
cp .env.example .env.local
# Edit .env.local with your backend URL
npm run dev
```

## Deploy on Vercel

1. Import repo on Vercel
2. Set root directory to `frontend`
3. Add env variable: `NEXT_PUBLIC_API_URL` = your Render backend URL
