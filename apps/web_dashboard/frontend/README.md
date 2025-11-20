# Project Aurum - Frontend Dashboard

This is the React + TypeScript frontend for the Project Aurum Indonesian Quantitative Trading Dashboard.

## **IMPORTANT: Working Directory Requirement**

⚠️ **ALWAYS run commands from this directory** (`apps/web_dashboard/frontend/`)

**WRONG:** `cd /path/to/project-aurum && npm run dev`
**CORRECT:** `cd /path/to/project-aurum/apps/web_dashboard/frontend && npm run dev`

## Quick Start

```bash
# From the project root
cd apps/web_dashboard/frontend

# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Type checking
npm run type-check

# Linting
npm run lint
```

## Development Server

The development server runs on `http://localhost:3000` with the following proxy configuration:
- API requests (`/api/*`) → `http://localhost:8000` (Python backend)
- WebSocket connections (`/ws/*`) → `ws://localhost:8000`

## Project Structure

```
frontend/
├── src/
│   ├── components/         # React components
│   │   ├── ui/            # Reusable UI components
│   │   └── dashboard/     # Dashboard-specific components
│   ├── lib/               # Utility functions and API helpers
│   ├── pages/             # Page components
│   ├── store/             # Zustand state management
│   ├── types/             # TypeScript type definitions
│   └── App.tsx            # Main application component
├── public/                # Static assets
├── dist/                  # Build output (generated)
├── package.json           # Dependencies and scripts
├── vite.config.ts         # Vite configuration (with @ alias)
└── tsconfig.json          # TypeScript configuration (with @ paths)
```

## Import Path Resolution

This project uses the `@` alias for clean imports:

```typescript
// Instead of this:
import { cn } from '../../../lib/utils'

// Use this:
import { cn } from '@/lib/utils'
```

The `@` alias is configured in both `vite.config.ts` and `tsconfig.json` to point to the `src/` directory.

## Key Features

- **Real-time Updates**: WebSocket connection for live market data
- **Indonesian Market Focus**: WIB timezone handling and IDX market hours
- **Responsive Design**: Mobile-first approach with Tailwind CSS
- **Type Safety**: Full TypeScript implementation
- **Modern Stack**: React 18 + Vite + Zustand

## Troubleshooting

### Import Resolution Errors

If you get `Failed to resolve import "@/lib/utils"` errors:

1. **Check your working directory:**
   ```bash
   pwd  # Should show .../apps/web_dashboard/frontend
   ```

2. **Ensure you're in the correct directory:**
   ```bash
   cd apps/web_dashboard/frontend
   npm install
   npm run dev
   ```

3. **Verify configurations are correct:**
   - `vite.config.ts` should have the `@` alias
   - `tsconfig.json` should have the `@` path mapping

### Build Issues

```bash
# Clean and reinstall
rm -rf node_modules dist package-lock.json
npm install
npm run build
```

### Type Checking Issues

```bash
# Check for TypeScript errors
npm run type-check

# Fix automatically where possible
npm run lint -- --fix
```

## Environment Variables

Copy `.env.example` to `.env` and update as needed:

```bash
cp .env.example .env
```

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint
- `npm run type-check` - Run TypeScript compiler check

## Backend Integration

This frontend expects a Python backend running on `http://localhost:8000`. Make sure the backend is running before starting the frontend development server.