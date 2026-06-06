import { useState, useEffect, useRef } from "react";

const useInView = (threshold = 0.15) => {
  const ref = useRef(null);
  const [inView, setInView] = useState(false);
  useEffect(() => {
    const obs = new IntersectionObserver(([e]) => { if (e.isIntersecting) setInView(true); }, { threshold });
    if (ref.current) obs.observe(ref.current);
    return () => obs.disconnect();
  }, []);
  return [ref, inView];
};

const FadeIn = ({ children, delay = 0, className = "" }) => {
  const [ref, inView] = useInView();
  return (
    <div ref={ref} className={className} style={{
      opacity: inView ? 1 : 0,
      transform: inView ? "translateY(0)" : "translateY(32px)",
      transition: `opacity 0.8s ease ${delay}s, transform 0.8s ease ${delay}s`
    }}>{children}</div>
  );
};

const HexGrid = () => {
  const hexes = Array.from({ length: 48 }, (_, i) => ({ id: i, x: (i % 8) * 80 + ((Math.floor(i / 8) % 2) * 40), y: Math.floor(i / 8) * 70 }));
  return (
    <svg width="100%" height="100%" viewBox="0 0 640 420" style={{ position: "absolute", inset: 0, opacity: 0.12 }}>
      {hexes.map(h => (
        <polygon key={h.id} points={`${h.x+34},${h.y+8} ${h.x+60},${h.y+22} ${h.x+60},${h.y+52} ${h.x+34},${h.y+66} ${h.x+8},${h.y+52} ${h.x+8},${h.y+22}`}
          fill="none" stroke="#22c55e" strokeWidth="1" />
      ))}
    </svg>
  );
};

const LockIcon = ({ size = 48, animated = false }) => {
  const [open, setOpen] = useState(false);
  useEffect(() => { if (animated) { setTimeout(() => setOpen(true), 1200); setTimeout(() => setOpen(false), 2800); const t = setInterval(() => { setOpen(true); setTimeout(() => setOpen(false), 1600); }, 4000); return () => clearInterval(t); } }, [animated]);
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none">
      <rect x="8" y="22" width="32" height="22" rx="4" fill="#16a34a" opacity="0.9" />
      <path d={open ? "M14 22 V14 Q14 6 24 6 Q34 6 34 14 V18" : "M14 22 V16 Q14 6 24 6 Q34 6 34 16 V22"}
        stroke="#22c55e" strokeWidth="3" strokeLinecap="round" fill="none"
        style={{ transition: "d 0.5s ease" }} />
      <circle cx="24" cy="33" r="3" fill="#bbf7d0" />
      <line x1="24" y1="36" x2="24" y2="40" stroke="#bbf7d0" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
};

const FlowDiagram = () => {
  const [step, setStep] = useState(0);
  useEffect(() => { const t = setInterval(() => setStep(s => (s + 1) % 4), 1800); return () => clearInterval(t); }, []);
  const nodes = [
    { label: "Parsing local", x: 40, color: "#1e3a5f" },
    { label: "MinHash + BFV", x: 210, color: "#166534" },
    { label: "diff² homomorphe", x: 380, color: "#166534" },
    { label: "Déchiffrement", x: 550, color: "#1e3a5f" },
  ];
  return (
    <svg width="100%" viewBox="0 0 760 100" style={{ overflow: "visible" }}>
      {nodes.map((n, i) => (
        <g key={i}>
          <rect x={n.x} y="20" width="150" height="44" rx="8"
            fill={step === i ? n.color : "#0f172a"}
            stroke={step === i ? "#22c55e" : "#1e3a5f"}
            strokeWidth={step === i ? 2 : 1}
            style={{ transition: "all 0.4s ease" }} />
          <text x={n.x + 75} y="47" textAnchor="middle" fill={step === i ? "#bbf7d0" : "#64748b"} fontSize="11" fontFamily="monospace"
            style={{ transition: "all 0.4s ease" }}>{n.label}</text>
          {i < 3 && (
            <g>
              <line x1={n.x + 150} y1="42" x2={n.x + 200} y2="42" stroke={step > i ? "#22c55e" : "#1e3a5f"} strokeWidth="2" style={{ transition: "stroke 0.4s ease" }} />
              <polygon points={`${n.x + 200},38 ${n.x + 210},42 ${n.x + 200},46`} fill={step > i ? "#22c55e" : "#1e3a5f"} style={{ transition: "fill 0.4s ease" }} />
            </g>
          )}
        </g>
      ))}
    </svg>
  );
};

