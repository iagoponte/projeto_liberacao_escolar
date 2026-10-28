/** @type {import("next").NextConfig} */

const nextConfig = {
  async rewrites() {
    const backend = (
      process.env.API_PROXY_TARGET ?? "http://127.0.0.1:8000"
    ).replace(/\/$/, "");

    return [
      {
        source: "/api/backend/:path*",
        destination: `${backend}/:path*`,
      },
    ];
  },
};

export default nextConfig;