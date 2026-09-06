import { Nav } from "@/components/site/Nav";
import { Footer } from "@/components/site/Footer";
import { MotionRoot } from "@/components/site/MotionRoot";

export default function SiteLayout({ children }: { children: React.ReactNode }) {
  return (
    <MotionRoot>
      <div className="site">
        <Nav />
        <main className="site-main">{children}</main>
        <Footer />
      </div>
    </MotionRoot>
  );
}
