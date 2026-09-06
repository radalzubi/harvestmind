/** The homepage's atmosphere, without the network: every public page opens on the same air. */
export function PageAtmos() {
  return (
    <div className="page-atmos" aria-hidden>
      <div className="hero-atmos" />
      <div className="hero-noise" />
    </div>
  );
}
