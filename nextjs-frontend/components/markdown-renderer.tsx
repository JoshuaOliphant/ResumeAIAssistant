"use client"

import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

export function MarkdownRenderer({ content, className = "" }: MarkdownRendererProps) {
  return (
    <div className={`prose prose-gray dark:prose-invert max-w-none ${className}`}>
      <ReactMarkdown 
        remarkPlugins={[remarkGfm]}
        components={{
          // Headers
          h1: ({children}) => (
            <h1 className="text-3xl font-bold mt-8 mb-4 text-gray-900 dark:text-gray-100">
              {children}
            </h1>
          ),
          h2: ({children}) => (
            <h2 className="text-2xl font-semibold mt-6 mb-3 text-gray-800 dark:text-gray-200">
              {children}
            </h2>
          ),
          h3: ({children}) => (
            <h3 className="text-xl font-semibold mt-4 mb-2 text-gray-800 dark:text-gray-200">
              {children}
            </h3>
          ),
          h4: ({children}) => (
            <h4 className="text-lg font-medium mt-3 mb-2 text-gray-700 dark:text-gray-300">
              {children}
            </h4>
          ),
          
          // Lists
          ul: ({children}) => (
            <ul className="list-disc list-inside space-y-2 my-4 ml-4 text-gray-700 dark:text-gray-300">
              {children}
            </ul>
          ),
          ol: ({children}) => (
            <ol className="list-decimal list-inside space-y-2 my-4 ml-4 text-gray-700 dark:text-gray-300">
              {children}
            </ol>
          ),
          li: ({children}) => (
            <li className="leading-relaxed">
              {children}
            </li>
          ),
          
          // Text elements
          p: ({children}) => (
            <p className="my-4 leading-relaxed text-gray-700 dark:text-gray-300">
              {children}
            </p>
          ),
          strong: ({children}) => (
            <strong className="font-semibold text-gray-900 dark:text-gray-100">
              {children}
            </strong>
          ),
          em: ({children}) => (
            <em className="italic text-gray-700 dark:text-gray-300">
              {children}
            </em>
          ),
          
          // Code
          code: ({children}) => (
            <code className="bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded text-sm font-mono text-gray-800 dark:text-gray-200">
              {children}
            </code>
          ),
          pre: ({children}) => (
            <pre className="bg-gray-100 dark:bg-gray-800 p-4 rounded-lg overflow-x-auto my-4 text-sm">
              {children}
            </pre>
          ),
          
          // Other elements
          blockquote: ({children}) => (
            <blockquote className="border-l-4 border-gray-300 dark:border-gray-700 pl-4 my-4 italic text-gray-700 dark:text-gray-300">
              {children}
            </blockquote>
          ),
          hr: () => (
            <hr className="my-8 border-t border-gray-300 dark:border-gray-700" />
          ),
          
          // Links
          a: ({href, children}) => (
            <a 
              href={href} 
              className="text-blue-600 dark:text-blue-400 hover:underline"
              target="_blank"
              rel="noopener noreferrer"
            >
              {children}
            </a>
          ),
          
          // Tables
          table: ({children}) => (
            <div className="overflow-x-auto my-4">
              <table className="min-w-full divide-y divide-gray-300 dark:divide-gray-700">
                {children}
              </table>
            </div>
          ),
          thead: ({children}) => (
            <thead className="bg-gray-50 dark:bg-gray-800">
              {children}
            </thead>
          ),
          tbody: ({children}) => (
            <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-800">
              {children}
            </tbody>
          ),
          tr: ({children}) => (
            <tr>
              {children}
            </tr>
          ),
          th: ({children}) => (
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-600 dark:text-gray-400 uppercase tracking-wider">
              {children}
            </th>
          ),
          td: ({children}) => (
            <td className="px-4 py-3 text-sm text-gray-700 dark:text-gray-300">
              {children}
            </td>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}