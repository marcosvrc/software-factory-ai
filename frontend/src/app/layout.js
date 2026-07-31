export const metadata = {
  title: "Software Factory",
  description: "Fábrica de software local multiagente",
};

const nav = {
  display: "flex", gap: "1.5rem", padding: "1rem 2rem",
  borderBottom: "1px solid #e2e2e2", alignItems: "center",
};

export default function RootLayout({ children }) {
  return (
    <html lang="pt-BR">
      <body style={{ fontFamily: "system-ui, sans-serif", margin: 0, color: "#1a1a1a" }}>
        <nav style={nav}>
          <strong>🏭 Software Factory</strong>
          <a href="/">Dashboard</a>
          <a href="/projects">Projetos</a>
          <a href="/approvals">Aprovações</a>
        </nav>
        <main style={{ padding: "2rem", maxWidth: 1100, margin: "0 auto" }}>{children}</main>
      </body>
    </html>
  );
}
