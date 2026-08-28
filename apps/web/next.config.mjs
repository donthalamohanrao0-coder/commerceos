/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  eslint: {
    // lint is run explicitly in CI; don't fail production builds on style.
    ignoreDuringBuilds: true,
  },
  images: {
    // Product photography is hotlinked from Unsplash's CDN (permissive licence,
    // hotlink-friendly). Every <Image> falls back to a generated tile on error.
    remotePatterns: [{ protocol: "https", hostname: "images.unsplash.com" }],
  },
};

export default nextConfig;
