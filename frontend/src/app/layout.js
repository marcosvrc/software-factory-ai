import "./globals.css";
import { AppShell } from "@/components/layout/AppShell";
import { ToastProvider } from "@/components/ui/Toast";

export const metadata = {
  title: "Software Factory",
  description: "Fábrica de software local multiagente",
};

export default function RootLayout({ children }) {
  return (
    <html lang="pt-BR">
      <body className="font-sans antialiased">
        <ToastProvider>
          <AppShell>{children}</AppShell>
        </ToastProvider>
      </body>
    </html>
  );
}
