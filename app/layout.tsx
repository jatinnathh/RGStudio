import type { Metadata } from "next";
import { Playfair_Display, DM_Sans, Dancing_Script } from "next/font/google";
import "./globals.css";
import { PageVisit } from "./components/PageVisit";

const playfairDisplay = Playfair_Display({
  subsets: ["latin"],
  variable: "--font-playfair",
  display: "swap",
  style: ["normal", "italic"],
  weight: ["400", "700"],
});

const dmSans = DM_Sans({
  subsets: ["latin"],
  variable: "--font-dm-sans",
  display: "swap",
  weight: ["300", "400", "500"],
});

const dancingScript = Dancing_Script({
  subsets: ["latin"],
  variable: "--font-dancing",
  display: "swap",
  weight: ["700"],
});

export const metadata: Metadata = {
  title: "RGStudio — RAG-Powered GAN Art Studio",
  description:
    "Describe an art style, RAG retrieves reference images + artist context, CLIP-guided GAN generates new artwork in that style. Two systems, one seamless pipeline.",
  keywords: [
    "AI Art",
    "Style Transfer",
    "RAG",
    "GAN",
    "CLIP",
    "Art Generation",
    "RGStudio",
  ],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${playfairDisplay.variable} ${dmSans.variable} ${dancingScript.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <PageVisit />
        {children}
      </body>
    </html>
  );
}
