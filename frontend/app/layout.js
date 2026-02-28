import "./globals.css";

export const metadata = {
  title: "Youticle Workspace",
  description: "Strategy + Generation collaboration workspace",
};

export default function RootLayout({ children }) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
