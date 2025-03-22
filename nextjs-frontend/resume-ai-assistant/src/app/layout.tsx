import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import Link from "next/link";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Resume AI Assistant",
  description: "AI-powered resume analysis and optimization tool",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased min-h-screen flex flex-col`}
      >
        <header className="border-b border-gray-200 py-4">
          <div className="container mx-auto px-4 flex justify-between items-center">
            <Link href="/" className="text-xl font-bold">Resume AI Assistant</Link>
            <nav>
              <ul className="flex space-x-6">
                <li><Link href="/features" className="hover:text-gray-600 transition-colors">Features</Link></li>
                <li><Link href="/how-it-works" className="hover:text-gray-600 transition-colors">How It Works</Link></li>
                <li><Link href="/api-docs" className="hover:text-gray-600 transition-colors">API Docs</Link></li>
              </ul>
            </nav>
          </div>
        </header>
        <main className="flex-grow container mx-auto px-4 py-8">
          {children}
        </main>
        <footer className="border-t border-gray-200 py-6 bg-gray-50">
          <div className="container mx-auto px-4">
            <div className="flex flex-col md:flex-row justify-between items-center">
              <p className="text-sm text-gray-600">&copy; {new Date().getFullYear()} Resume AI Assistant. All rights reserved.</p>
              <div className="flex space-x-4 mt-4 md:mt-0">
                <Link href="/privacy" className="text-sm text-gray-600 hover:text-gray-900">Privacy Policy</Link>
                <Link href="/terms" className="text-sm text-gray-600 hover:text-gray-900">Terms of Service</Link>
                <Link href="/contact" className="text-sm text-gray-600 hover:text-gray-900">Contact</Link>
              </div>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
