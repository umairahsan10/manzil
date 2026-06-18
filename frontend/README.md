# Manzil Frontend

Next.js 16 + Tailwind CSS v4 + shadcn/ui frontend for the Manzil travel planner.

## Local Development

1. Install dependencies:
   ```bash
   npm install
   ```

2. Create `.env.local` (see `.env.local.example`):
   ```bash
   API_URL=http://127.0.0.1:8000
   ```

3. Start the dev server:
   ```bash
   npm run dev
   ```

The app will be available at http://localhost:3000.

## Pages

- `/` — Marketing landing page
- `/plan` — Trip planner form and results
- `/feedback` — Post-trip feedback

## Notes

- The frontend proxies `/api/*` requests to the FastAPI backend.
- Tailwind v4 uses CSS-based configuration (`app/globals.css`).
- shadcn/ui components are built on `@base-ui/react`.
