# Resume AI Assistant - Next.js Frontend

This is the frontend application for the Resume AI Assistant, built with Next.js, TypeScript, and Tailwind CSS. It connects to a FastAPI backend running on port 5000.

## Features

- Modern UI built with Next.js and TypeScript
- Responsive design with Tailwind CSS
- UI components from shadcn/ui
- Resume analysis against job descriptions
- ATS optimization suggestions
- User authentication

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- FastAPI backend running on port 5000

### Installation

1. Clone the repository
2. Navigate to the project directory:

```bash
cd nextjs-frontend/resume-ai-assistant
```

3. Install dependencies:

```bash
npm install
```

4. Start the development server:

```bash
npm run dev
```

The application will be available at [http://localhost:3000](http://localhost:3000).

## Project Structure

- `src/app/` - Next.js App Router pages
- `src/components/` - Reusable React components
- `src/lib/` - Utility functions and API client
- `src/styles/` - Global styles

## API Integration

The frontend communicates with the FastAPI backend through the API client in `src/lib/client.ts`. This client handles:

- Resume analysis requests
- User authentication
- Error handling
- Response parsing

## Available Scripts

- `npm run dev` - Start the development server
- `npm run build` - Build the application for production
- `npm run start` - Start the production server
- `npm run lint` - Run ESLint

## Deployment

To deploy the application:

1. Build the application:

```bash
npm run build
```

2. Start the production server:

```bash
npm run start
```

## Backend Connection

The frontend is configured to connect to a FastAPI backend running on `http://localhost:5000`. If your backend is running on a different URL, update the `API_BASE_URL` in `src/lib/client.ts`.