const SchemaCard = ({ title, tag, desc, features, accent }) => {
  const [ref, inView] = useInView();
  return (
    <div ref={ref} style={{
      background: "#0a1628", border: `1px solid ${inView ? accent : "#1e3a5f"}`, borderRadius: 12,
      padding: "28px", transition: "border-color 0.8s ease, transform 0.4s ease",
      transform: inView ? "translateY(0)" : "translateY(24px)",
      opacity: inView ? 1 : 0,
    }}
      onMouseEnter={e => e.currentTarget.style.transform = "translateY(-4px)"}
      onMouseLeave={e => e.currentTarget.style.transform = "translateY(0)"}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
        <span style={{ fontFamily: "monospace", fontSize: 22, fontWeight: 700, color: accent }}>{title}</span>
        <span style={{ fontSize: 11, background: accent + "22", color: accent, padding: "3px 10px", borderRadius: 20, border: `1px solid ${accent}44` }}>{tag}</span>
      </div>
      <p style={{ color: "#94a3b8", fontSize: 14, lineHeight: 1.6, marginBottom: 16 }}>{desc}</p>
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {features.map((f, i) => (
          <div key={i} style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <div style={{ width: 6, height: 6, borderRadius: "50%", background: accent, flexShrink: 0 }} />
            <span style={{ color: "#cbd5e1", fontSize: 13 }}>{f}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

const StatPill = ({ value, label, delay }) => {
  const [ref, inView] = useInView();
  return (
    <div ref={ref} style={{
      textAlign: "center", opacity: inView ? 1 : 0,
      transform: inView ? "scale(1)" : "scale(0.85)",
      transition: `all 0.6s ease ${delay}s`
    }}>
      <div style={{ fontSize: 42, fontWeight: 800, color: "#22c55e", fontFamily: "monospace", lineHeight: 1 }}>{value}</div>
      <div style={{ fontSize: 13, color: "#64748b", marginTop: 6, textTransform: "uppercase", letterSpacing: "0.08em" }}>{label}</div>
    </div>
  );
};

const TerminalBlock = ({ lines }) => {
  const [shown, setShown] = useState(0);
  const [ref, inView] = useInView();
  useEffect(() => { if (inView && shown < lines.length) { const t = setTimeout(() => setShown(s => s + 1), 400); return () => clearTimeout(t); } }, [inView, shown, lines.length]);
  return (
    <div ref={ref} style={{ background: "#020810", border: "1px solid #1e3a5f", borderRadius: 10, padding: "20px 24px", fontFamily: "monospace", fontSize: 13, lineHeight: 2 }}>
      <div style={{ display: "flex", gap: 6, marginBottom: 12 }}>
        {["#ff5f57", "#febc2e", "#28c840"].map((c, i) => <div key={i} style={{ width: 11, height: 11, borderRadius: "50%", background: c }} />)}
      </div>
      {lines.slice(0, shown).map((l, i) => (
        <div key={i} style={{ color: l.startsWith("$") ? "#22c55e" : l.startsWith("#") ? "#64748b" : "#cbd5e1" }}>{l}</div>
      ))}
      {shown < lines.length && <span style={{ borderRight: "2px solid #22c55e", animation: "blink 1s step-end infinite" }}>&nbsp;</span>}
    </div>
  );
};

export default function App() {
  const [scrollY, setScrollY] = useState(0);
  useEffect(() => { const h = () => setScrollY(window.scrollY); window.addEventListener("scroll", h); return () => window.removeEventListener("scroll", h); }, []);

  return (
    <div style={{ background: "#030b18", color: "#e2e8f0", fontFamily: "'Segoe UI', system-ui, sans-serif", overflowX: "hidden" }}>
      <style>{`
        @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }
        @keyframes float { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-12px)} }
        @keyframes pulse-ring { 0%{transform:scale(0.9);opacity:0.8} 100%{transform:scale(1.6);opacity:0} }
        @keyframes scanline { 0%{top:-10%} 100%{top:110%} }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        ::-webkit-scrollbar { width: 4px; } ::-webkit-scrollbar-track { background: #030b18; } ::-webkit-scrollbar-thumb { background: #166534; border-radius: 2px; }
      `}</style>

      {/* NAV */}
      <nav style={{ position: "fixed", top: 0, left: 0, right: 0, zIndex: 100, padding: "0 48px", height: 64, display: "flex", alignItems: "center", justifyContent: "space-between", background: scrollY > 40 ? "rgba(3,11,24,0.92)" : "transparent", backdropFilter: scrollY > 40 ? "blur(12px)" : "none", borderBottom: scrollY > 40 ? "1px solid #1e3a5f" : "none", transition: "all 0.3s ease" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <LockIcon size={28} />
          <span style={{ fontFamily: "monospace", fontWeight: 700, fontSize: 18, color: "#22c55e", letterSpacing: "0.05em" }}>CryptTraject</span>
        </div>
        <div style={{ display: "flex", gap: 32, fontSize: 14, color: "#94a3b8" }}>
          {[
            { label: "Concept", href: "#concept" },
            { label: "Pipeline", href: "#pipeline" },
            { label: "Workflow", href: "#workflow" },
            { label: "Télécharger", href: "#telecharger" },
          ].map(l => (
            <a key={l.label} href={l.href} style={{ color: "#94a3b8", textDecoration: "none", transition: "color 0.2s" }}
              onMouseEnter={e => e.target.style.color = "#22c55e"} onMouseLeave={e => e.target.style.color = "#94a3b8"}>{l.label}</a>
          ))}
        </div>
      </nav>

      {/* HERO */}
      <section style={{ minHeight: "100vh", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", position: "relative", padding: "80px 48px 60px", overflow: "hidden" }}>
        <HexGrid />
        <div style={{ position: "absolute", inset: 0, pointerEvents: "none", overflow: "hidden" }}>
          <div style={{ position: "absolute", left: 0, right: 0, height: "2px", background: "linear-gradient(transparent, #22c55e22, transparent)", animation: "scanline 6s linear infinite" }} />
        </div>
        <div style={{ position: "absolute", top: "20%", left: "10%", width: 300, height: 300, borderRadius: "50%", background: "radial-gradient(circle, #16653422 0%, transparent 70%)", filter: "blur(40px)" }} />
        <div style={{ position: "absolute", bottom: "20%", right: "10%", width: 400, height: 400, borderRadius: "50%", background: "radial-gradient(circle, #1e3a8a22 0%, transparent 70%)", filter: "blur(60px)" }} />

        <div style={{ position: "relative", textAlign: "center", maxWidth: 800 }}>
          <div style={{ animation: "float 5s ease-in-out infinite", marginBottom: 32 }}>
            <div style={{ position: "relative", display: "inline-block" }}>
              <div style={{ position: "absolute", inset: -16, borderRadius: "50%", border: "2px solid #22c55e44", animation: "pulse-ring 2s ease-out infinite" }} />
              <div style={{ position: "absolute", inset: -8, borderRadius: "50%", border: "1px solid #22c55e66" }} />
              <LockIcon size={72} animated={true} />
            </div>
          </div>

          <div style={{ fontFamily: "monospace", fontSize: 12, color: "#22c55e", letterSpacing: "0.2em", marginBottom: 20, textTransform: "uppercase" }}>
            BFV · MinHash · LSH
          </div>

          <h1 style={{ fontSize: "clamp(36px, 6vw, 72px)", fontWeight: 900, lineHeight: 1.05, marginBottom: 24, background: "linear-gradient(135deg, #f0fdf4 0%, #86efac 40%, #22c55e 70%, #15803d 100%)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
            Clusterisez sans<br />jamais déchiffrer
          </h1>

          <p style={{ fontSize: 18, color: "#94a3b8", lineHeight: 1.7, marginBottom: 48, maxWidth: 560, margin: "0 auto 48px" }}>
            CryptTraject chiffre vos données de géolocalisation localement et délègue le clustering de trajectoires à un serveur qui ne voit jamais les données en clair. Visualisez les clusters sur une carte, directement dans l'application. La clé secrète ne quitte jamais votre machine.
          </p>

          <div style={{ display: "flex", gap: 16, justifyContent: "center", flexWrap: "wrap" }}>
            <a href="#telecharger" style={{ padding: "14px 32px", background: "#16a34a", color: "#fff", textDecoration: "none", borderRadius: 8, fontWeight: 600, fontSize: 15, transition: "all 0.2s", border: "2px solid #22c55e" }}
              onMouseEnter={e => { e.target.style.background = "#15803d"; e.target.style.transform = "translateY(-2px)"; }}
              onMouseLeave={e => { e.target.style.background = "#16a34a"; e.target.style.transform = "translateY(0)"; }}>
              Installer l'application
            </a>
            <a href="#concept" style={{ padding: "14px 32px", background: "transparent", color: "#94a3b8", textDecoration: "none", borderRadius: 8, fontWeight: 500, fontSize: 15, border: "1px solid #1e3a5f", transition: "all 0.2s" }}
              onMouseEnter={e => { e.target.style.borderColor = "#22c55e44"; e.target.style.color = "#e2e8f0"; }}
              onMouseLeave={e => { e.target.style.borderColor = "#1e3a5f"; e.target.style.color = "#94a3b8"; }}>
              Comment ça marche
            </a>
          </div>
        </div>

        <div style={{ position: "absolute", bottom: 32, display: "flex", flexDirection: "column", alignItems: "center", gap: 6, color: "#334155", fontSize: 12 }}>
          <span>Défiler</span>
          <div style={{ width: 1, height: 40, background: "linear-gradient(#22c55e, transparent)", animation: "float 2s ease-in-out infinite" }} />
        </div>
      </section>

      {/* STATS */}
      <section style={{ padding: "80px 48px", borderTop: "1px solid #0f2337", borderBottom: "1px solid #0f2337", background: "#050d1a" }}>
        <div style={{ maxWidth: 900, margin: "0 auto", display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 40 }}>
          <StatPill value="0" label="Clé secrète sur le serveur" delay={0} />
          <StatPill value="BFV" label="Schéma homomorphe utilisé" delay={0.1} />
          <StatPill value="n=4096" label="Degré du polynôme (sec=128)" delay={0.2} />
          <StatPill value="128" label="Permutations MinHash" delay={0.3} />
        </div>
      </section>

      {/* CONCEPT */}
      <section id="concept" style={{ padding: "120px 48px", maxWidth: 1100, margin: "0 auto" }}>
        <FadeIn>
          <div style={{ fontFamily: "monospace", fontSize: 12, color: "#22c55e", letterSpacing: "0.2em", marginBottom: 16, textTransform: "uppercase" }}>01 — Principe</div>
          <h2 style={{ fontSize: "clamp(28px, 4vw, 52px)", fontWeight: 800, marginBottom: 24, lineHeight: 1.15 }}>
            Vos données restent <span style={{ color: "#22c55e" }}>les vôtres.</span><br />Même pendant le calcul.
          </h2>
        </FadeIn>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 64, alignItems: "center", marginTop: 60 }}>
          <FadeIn delay={0.1}>
            <p style={{ color: "#94a3b8", fontSize: 16, lineHeight: 1.8, marginBottom: 24 }}>
              Le chiffrement complètement homomorphe (FHE) permet d'opérer sur des ciphertexts comme s'ils étaient en clair. Avec le schéma <b>BFV</b>, additions et multiplications sont conservées modulo un entier.
            </p>
            <p style={{ color: "#94a3b8", fontSize: 16, lineHeight: 1.8 }}>
              L'application de bureau fait tout le travail sensible : parsing, MinHash, génération de clé, chiffrement, <b>déchiffrement et visualisation</b>. Le serveur reçoit uniquement le contexte BFV, la clé <b>publique</b>, et les signatures chiffrées. Il calcule des clusters sur les ciphertexts et vous renvoie le résultat, que vous seuls pouvez déchiffrer — et afficher sur une carte.
            </p>
          </FadeIn>
          <FadeIn delay={0.25}>
            <div style={{ background: "#050d1a", border: "1px solid #1e3a5f", borderRadius: 12, padding: "32px 24px" }}>
              <div style={{ fontSize: 13, color: "#64748b", fontFamily: "monospace", marginBottom: 20 }}>pipeline de traitement</div>
              <FlowDiagram />
              <div style={{ display: "flex", justifyContent: "space-between", marginTop: 12 }}>
                <span style={{ fontSize: 11, color: "#475569", fontFamily: "monospace" }}>CLIENT</span>
                <span style={{ fontSize: 11, color: "#475569", fontFamily: "monospace" }}>SERVEUR (aveugle)</span>
                <span style={{ fontSize: 11, color: "#475569", fontFamily: "monospace" }}>CLIENT</span>
              </div>
            </div>
          </FadeIn>
        </div>
      </section>

      {/* PIPELINE — anciennement SCHEMAS */}
      <section id="pipeline" style={{ padding: "120px 48px", background: "#050d1a", borderTop: "1px solid #0f2337" }}>
        <div style={{ maxWidth: 1100, margin: "0 auto" }}>
          <FadeIn>
            <div style={{ fontFamily: "monospace", fontSize: 12, color: "#22c55e", letterSpacing: "0.2em", marginBottom: 16, textTransform: "uppercase" }}>02 — Le pipeline en trois briques</div>
            <h2 style={{ fontSize: "clamp(28px, 4vw, 48px)", fontWeight: 800, marginBottom: 16 }}>Trois briques cryptographiques<br />pour un seul objectif</h2>
            <p style={{ color: "#64748b", fontSize: 16, marginBottom: 60, maxWidth: 600 }}>
              CryptTraject combine MinHash pour résumer les enregistrements, LSH pour identifier les paires proches, et BFV pour faire tout ça sur des données chiffrées. Chaque brique a un rôle précis.
            </p>
          </FadeIn>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 20 }}>
            <SchemaCard title="MinHash" tag="Côté client" accent="#22c55e"
              desc="Résume chaque enregistrement en une signature de taille fixe à partir d'un ensemble de tokens (geohash, n-grammes…)."
              features={["128 permutations par défaut", "Estimation Jaccard en O(1)", "Geohash pour trajectoires GPS", "Tokens texte pour CSV/JSON"]} />
            <SchemaCard title="BFV" tag="Sur le serveur" accent="#3b82f6"
              desc="Schéma Brakerski-Fan-Vercauteren via Pyfhel. Permet additions et multiplications sur ciphertexts entiers."
              features={["n = 4096, t = 65537, sec = 128", "Batching SIMD (2048 slots)", "Test d'égalité via (x−y)²", "Clé secrète exclusivement locale"]} />
            <SchemaCard title="LSH + Jaccard" tag="Bout en bout" accent="#8b5cf6"
              desc="Locality-Sensitive Hashing identifie les paires candidates, Union-Find assemble les clusters côté client après déchiffrement."
              features={["Bandes paramétrables (b × r)", "Seuil Jaccard configurable", "Union-Find avec compression", "Comparé à un baseline en clair"]} />
          </div>
        </div>
      </section>

      {/* WORKFLOW */}
      <section id="workflow" style={{ padding: "120px 48px" }}>
        <div style={{ maxWidth: 1100, margin: "0 auto" }}>
          <FadeIn>
            <div style={{ fontFamily: "monospace", fontSize: 12, color: "#22c55e", letterSpacing: "0.2em", marginBottom: 16, textTransform: "uppercase" }}>03 — Workflow</div>
            <h2 style={{ fontSize: "clamp(28px, 4vw, 48px)", fontWeight: 800, marginBottom: 60 }}>De vos fichiers aux clusters,<br />sans rien révéler</h2>
          </FadeIn>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 64, alignItems: "start" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 28 }}>
              {[
                { n: "01", t: "Choix de la source", d: "CSV, JSON, JSON-Lines ou trajectoires .plt Geolife. Vous choisissez la colonne d'identifiant et l'extracteur (geohash pour des points GPS, tokens pour du texte) directement dans l'application." },
                { n: "02", t: "MinHash + chiffrement BFV", d: "L'application calcule la signature MinHash de chaque enregistrement, génère une paire de clés BFV (n=4096, sec=128), et chiffre. La clé secrète est sauvegardée localement, jamais transmise." },
                { n: "03", t: "Upload + suivi de progression", d: "Les ciphertexts sont envoyés au serveur. L'interface affiche la progression étape par étape — chiffrement, transfert, temps de calcul serveur — avec un chrono en direct." },
                { n: "04", t: "Calcul homomorphe + Union-Find", d: "Le serveur calcule (sig_A − sig_B)² pour chaque paire et renvoie les ciphertexts. L'application déchiffre, applique le seuil de Jaccard et assemble les clusters via Union-Find." },
                { n: "05", t: "Visualisation sur carte", d: "Les clusters s'affichent dans une carte interactive : chaque trajectoire est colorée selon son cluster. Tout est déchiffré et tracé localement — le serveur n'a jamais vu vos données en clair. Export JSON disponible." },
              ].map(({ n, t, d }, i) => (
                <FadeIn key={n} delay={i * 0.1}>
                  <div style={{ display: "flex", gap: 20 }}>
                    <div style={{ fontFamily: "monospace", fontSize: 13, color: "#22c55e", opacity: 0.6, flexShrink: 0, paddingTop: 2 }}>{n}</div>
                    <div>
                      <div style={{ fontWeight: 600, fontSize: 16, marginBottom: 8, color: "#e2e8f0" }}>{t}</div>
                      <div style={{ color: "#64748b", fontSize: 14, lineHeight: 1.7 }}>{d}</div>
                    </div>
                  </div>
                </FadeIn>
              ))}
            </div>
            <FadeIn delay={0.2}>
              <TerminalBlock lines={[
                "# CryptTraject — déroulé d'une analyse",
                "  Source : Geolife/Data  ·  50 trajets",
                "  Serveur : crypttraject.rezel.net/api",
                "",
                "  ✓ Lecture + chiffrement local      1.8s",
                "    → 50 signatures MinHash, clé BFV générée",
                "  ✓ Envoi des signatures chiffrées   0.6s",
                "    → 50 ciphertexts envoyés au serveur",
                "  ⠹ Calcul serveur + déchiffrement   3.4s",
                "    → 1225 paires, déchiffrées localement",
                "",
                "  [carte]  7 clusters affichés",
                "           (seuil de Jaccard = 0.50)",
              ]} />
            </FadeIn>
          </div>
        </div>
      </section>

      {/* FORMATS */}
      <section style={{ padding: "80px 48px", background: "#050d1a", borderTop: "1px solid #0f2337" }}>
        <div style={{ maxWidth: 1100, margin: "0 auto" }}>
          <FadeIn>
            <div style={{ fontFamily: "monospace", fontSize: 12, color: "#22c55e", letterSpacing: "0.2em", marginBottom: 16, textTransform: "uppercase", textAlign: "center" }}>04 — Formats pris en charge</div>
            <p style={{ color: "#64748b", fontSize: 14, marginBottom: 48, maxWidth: 540, margin: "0 auto 48px", textAlign: "center" }}>
              Le système d'adaptateurs rend l'ingestion ouverte : ajouter un nouveau format = écrire une sous-classe de <code style={{ color: "#22c55e" }}>DataSourceAdapter</code>. Voici ce qui est embarqué de base.
            </p>
          </FadeIn>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, maxWidth: 880, margin: "0 auto" }}>
            {[
              { fmt: "CSV", detail: "Lignes plates ou groupées par id" },
              { fmt: "JSON", detail: "Tableau d'objets" },
              { fmt: "JSON-Lines", detail: "Un objet par ligne" },
              { fmt: ".plt", detail: "Trajectoires Geolife" },
            ].map(({ fmt, detail }, i) => (
              <FadeIn key={fmt} delay={i * 0.07}>
                <div style={{ background: "#0a1628", border: "1px solid #1e3a5f", borderRadius: 10, padding: "20px 12px", textAlign: "center", transition: "border-color 0.2s" }}
                  onMouseEnter={e => e.currentTarget.style.borderColor = "#22c55e44"}
                  onMouseLeave={e => e.currentTarget.style.borderColor = "#1e3a5f"}>
                  <div style={{ fontFamily: "monospace", fontWeight: 700, fontSize: 15, color: "#22c55e", marginBottom: 6 }}>{fmt}</div>
                  <div style={{ fontSize: 11, color: "#475569" }}>{detail}</div>
                </div>
              </FadeIn>
            ))}
          </div>
        </div>
      </section>

      {/* DOWNLOAD */}
      <section id="telecharger" style={{ padding: "140px 48px", position: "relative", overflow: "hidden" }}>
        <div style={{ position: "absolute", top: "50%", left: "50%", transform: "translate(-50%, -50%)", width: 600, height: 600, borderRadius: "50%", background: "radial-gradient(circle, #16653414 0%, transparent 70%)", pointerEvents: "none" }} />
        <div style={{ maxWidth: 720, margin: "0 auto", textAlign: "center", position: "relative" }}>
          <FadeIn>
            <div style={{ fontFamily: "monospace", fontSize: 12, color: "#22c55e", letterSpacing: "0.2em", marginBottom: 24, textTransform: "uppercase" }}>05 — Installation</div>
            <h2 style={{ fontSize: "clamp(32px, 5vw, 60px)", fontWeight: 900, lineHeight: 1.1, marginBottom: 20 }}>
              Prêt à chiffrer<br /><span style={{ color: "#22c55e" }}>vos données</span> ?
            </h2>
            <p style={{ color: "#64748b", fontSize: 16, lineHeight: 1.7, marginBottom: 56, maxWidth: 520, margin: "0 auto 56px" }}>
              Téléchargez l'installeur Windows : un double-clic installe l'application de bureau, rien d'autre à configurer. Importez vos données, suivez la progression du transfert, et visualisez les clusters sur une carte — le tout en local. La clé secrète est générée localement, jamais transmise.
            </p>

            <div style={{ marginBottom: 40 }}>
              <FadeIn delay={0.1}>
                <a href="https://github.com/tVelard/Crypttraject-Software/releases/latest/download/CryptTraject-Setup.exe"
                  style={{ display: "inline-block", minWidth: 300, background: "#0a1628", border: "1px solid #1e3a5f", borderRadius: 12, padding: "28px 40px", color: "inherit", textDecoration: "none", transition: "all 0.2s" }}
                  onMouseEnter={e => { e.currentTarget.style.borderColor = "#22c55e"; e.currentTarget.style.transform = "translateY(-4px)"; }}
                  onMouseLeave={e => { e.currentTarget.style.borderColor = "#1e3a5f"; e.currentTarget.style.transform = "translateY(0)"; }}>
                  <div style={{ fontSize: 32, marginBottom: 10 }}>⊞</div>
                  <div style={{ fontWeight: 700, fontSize: 18, color: "#e2e8f0", marginBottom: 4 }}>Windows</div>
                  <div style={{ fontSize: 12, color: "#475569" }}>x64 · application de bureau · ~180 MB</div>
                  <div style={{ fontSize: 10, color: "#22c55e", marginTop: 8, fontFamily: "monospace", textTransform: "uppercase", letterSpacing: "0.1em" }}>Télécharger l'installeur ↓</div>
                </a>
              </FadeIn>
            </div>

            <FadeIn delay={0.2}>
              <div style={{ fontFamily: "monospace", fontSize: 12, color: "#475569", marginBottom: 32 }}>
                Lancez <code style={{ color: "#22c55e" }}>CryptTraject-Setup.exe</code>, puis ouvrez <code style={{ color: "#22c55e" }}>CryptTraject</code> depuis le menu Démarrer.
              </div>
            </FadeIn>

            <FadeIn delay={0.25}>
              <details style={{ background: "#020810", border: "1px solid #1e3a5f", borderRadius: 10, padding: "16px 22px", textAlign: "left", marginBottom: 40 }}>
                <summary style={{ cursor: "pointer", fontFamily: "monospace", fontSize: 13, color: "#94a3b8" }}>
                  Ou depuis les sources (dev)
                </summary>
                <div style={{ fontFamily: "monospace", fontSize: 13, lineHeight: 1.9, marginTop: 14 }}>
                  <div style={{ color: "#64748b" }}># cloner</div>
                  <div><span style={{ color: "#22c55e" }}>$</span> git clone https://github.com/tVelard/Crypttraject-Software</div>
                  <div><span style={{ color: "#22c55e" }}>$</span> cd CryptTraject-Software</div>
                  <div style={{ color: "#64748b", marginTop: 12 }}># installer Python deps + dev install</div>
                  <div><span style={{ color: "#22c55e" }}>$</span> pip install -r requirements.txt && pip install -e .</div>
                  <div style={{ color: "#64748b", marginTop: 12 }}># lancer l'application de bureau</div>
                  <div><span style={{ color: "#22c55e" }}>$</span> python -m crypttraject_client.gui</div>
                  <div style={{ color: "#64748b", marginTop: 12 }}># ou en ligne de commande</div>
                  <div><span style={{ color: "#22c55e" }}>$</span> crypttraject-client --help</div>
                </div>
              </details>
            </FadeIn>

            <FadeIn delay={0.3}>
              <div style={{ fontFamily: "monospace", fontSize: 13, color: "#64748b", background: "#050d1a", border: "1px solid #1e3a5f", borderRadius: 8, padding: "12px 20px", display: "inline-block" }}>
                crypttraject v0.1.0 &nbsp;·&nbsp; Python 3.10+ &nbsp;·&nbsp; BFV via Pyfhel
              </div>
            </FadeIn>
          </FadeIn>
        </div>
      </section>

      {/* FOOTER */}
      <footer style={{ borderTop: "1px solid #0f2337", padding: "40px 48px", display: "flex", justifyContent: "space-between", alignItems: "center", background: "#030b18" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <LockIcon size={22} />
          <span style={{ fontFamily: "monospace", fontSize: 14, color: "#334155" }}>CryptTraject — projet intégrateur Télécom Paris 2A</span>
        </div>
        <div style={{ display: "flex", gap: 24, fontSize: 13, color: "#334155" }}>
          <a href="https://github.com" style={{ color: "#334155", textDecoration: "none" }}>GitHub</a>
          <a href="#concept" style={{ color: "#334155", textDecoration: "none" }}>Documentation</a>
          <a href="#telecharger" style={{ color: "#334155", textDecoration: "none" }}>Installation</a>
        </div>
      </footer>
    </div>
  );
}
