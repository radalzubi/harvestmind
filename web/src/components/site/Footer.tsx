import Link from "next/link";
import { Logo } from "./Logo";

export function Footer() {
  return (
    <footer className="site-footer">
      <div className="site-footer-inner">
        <div className="site-footer-brand">
          <Logo size={22} muted />
          <p>Purchasing decisions for businesses that import what they sell. Built in Amman.</p>
        </div>
        <div className="site-footer-cols">
          <div>
            <h4>Product</h4>
            <Link href="/product">How it works</Link>
            <Link href="/sectors">Sectors</Link>
            <Link href="/security">Security</Link>
          </div>
          <div>
            <h4>Company</h4>
            <Link href="/about">About</Link>
            <Link href="/contact">Contact</Link>
          </div>
          <div>
            <h4>Workspace</h4>
            <Link href="/get-started">Get started</Link>
            <Link href="/get-started?mode=key">Enter a key</Link>
          </div>
          <div>
            <h4>Legal</h4>
            <Link href="/privacy">Privacy</Link>
            <Link href="/terms">Terms</Link>
          </div>
        </div>
      </div>
      <div className="site-footer-base">
        <span>© {new Date().getFullYear()} Zaad Supply</span>
        <span>No forecasts of savings. Ever.</span>
      </div>
    </footer>
  );
}
