import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactCompiler: true,
  // Force dynamic rendering for all pages
  output: 'standalone',
};

export default nextConfig;