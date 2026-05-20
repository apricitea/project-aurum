# Frontend Setup Guide for Multi-Developer Environment

## 🚨 CRITICAL: Working Directory Issues

The most common issue developers face is **running commands from the wrong directory**. This is a Python + TypeScript hybrid project, and the frontend has its own isolated environment.

### ✅ CORRECT Workflow

```bash
# Always start from project root
cd /path/to/project-aurum

# Then navigate to frontend
cd apps/web_dashboard/frontend

# Now you can run frontend commands
npm install
npm run dev
```

### ❌ WRONG Workflow (causes import errors)

```bash
# DON'T do this - causes "Failed to resolve import '@/lib/utils'"
cd /path/to/project-aurum
npm install  # This will fail - no package.json at root
npm run dev   # This will also fail
```

## Quick Setup for New Developers

### 1. Project Structure Understanding

```
project-aurum/                    # ← Project root (Python backend)
├── src/                         # Python backend code
├── apps/web_dashboard/frontend/ # ← Frontend directory (React/TypeScript)
│   ├── src/
│   │   ├── lib/utils.ts        # ← This file exists here
│   │   └── components/         # ← Components that import from @/lib/utils
│   ├── package.json            # ← Frontend dependencies
│   ├── vite.config.ts          # ← Vite config with @ alias
│   └── tsconfig.json           # ← TypeScript config with @ paths
└── pyproject.toml              # ← Python backend config
```

### 2. Prerequisites

- Node.js 18+ (frontend)
- Python 3.11+ (backend)
- Git

### 3. Frontend Setup

```bash
# Navigate to frontend directory
cd apps/web_dashboard/frontend

# Install dependencies
npm install

# Start development server
npm run dev

# Open http://localhost:3000
```

### 4. Backend Setup (separate from frontend)

```bash
# Navigate to project root
cd /path/to/project-aurum

# Setup Python environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install Python dependencies
pip install -e .

# Start backend server
python main.py
```

## Common Issues & Solutions

### Issue 1: "Failed to resolve import '@/lib/utils'"

**Cause**: Running npm commands from wrong directory
**Solution**: Always run from `apps/web_dashboard/frontend/`

```bash
# Check current directory
pwd  # Should end with apps/web_dashboard/frontend

# If not, navigate there
cd apps/web_dashboard/frontend

# Verify package.json exists
ls package.json  # Should show the file

# Now run commands
npm run dev
```

### Issue 2: Module resolution fails in IDE

**Cause**: IDE doesn't understand the @ alias
**Solution**: Ensure IDE is configured correctly

- **VS Code**: Open the project from `apps/web_dashboard/frontend/` directory
- **WebStorm/IntelliJ**: Mark `apps/web_dashboard/frontend` as the project root

### Issue 3: TypeScript errors about @ paths

**Cause**: Missing or incorrect tsconfig.json configuration
**Solution**: Verify tsconfig.json has the paths configured:

```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

## Development Workflow

### Daily Development

```bash
# Start frontend (from frontend directory)
cd apps/web_dashboard/frontend
npm run dev

# Start backend (from project root, in separate terminal)
cd /path/to/project-aurum
source .venv/bin/activate
python main.py
```

### Code Quality Checks

```bash
# From frontend directory
npm run type-check  # TypeScript checking
npm run lint        # ESLint checking
```

### Building for Production

```bash
# From frontend directory
npm run build

# Output will be in dist/ directory
```

## Git & Collaboration

### Files That Should Be Tracked

All important frontend files are tracked by git, including:
- `src/lib/utils.ts` - Core utility functions
- `src/components/` - React components
- `vite.config.ts` - Vite configuration
- `tsconfig.json` - TypeScript configuration
- `package.json` - Dependencies and scripts

### Files That Should NOT Be Tracked

- `node_modules/` - Dependencies (in .gitignore)
- `dist/` - Build output (in .gitignore)
- `.env` - Environment variables (in .gitignore)

### Fixing Git Issues

If you find important files aren't tracked:

```bash
# Check git status from frontend directory
cd apps/web_dashboard/frontend
git status

# Add missing files
git add src/lib/utils.ts
git commit -m "Add missing utility files"
```

## IDE Configuration

### VS Code Settings

Create `.vscode/settings.json` in the frontend directory:

```json
{
  "typescript.preferences.importModuleSpecifier": "relative",
  "typescript.suggest.autoImports": true,
  "editor.formatOnSave": true
}
```

### Recommended Extensions

- TypeScript and JavaScript Language Features
- ES7+ React/Redux/React-Native snippets
- Tailwind CSS IntelliSense
- Auto Rename Tag
- Prettier - Code formatter

## Team Communication

When reporting frontend issues:

1. **Always include your working directory**: `pwd` output
2. **Include the exact command** you ran
3. **Include the full error message**
4. **Mention if you're using WSL, Windows, or macOS**

### Example Issue Report

```
Working Directory: /home/user/project-aurum/apps/web_dashboard/frontend
Command: npm run dev
Error: Failed to resolve import "@/lib/utils"
OS: Ubuntu 22.04 WSL2
```

This helps us quickly identify if it's a working directory issue or something else.

## Architecture Notes

### Import Path Resolution

- `@` alias maps to `src/` directory
- Configured in both `vite.config.ts` and `tsconfig.json`
- Works for both development and production builds

### State Management

- Uses Zustand for simple, powerful state management
- Stores are in `src/store/` directory
- No complex Redux setup required

### Styling

- Tailwind CSS for utility-first styling
- Custom components in `src/components/ui/`
- Responsive design approach

## Testing the Setup

Verify everything works:

```bash
# From frontend directory
npm run build  # Should complete without errors
npm run preview  # Should show built app

# Check imports work
npm run type-check  # Should show no import resolution errors
```

If all these pass, your setup is correct!