# ResumeAIAssistant Frontend Development Assignment

## Task Overview
You are assigned to work on issue #{ISSUE_NUMBER} for the ResumeAIAssistant project. You'll need to:

1. Retrieve the issue details using GitHub CLI
2. Understand the frontend codebase structure
3. Implement the requested feature/fix according to project standards
4. Submit a pull request with your changes

## Setup and Authentication
The GitHub CLI is already authenticated and configured for this repository. You can access the issue using:

```bash
gh issue view {ISSUE_NUMBER} --repo JoshuaOliphant/ResumeAIAssistant
```

## Project Architecture Overview
ResumeAIAssistant is a resume customization and ATS optimization application with these key components:

1. **Next.js Frontend**: Modern interface with App Router, shadcn UI, and Tailwind CSS
2. **PydanticAI Backend**: A model-agnostic AI system for resume customization
3. **Multi-Model Support**: Integration with multiple AI providers (Anthropic Claude, Google Gemini, OpenAI)

## Key Frontend Concepts

### Tech Stack
- **Next.js 14**: React framework with App Router
- **TypeScript**: For type safety and better developer experience
- **Tailwind CSS**: For styling
- **shadcn/ui**: Component library for consistent UI
- **React Hook Form**: Form validation with Zod
- **next-themes**: Theme management (light/dark mode)

### Frontend Structure
- `/nextjs-frontend/app`: Next.js App Router pages
- `/nextjs-frontend/components`: Reusable React components
  - `/ui`: shadcn UI components
- `/nextjs-frontend/lib`: Utility functions and API client
  - `client.ts`: API client for FastAPI backend
  - `utils.ts`: Helper functions

### UI/UX Design Guidelines
- **Responsive Design**: All components must work on mobile, tablet, and desktop
- **Accessibility**: Components should follow WCAG 2.1 AA standards
  - Use proper semantic HTML elements
  - Include appropriate ARIA attributes
  - Ensure keyboard navigation works
  - Maintain sufficient color contrast
- **Theme Support**: All components should work in both light and dark mode
- **Loading States**: Include proper loading states for all async operations
- **Error Handling**: Provide user-friendly error messages and recovery options

### Browser Compatibility
- **Target Browsers**:
  - Chrome (latest 2 versions)
  - Firefox (latest 2 versions)
  - Safari (latest 2 versions)
  - Edge (latest 2 versions)
- **Mobile Browsers**:
  - iOS Safari (latest 2 versions)
  - Android Chrome (latest 2 versions)

### Performance Expectations
- **First Contentful Paint**: < 1.5s
- **Time to Interactive**: < 3.5s
- **Lighthouse Score**: 90+ for Performance, Accessibility, Best Practices, and SEO
- **Bundle Size**: Keep page bundles < 300KB (gzipped)

## Development Guidelines

### Code Style
- Use TypeScript for type safety
- Follow ESLint and Prettier configurations
- Use functional components with hooks
- Use camelCase for variables/functions, PascalCase for components
- Import order: React, third-party, local (with blank lines between groups)

### Component Structure
- Each component should have a single responsibility
- Break large components into smaller, reusable ones
- Leverage shadcn UI components when possible
- Use proper prop typing with TypeScript interfaces
- Include JSDoc comments for complex components

### State Management
- Use React hooks for local state
- Use React Context for shared state when needed
- Use React Query for server state management
- Avoid prop drilling by using composition or context

### API Integration
- Use the client.ts utility for all API calls
- Handle loading, error, and success states
- Implement proper error handling and retries
- Use React Query for data fetching and caching

## Getting Started

1. Create a development branch:
```bash
gh issue develop {ISSUE_NUMBER} --repo JoshuaOliphant/ResumeAIAssistant --name feature/issue-{ISSUE_NUMBER}
```

2. Start the frontend development server:
```bash
cd nextjs-frontend
npm install
npm run dev
```

3. Explore the codebase to understand the components relevant to your task

4. Implement your changes according to the issue requirements

5. Test your changes across different browsers and screen sizes

6. Run linting to ensure code quality:
```bash
npm run lint
```

7. Create a pull request when complete:
```bash
gh pr create --title "Fix/Feature: Issue #{ISSUE_NUMBER} description" --body "Resolves #{ISSUE_NUMBER}"
```

## Additional Resources
- **Design System**: Reference existing components in `/nextjs-frontend/components/ui`
- **API Documentation**: Available at http://localhost:5001/docs when backend is running
- **shadcn/ui Documentation**: https://ui.shadcn.com/docs
- **Next.js Documentation**: https://nextjs.org/docs
- **Tailwind CSS Documentation**: https://tailwindcss.com/docs

Good luck with your implementation! Feel free to ask clarifying questions about the codebase as you work.