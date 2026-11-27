const capabilities = [
  {
    title: "Create exam templates",
    description: "Define questions, options, sections, and marking rules.",
  },
  {
    title: "Scan from phone or scanner",
    description: "Capture pages or upload a multipage PDF for processing.",
  },
  {
    title: "Review before grading",
    description: "Resolve uncertain and multiple-mark responses with evidence.",
  },
];

export default function HomePage() {
  return (
    <main className="shell">
      <nav className="nav">
        <a className="brand" href="/" aria-label="OMR Checker home">
          <span className="brand-mark">O</span>
          <span>OMR Checker</span>
        </a>
        <span className="nav-note">ACM BIT Mesra · Project foundation</span>
      </nav>

      <section className="hero">
        <p className="eyebrow">SCAN · RECOGNIZE · REVIEW · EVALUATE</p>
        <h1>OMR evaluation, made accessible.</h1>
        <p className="lede">
          Create printable answer sheets, scan them with a phone or document
          scanner, and evaluate responses with a transparent review workflow.
        </p>
        <div className="notice">
          <strong>Foundation build</strong>
          <span>
            Product architecture and starter services are in place. Recognition,
            exam management, and scanning workflows are under development.
          </span>
        </div>
      </section>

      <section className="grid" aria-label="Product capabilities">
        {capabilities.map((item) => (
          <article className="feature" key={item.title}>
            <span className="feature-status">Planned</span>
            <h2>{item.title}</h2>
            <p>{item.description}</p>
          </article>
        ))}
      </section>

      <footer className="footer">
        Built for dependable assessment workflows. Uncertain marks should always
        be reviewable.
      </footer>
    </main>
  );
}
