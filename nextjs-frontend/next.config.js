/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:5001/api/:path*', // Proxy to Backend on port 5001
      },
    ]
  },
  // Increase API timeout for long-running operations like job extraction
  serverRuntimeConfig: {
    api: {
      // Response timeout is 120 seconds
      responseTimeout: 120000,
    },
  },
}

module.exports = nextConfig
