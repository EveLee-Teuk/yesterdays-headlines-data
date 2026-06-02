import type {Metadata} from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: "昨日头条",
  description: '为现代读者精心挑选的高端新闻。',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN" className="dark" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=PT+Sans:wght@400;700&family=Noto+Serif+SC:wght@400;700&display=swap" rel="stylesheet" />
      </head>
      <body className="font-body selection:bg-primary selection:text-white">
        <div className="mx-auto min-h-screen max-w-md bg-obsidian shadow-2xl overflow-hidden relative">
          {children}
        </div>
      </body>
    </html>
  );
}
