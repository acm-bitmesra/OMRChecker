import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "OMR Checker",
    short_name: "OMR Checker",
    description: "Create, scan, review, and evaluate OMR answer sheets.",
    start_url: "/",
    display: "standalone",
    background_color: "#f5f7f3",
    theme_color: "#176b50",
    icons: [
      {
        src: "/omr-icon.svg",
        sizes: "any",
        type: "image/svg+xml",
        purpose: "any",
      },
    ],
  };
}
