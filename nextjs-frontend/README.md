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

## Getting Started

### Prerequisites

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

## Available Scripts

- `npm run dev` - Start the development server
- `npm run build` - Build the application for production
- `npm run start` - Start the production server
- `npm run lint` - Run ESLint

## API Integration

The frontend communicates with the FastAPI backend running on port 5000. API endpoints are defined in `lib/client.ts`.

## Authentication

The application uses OAuth2 for authentication, with JWT tokens stored in localStorage. Authentication state is managed through React Context.

## Theme

The application supports both light and dark themes, managed by the `next-themes` library.