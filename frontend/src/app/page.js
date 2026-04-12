"use client";
import { useState, useEffect, useRef, useCallback } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/* ═══════════════════════════════════════
   SCROLL-REVEAL COMPONENT
   ═══════════════════════════════════════ */
function Reveal({ children, className = "", delay = 0, scale = false }) {
  const ref = useRef(null);
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([e]) => { if (e.isIntersecting) setVisible(true); },
      { threshold: 0.12 }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);
  const cls = scale ? "reveal--scale" : "reveal";
  return (
    <div
      ref={ref}
      className={`${cls} ${visible ? "in-view" : ""} ${className}`}
      data-delay={delay}
    >
      {children}
    </div>
  );
}

/* ═══════════════════════════════════════
   ANIMATED COUNTER
   ═══════════════════════════════════════ */
function Counter({ to, suffix = "", duration = 1800 }) {
  const ref = useRef(null);
  const [val, setVal] = useState(0);
  const [started, setStarted] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([e]) => { if (e.isIntersecting && !started) setStarted(true); },
      { threshold: 0.5 }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, [started]);
  useEffect(() => {
    if (!started) return;
    const start = Date.now();
    const tick = () => {
      const elapsed = Date.now() - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setVal(Math.round(eased * to));
      if (progress < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }, [started, to, duration]);
  return <span ref={ref}>{val}{suffix}</span>;
}

/* ═══════════════════════════════════════
   THREAT PARAMETERS DATA
   ═══════════════════════════════════════ */
const THREAT_PARAMS = [
  { name: "Identity Verification", desc: "Cross-checks recruiter identity against known databases and social profiles." },
  { name: "Company Registry Check", desc: "Verifies if the hiring company is registered with MCA/ROC." },
  { name: "Domain Age Analysis", desc: "Flags domains registered recently — a hallmark of phishing operations." },
  { name: "Financial Red Flags", desc: "Detects requests for upfront payments, processing fees, or bank details." },
  { name: "Pressure Tactics", desc: "Identifies urgency language designed to rush candidates into decisions." },
  { name: "Unrealistic Promises", desc: "Catches exaggerated salary claims and guaranteed placement offers." },
  { name: "Contact Method Audit", desc: "Flags usage of personal WhatsApp, Telegram, or non-corporate emails." },
  { name: "Language Manipulation", desc: "Detects emotional manipulation and deceptive language patterns." },
  { name: "Salary Benchmark", desc: "Compares offered salary against industry standards for the role." },
  { name: "Ghost Company Detection", desc: "Identifies shell companies with no verifiable online presence." },
  { name: "Emoji & Formatting", desc: "Excessive emojis and poor formatting correlate with scam listings." },
  { name: "Job Description Length", desc: "Unusually short or vague descriptions signal low-effort scam posts." },
  { name: "Skill Requirements", desc: "Missing or nonsensical requirements indicate fake postings." },
  { name: "Application Channel", desc: "Flags routing to external forms, Google Docs, or personal links." },
  { name: "Document Requests", desc: "Pre-interview requests for Aadhaar, PAN, or other ID documents." },
  { name: "Upfront Payment", desc: "Any request for money before employment is a critical red flag." },
  { name: "Guaranteed Selection", desc: "No legitimate employer guarantees selection before interviews." },
  { name: "Social Proof Check", desc: "Validates employee reviews and company ratings across platforms." },
  { name: "Location Verification", desc: "Confirms the listed office address exists and matches company records." },
  { name: "Historical Patterns", desc: "Matches listing against known scam templates and repeat offenders." },
];

/* ═══════════════════════════════════════
   MAIN COMPONENT
   ═══════════════════════════════════════ */
export default function Home() {
  /* ─── State ─── */
  const [entered, setEntered] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [jobs, setJobs] = useState([]);
  const [roles, setRoles] = useState([]);
  const [activeRole, setActiveRole] = useState(null);
  const [selectedJob, setSelectedJob] = useState(null);
  const [stats, setStats] = useState({ total: 0, safe: 0, risky: 0 });
  const [loading, setLoading] = useState(false);
  const [toolRevealed, setToolRevealed] = useState(false);
  const [dialIndex, setDialIndex] = useState(0);
  const [dialProgress, setDialProgress] = useState(0);
  const [dialRotation, setDialRotation] = useState(0);
  const [navDark, setNavDark] = useState(false);
  const [activeTab, setActiveTab] = useState('jobs'); // 'jobs' or 'internships'

  const toolRef = useRef(null);
  const dialRef = useRef(null);
  const introRef = useRef(null);

  /* ─── API Fetches ─── */
  useEffect(() => {
    fetch(`${API}/api/roles`).then(r => r.json()).then(setRoles).catch(() => {});
    fetch(`${API}/api/stats`).then(r => r.json()).then(setStats).catch(() => {});
  }, []);

  useEffect(() => {
    if (!toolRevealed) return;
    setLoading(true);
    const url = activeRole
      ? `${API}/api/jobs?role=${encodeURIComponent(activeRole)}`
      : `${API}/api/jobs`;
    fetch(url)
      .then(r => r.json())
      .then(data => { setJobs(data); setSelectedJob(data[0] || null); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [activeRole, toolRevealed]);

  /* ─── Tool reveal observer ─── */
  useEffect(() => {
    const el = toolRef.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([e]) => { if (e.isIntersecting) setToolRevealed(true); },
      { threshold: 0.1 }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  /* ─── Dial scroll listener (scroll-driven rotation) ─── */
  useEffect(() => {
    const onScroll = () => {
      const dialEl = dialRef.current;
      if (!dialEl) return;
      const rect = dialEl.getBoundingClientRect();
      const totalScroll = dialEl.offsetHeight - window.innerHeight;
      const scrolled = -rect.top;
      const progress = Math.max(0, Math.min(1, scrolled / totalScroll));
      setDialProgress(progress);

      // Full 360° rotation mapped to scroll
      setDialRotation(progress * 360);

      const idx = Math.min(
        THREAT_PARAMS.length - 1,
        Math.floor(progress * THREAT_PARAMS.length)
      );
      setDialIndex(idx);

      // Nav color logic — dark when on coral sections
      const introEl = introRef.current;
      if (introEl) {
        const introRect = introEl.getBoundingClientRect();
        setNavDark(introRect.bottom > 60);
      }
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  /* ─── Helper fns ─── */
  const si = (score) => {
    if (!score) return { cls: "", label: "N/A", color: "#6b6b6b" };
    const s = score.final_score;
    if (s >= 61) return { cls: "crit", label: "HIGH RISK", color: "#ef4444" };
    if (s >= 31) return { cls: "warn", label: "CAUTION", color: "#f59e0b" };
    return { cls: "safe", label: "LOW RISK", color: "#10b981" };
  };

  const verd = (score) => {
    if (!score) return null;
    const s = score.final_score;
    if (s >= 61) return { icon: "🚫", t: "AVOID", d: "Critical threat signals detected. Matches known scam patterns.", c: "text-red-400", bg: "verdict-crit" };
    if (s >= 31) return { icon: "⚠️", t: "CAUTION", d: "Some warning signals. Verify company independently.", c: "text-amber-400", bg: "verdict-warn" };
    return { icon: "✅", t: "LOOKS SAFE", d: "No major threats. Appears from a verified entity.", c: "text-emerald-400", bg: "verdict-safe" };
  };

  /* ─── Dial calculations ─── */
  const dialRadius = 220;
  const dialCenterX = 280;
  const dialCenterY = 280;

  const getDialPos = (index, total) => {
    // Evenly distribute items around the full circle
    const angle = ((2 * Math.PI) / total) * index - Math.PI / 2; // start from top
    return {
      x: dialCenterX + dialRadius * Math.cos(angle),
      y: dialCenterY + dialRadius * Math.sin(angle),
      angle,
    };
  };

  const handleEnter = () => {
    setEntered(true);
    setTimeout(() => {
      window.scrollTo({ top: window.innerHeight, behavior: "smooth" });
    }, 600);
  };

  return (
    <div className="page-wrapper">
      {/* ═══════════ NAVIGATION ═══════════ */}
      <nav className={`nav ${navDark && !entered ? "on-dark" : ""}`}>
        <a href="#" className="nav-logo" onClick={(e) => { e.preventDefault(); window.scrollTo({ top: 0, behavior: "smooth" }); }}>
          SHIELDDB<span className="nav-logo-sub">SAFE</span>
        </a>
        <button
          className={`nav-burger ${menuOpen ? "open" : ""}`}
          onClick={() => setMenuOpen(!menuOpen)}
          aria-label="Menu"
        >
          <span /><span /><span />
        </button>
      </nav>

      {/* Full-screen menu overlay */}
      <div className={`nav-overlay ${menuOpen ? "open" : ""}`}>
        <a href="#hook" onClick={() => setMenuOpen(false)}>The Problem</a>
        <a href="#dial" onClick={() => setMenuOpen(false)}>Threat Engine</a>
        <a href="#how" onClick={() => setMenuOpen(false)}>How It Works</a>
        <a href="#stats" onClick={() => setMenuOpen(false)}>Live Stats</a>
        <a href="#tool" onClick={() => setMenuOpen(false)}>Search Jobs</a>
      </div>

      {/* ═══════════ INTRO HERO ═══════════ */}
      <section
        ref={introRef}
        className={`intro ${entered ? "zoomed" : ""}`}
        id="intro"
      >
        {/* Geometric circle */}
        <div className="intro-circle" />
        <div className="intro-dot" />

        <div className="intro-title">
          <span className="intro-title-main">SHIELD</span>
          <span className="intro-title-sub">DB</span>
        </div>

        <button className="intro-cta" onClick={handleEnter}>
          Enter the experience
        </button>
      </section>

      {/* ═══════════ SCENE 2: THE HOOK ═══════════ */}
      <section className="section section--cream section--full" id="hook">
        <div className="section-inner">
          <div className="hook">
            <Reveal>
              <p className="label-sm label-sm--coral">The Problem</p>
            </Reveal>
            <Reveal delay={1}>
              <h2 className="heading-mega">
                Job scams cost Indians<br />
                <span className="accent">₹<Counter to={1000} suffix=" Cr+" /></span> every year
              </h2>
            </Reveal>
            <Reveal delay={2}>
              <p className="text-body" style={{ textAlign: "center", margin: "0 auto" }}>
                Every 14 seconds, someone falls victim. Fake recruiters exploit
                trust with sophisticated tactics that slip past traditional filters.
              </p>
            </Reveal>

            <div className="problem-row">
              <Reveal delay={2}>
                <div className="problem-card">
                  <div className="problem-icon">📧</div>
                  <h3 className="problem-stat"><Counter to={73} suffix="%" /></h3>
                  <p className="problem-desc">of scam listings use<br /><strong>fake email domains</strong></p>
                </div>
              </Reveal>
              <Reveal delay={3}>
                <div className="problem-card">
                  <div className="problem-icon">💸</div>
                  <h3 className="problem-stat"><Counter to={45} suffix="%" /></h3>
                  <p className="problem-desc">demand <strong>upfront fees</strong><br />for &quot;processing&quot;</p>
                </div>
              </Reveal>
              <Reveal delay={4}>
                <div className="problem-card">
                  <div className="problem-icon">🪪</div>
                  <h3 className="problem-stat"><Counter to={62} suffix="%" /></h3>
                  <p className="problem-desc">request <strong>Aadhaar/PAN</strong><br />before any interview</p>
                </div>
              </Reveal>
            </div>
          </div>
        </div>

        {/* Geo decoration removed */}
      </section>

      {/* ═══════════ SCENE 3: ROTATING DIAL ═══════════ */}
      <div className="dial-container" id="dial" ref={dialRef}>
        <div className="dial-sticky">
          {/* Left side label */}
          <div className="dial-label">THREAT ENGINE</div>

          {/* Scroll progress bar */}
          <div className="dial-progress">
            <div className="dial-progress-fill" style={{ height: `${dialProgress * 100}%` }} />
          </div>
          <div className="dial-progress-count">
            {String(dialIndex + 1).padStart(2, "0")}
            <span className="dial-progress-total">/{THREAT_PARAMS.length}</span>
          </div>

          {/* Rotating SVG container */}
          <div className="dial-arcs">
            {/* The entire wheel rotates on scroll */}
            <div
              className="dial-wheel"
              style={{ transform: `rotate(${dialRotation}deg)` }}
            >
              <svg viewBox="0 0 560 560" xmlns="http://www.w3.org/2000/svg">
                {/* Outer circle */}
                <circle cx="280" cy="280" r="220" className="dial-arc-circle" />
                {/* Inner circle */}
                <circle cx="280" cy="280" r="150" className="dial-arc-circle" />
                {/* Inner-inner circle */}
                <circle cx="280" cy="280" r="80" className="dial-arc-circle" />
                {/* Cross lines */}
                <line x1="0" y1="280" x2="560" y2="280" className="dial-arc-line" />
                <line x1="280" y1="0" x2="280" y2="560" className="dial-arc-line" />
                {/* Diagonal lines */}
                <line x1="60" y1="60" x2="500" y2="500" className="dial-arc-line" />
                <line x1="500" y1="60" x2="60" y2="500" className="dial-arc-line" />
                {/* Extra diagonals for denser look */}
                <line x1="140" y1="0" x2="420" y2="560" className="dial-arc-line" />
                <line x1="420" y1="0" x2="140" y2="560" className="dial-arc-line" />
              </svg>
            </div>

            {/* Text labels orbiting the circle (rotate independently) */}
            {THREAT_PARAMS.map((param, i) => {
              const pos = getDialPos(i, THREAT_PARAMS.length);
              const isActive = dialIndex === i;
              // Compute shortest distance around the circular array of length 20
              let distance = Math.abs(dialIndex - i);
              if (distance > THREAT_PARAMS.length / 2) {
                 distance = THREAT_PARAMS.length - distance;
              }
              const opacity = isActive ? 1 : distance <= 3 ? 0.6 : 0.35;
              return (
                <div
                  key={i}
                  className={`dial-orbit-item ${isActive ? "active" : ""}`}
                  style={{
                    left: `${((pos.x / 560) * 100).toFixed(4)}%`,
                    top: `${((pos.y / 560) * 100).toFixed(4)}%`,
                    opacity,
                  }}
                >
                  <span className="dial-orbit-num">{String(i + 1).padStart(2, "0")}</span>
                  {isActive && <span className="dial-orbit-name">{param.name}</span>}
                </div>
              );
            })}

            {/* Glowing active dot */}
            {(() => {
              const pos = getDialPos(dialIndex, THREAT_PARAMS.length);
              return (
                <div
                  className="dial-dot"
                  style={{
                    left: `${((pos.x / 560) * 100).toFixed(4)}%`,
                    top: `${((pos.y / 560) * 100).toFixed(4)}%`,
                  }}
                />
              );
            })()}
          </div>

          {/* Right side content — cross-fade */}
          <div className="dial-content">
            <div className="dial-content-num">
              {String(dialIndex + 1).padStart(2, "0")}
            </div>
            <div className="dial-content-anim" key={dialIndex}>
              <h3 className="dial-content-title">
                {THREAT_PARAMS[dialIndex].name}
              </h3>
              <p className="dial-content-desc">
                {THREAT_PARAMS[dialIndex].desc}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* ═══════════ SCENE 4: HOW IT WORKS ═══════════ */}
      <section className="section section--cream section--full" id="how">
        <div className="section-inner">
          <div className="steps-section">
            <Reveal>
              <p className="label-sm label-sm--coral" style={{ textAlign: "center" }}>How It Works</p>
              <h2 className="heading-lg" style={{ textAlign: "center" }}>
                Three steps. Zero guesswork.
              </h2>
            </Reveal>

            <div className="steps-grid">
              <Reveal delay={1}>
                <div className="step-card">
                  <div className="step-num">01</div>
                  <h3 className="step-title">Extract</h3>
                  <p className="step-desc">We use our secure browser extension to seamlessly aggregate listings directly from Naukri.</p>
                </div>
              </Reveal>
              <Reveal delay={2}>
                <div className="step-card">
                  <div className="step-num">02</div>
                  <h3 className="step-title">Score</h3>
                  <p className="step-desc">Each listing is scored against 20 heuristic parameters — from domain age to pressure language.</p>
                </div>
              </Reveal>
              <Reveal delay={3}>
                <div className="step-card">
                  <div className="step-num">03</div>
                  <h3 className="step-title">Shield</h3>
                  <p className="step-desc">You see only verified results. Scams are flagged, warnings are explained, safe jobs are highlighted.</p>
                </div>
              </Reveal>
            </div>
          </div>
        </div>
      </section>

      {/* ═══════════ SCENE 5: STATS (CORAL) ═══════════ */}
      <section className="section section--coral section--full" id="stats">
        <div className="section-inner">
          <div className="stats-section">
            <Reveal>
              <p className="label-sm label-sm--light" style={{ textAlign: "center" }}>Live Database</p>
              <h2 className="heading-mega heading-mega--light" style={{ textAlign: "center" }}>
                Already protecting<br />job seekers.
              </h2>
            </Reveal>

            <div className="stats-row">
              <Reveal delay={1}>
                <div className="big-stat">
                  <span className="big-stat-num"><Counter to={stats.total} /></span>
                  <span className="big-stat-label">Jobs Scanned</span>
                </div>
              </Reveal>
              <Reveal delay={2}>
                <div className="big-stat">
                  <span className="big-stat-num stat-safe"><Counter to={stats.safe} /></span>
                  <span className="big-stat-label">Verified Safe</span>
                </div>
              </Reveal>
              <Reveal delay={3}>
                <div className="big-stat">
                  <span className="big-stat-num stat-danger"><Counter to={stats.risky} /></span>
                  <span className="big-stat-label">Flagged Risky</span>
                </div>
              </Reveal>
              <Reveal delay={4}>
                <div className="big-stat">
                  <span className="big-stat-num stat-blue"><Counter to={roles.length} /></span>
                  <span className="big-stat-label">Roles Covered</span>
                </div>
              </Reveal>
            </div>
          </div>
        </div>
      </section>

      {/* ═══════════ CTA ═══════════ */}
      <section className="section section--coral section--full">
        <div className="cta-section">
          <Reveal>
            <p className="label-sm label-sm--light" style={{ textAlign: "center" }}>Protect Yourself</p>
            <h2 className="heading-mega heading-mega--light" style={{ textAlign: "center" }}>
              Build what&apos;s next.<br />
              <span className="accent">Safely.</span>
            </h2>
          </Reveal>
          <Reveal delay={2}>
            <a href="#tool" className="cta-btn">Search Safe Jobs</a>
          </Reveal>
        </div>
      </section>

      {/* ═══════════ SCENE 6: JOB TOOL ═══════════ */}
      <section className="section section--cream" id="tool" ref={toolRef}>
        <div className="section-inner">
          <div className="tool-section">
            <div className="tool-header">
              <Reveal>
                <p className="label-sm label-sm--coral">Try It Now</p>
                <h2 className="heading-lg" style={{ textAlign: "center" }}>
                  Find your next safe job.
                </h2>
                <p className="text-body" style={{ textAlign: "center", margin: "16px auto 0" }}>
                  Choose a position. See every listing scored in real time.
                </p>
              </Reveal>
            </div>

            <Reveal delay={1}>
              <div className="tool-controls">
                <div className="tool-tabs">
                  <button className={`tool-tab ${activeTab === 'jobs' ? 'active' : ''}`} onClick={() => setActiveTab('jobs')}>Jobs</button>
                  <button className={`tool-tab ${activeTab === 'internships' ? 'active' : ''}`} onClick={() => setActiveTab('internships')}>Internships</button>
                </div>
                <div className="tool-filter">
                  <div className="select-wrap">
                    <select
                      className="hero-select"
                      value={activeRole || ""}
                      onChange={(e) => setActiveRole(e.target.value || null)}
                    >
                      <option value="">All Positions ({stats.total} listings)</option>
                      {roles.map(r => <option key={r} value={r}>{r}</option>)}
                    </select>
                    <div className="select-chevron">
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="6 9 12 15 18 9"/></svg>
                    </div>
                  </div>
                </div>
              </div>
            </Reveal>

            {toolRevealed && (
              <>
                {loading ? (
                  <div className="empty-state">Loading...</div>
                ) : (() => {
                    const filteredJobs = jobs.filter(job => {
                      const isIntern = job.title.toLowerCase().includes('intern') || (job.role && job.role.toLowerCase().includes('intern'));
                      return activeTab === 'internships' ? isIntern : !isIntern;
                    });
                    
                    return filteredJobs.length === 0 ? (
                      <div className="empty-state">No {activeTab} found for this position.</div>
                    ) : (
                      <Reveal delay={2}>
                        <div className="results-grid">
                          {/* List */}
                          <div className="job-list custom-scrollbar">
                            <p className="list-count">{filteredJobs.length} results · safest first</p>
                            {filteredJobs.map((job) => {
                          const info = si(job.score);
                          const active = selectedJob?.id === job.id;
                          return (
                            <div key={job.id} onClick={() => setSelectedJob(job)} className={`job-card ${active ? "job-card-active" : ""}`}>
                              <div className="job-card-inner">
                                <div className={`score-pill ${info.cls}`}>
                                  {job.score ? `${Math.round(job.score.final_score)}%` : "—"}
                                </div>
                                <div className="job-card-text">
                                  <p className="job-card-title">{job.title}</p>
                                  <p className="job-card-company">{job.company}</p>
                                </div>
                                <span className="job-card-risk" style={{ color: info.color }}>{info.label}</span>
                              </div>
                            </div>
                          );
                        })}
                      </div>

                      {/* Detail */}
                      <div className="detail-col">
                        {selectedJob ? (
                          <div className="detail-panel">
                            <div className="detail-header">
                              <div className="detail-header-text">
                                <h2 className="detail-title">{selectedJob.title}</h2>
                                <div className="detail-meta">
                                  <span className="detail-company">{selectedJob.company}</span>
                                  {selectedJob.role && <span className="detail-role-badge">{selectedJob.role}</span>}
                                  {selectedJob.url && <a href={selectedJob.url} target="_blank" rel="noreferrer" className="detail-link">View Original ↗</a>}
                                </div>
                              </div>
                              {selectedJob.score && (() => {
                                const info = si(selectedJob.score);
                                return (
                                  <div className="detail-score-wrap">
                                    <div className={`score-pill big ${info.cls}`}>{Math.round(selectedJob.score.final_score)}%</div>
                                    <span className="detail-score-label">Scam Score</span>
                                  </div>
                                );
                              })()}
                            </div>
                            {selectedJob.score && (
                              <div className="detail-body">
                                {(() => {
                                  const v = verd(selectedJob.score);
                                  if (!v) return null;
                                  return (
                                    <div className={`verdict ${v.bg}`}>
                                      <span className="verdict-icon">{v.icon}</span>
                                      <div>
                                        <p className={`verdict-title ${v.c}`}>{v.t}</p>
                                        <p className="verdict-desc">{v.d}</p>
                                      </div>
                                    </div>
                                  );
                                })()}
                                <div>
                                  <h4 className="signals-heading">Threat Signals ({selectedJob.score.flags.length})</h4>
                                  <div className="signals-list">
                                    {selectedJob.score.flags.map((raw, i) => {
                                      let sev = "warn", lbl = "WARN", text = raw;
                                      if (raw.startsWith("CRIT:")) { sev = "crit"; lbl = "CRIT"; text = raw.slice(6); }
                                      else if (raw.startsWith("SAFE:")) { sev = "safe"; lbl = "SAFE"; text = raw.slice(6); }
                                      else if (raw.startsWith("WARN:")) { text = raw.slice(6); }
                                      return (
                                        <div key={i} className={`flag flag-${sev}`}>
                                          <span className="flag-badge">{lbl}</span>
                                          <span className="flag-text">{text}</span>
                                        </div>
                                      );
                                    })}
                                    {selectedJob.score.flags.length === 0 && (
                                      <div className="flag flag-safe" style={{ justifyContent: "center" }}>✓ No threats detected</div>
                                    )}
                                  </div>
                                </div>
                              </div>
                            )}
                          </div>
                        ) : null}
                      </div>
                    </div>
                  </Reveal>
                );
                })()}
              </>
            )}
          </div>
        </div>
      </section>

      {/* ═══════════ FOOTER ═══════════ */}
      <footer className="site-footer">
        <p>ShieldDB — Built to protect job seekers.</p>
      </footer>
    </div>
  );
}
