import { Nav } from "@/components/site/Nav";
import { Footer } from "@/components/site/Footer";

export default function SiteLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="site">
      <Nav />
      <main className="site-main">{children}</main>
      <Footer />
    </div>
  );
}
