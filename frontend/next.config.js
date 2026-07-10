/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Disable linting and TS check during build if desired, to ensure fast startup
  typescript: {
    ignoreBuildErrors: true,
  },
  eslint: {
    ignoreDuringBuilds: true,
  },
};

module.exports = nextConfig;
