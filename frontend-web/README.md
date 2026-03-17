# Fingerprint Vision Lab (Web Frontend)

A modern web interface for the Fingerprint Vision Lab system, built with React, Vite, TailwindCSS, and Framer Motion.

## Features

- Minimal, premium AI dashboard UI
- Glassmorphism upload panel
- Subtle animations (fade-in, hover, scanning effect)
- Drag & drop file upload
- Results grid with four visualization cards
- Metrics dashboard with animated numbers

## Requirements

- Node.js 18+

## Run Locally

```bash
npm install
npm run dev
```

The app runs on `http://localhost:5174` by default.

## API Endpoint

The frontend calls:

```
POST /api/analyze
```

You can configure a custom backend base URL with:

```
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## Notes

- The interface expects image URLs in the response under `images`.
- If your backend returns base64 images, it will still render them automatically.
