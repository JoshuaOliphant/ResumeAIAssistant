<<<<<<< HEAD
# Resume AI Assistant Frontend

A modern frontend for the Resume AI Assistant application, built with Next.js, TypeScript, Tailwind CSS, and shadcn UI.

## Features

- AI-powered resume customization and optimization
- ATS compatibility analysis
- Cover letter generation
- Export to multiple formats (PDF, DOCX, Markdown)
- Modern, responsive UI with dark mode support

## Tech Stack

- **Next.js 14** with App Router for frontend framework
- **TypeScript** for type safety
- **Tailwind CSS** for styling
- **shadcn UI** for component library
- **React Hook Form** with Zod for form validation
- **Lucide React** for icons
- **next-themes** for theme management
=======
# Resume AI Assistant - Next.js Frontend

This is the frontend application for the Resume AI Assistant, built with Next.js, TypeScript, and Tailwind CSS. It connects to a FastAPI backend running on port 5000.

## Features

- Modern UI built with Next.js and TypeScript
- Responsive design with Tailwind CSS
- UI components from shadcn/ui
- Resume analysis against job descriptions
- ATS optimization suggestions
- User authentication
>>>>>>> 046db8346d74349cca04626768a2da41bfd6abf7

## Getting Started

### Prerequisites

<<<<<<< HEAD
- Node.js 18.17.0 or higher
- npm or yarn
- Backend API running on port 5000 (see main project README)

### Installation

1. Clone the repository:

```bash
git clone <repository-url>
cd ResumeAIAssistant/frontend-next
```

2. Install dependencies:

```bash
npm install
# or
yarn
```

3. Start the development server:

```bash
npm run dev
# or
yarn dev
```

The application will be available at http://localhost:3000.

## Project Structure

- **app/** - Next.js App Router pages
- **components/** - Reusable React components
  - **ui/** - shadcn UI components
- **lib/** - Utility functions and API client
- **public/** - Static assets
=======
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
>>>>>>> 046db8346d74349cca04626768a2da41bfd6abf7

## Available Scripts

- `npm run dev` - Start the development server
- `npm run build` - Build the application for production
- `npm run start` - Start the production server
- `npm run lint` - Run ESLint

<<<<<<< HEAD
## API Integration

The frontend communicates with the FastAPI backend running on port 5000. API endpoints are defined in `lib/client.ts`.

## Authentication

The application uses OAuth2 for authentication, with JWT tokens stored in localStorage. Authentication state is managed through React Context.

## Theme

The application supports both light and dark themes, managed by the `next-themes` library.
=======
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
>>>>>>> 046db8346d74349cca04626768a2da41bfd6abf7
