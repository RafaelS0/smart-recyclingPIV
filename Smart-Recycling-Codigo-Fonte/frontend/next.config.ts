import type { NextConfig } from "next";
const config: NextConfig = {
  basePath: "/smart_recycling",
  trailingSlash: true,
  output: "standalone",
  poweredByHeader: false,
  experimental: { cpus: 1 },
  devIndicators: false,
};
export default config;
