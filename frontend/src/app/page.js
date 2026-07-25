"use client";
import { useState, useEffect, useRef, useCallback } from "react";
import { useAuth } from "@/lib/auth";
import { supabase } from "@/lib/supabase";

const API = process.env.NEXT_PUBLIC_API_URL || "";

function dedupeJobs(list) {
  const seen = new Set();
  return list.filter((job) => {
    if (seen.has(job.id)) return false;
    seen.add(job.id);
    return true;
  });
}

function normalizeBaseRole(role) {
  if (!role) return role;
  let r = role.trim();
  r = r.replace(/\s[-–]\s*(intern(ship)?|trainee|apprentice)\s*$/i, "").trim();
  const low = r.toLowerCase();
  for (const suffix of [" internship", " intern", " trainee", " apprentice"]) {
    if (low.endsWith(suffix)) return r.slice(0, -suffix.length).trim();
  }
  return r;
}

function sortJobsByRecency(list) {
  return [...list].sort((a, b) => {
    const postedA = a.posted_date || "";
    const postedB = b.posted_date || "";
    if (postedA !== postedB) return postedB.localeCompare(postedA);
    const createdA = a.created_at || "";
    const createdB = b.created_at || "";
    if (createdA !== createdB) return createdB.localeCompare(createdA);
    return (b.id || 0) - (a.id || 0);
  });
}

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
  const { user } = useAuth();
  const [entered, setEntered] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [jobs, setJobs] = useState([]);
  const [roles, setRoles] = useState([]);
  const [locations, setLocations] = useState([]);
  const [activeRole, setActiveRole] = useState(null);
  const [activeLocation, setActiveLocation] = useState(null);
  const [selectedJob, setSelectedJob] = useState(null);
  const [stats, setStats] = useState({ total: 0, safe: 0, caution: 0, risky: 0 });
  const [loading, setLoading] = useState(false);
  const [toolRevealed, setToolRevealed] = useState(false);
  const [dialIndex, setDialIndex] = useState(0);
  const [dialProgress, setDialProgress] = useState(0);
  const [dialRotation, setDialRotation] = useState(0);
  const [navDark, setNavDark] = useState(false);
  const [viewMode, setViewMode] = useState('threat'); // 'threat' or 'insights'
  const [allJobs, setAllJobs] = useState([]);
  const [insightsRole, setInsightsRole] = useState("");
  const [insightsCity, setInsightsCity] = useState("");
  const [activeTab, setActiveTab] = useState('jobs'); // 'jobs' or 'internships'
  const [searchQuery, setSearchQuery] = useState('');
  const [interactions, setInteractions] = useState({});
  const [dashRole, setDashRole] = useState('');
  const [dashLocation, setDashLocation] = useState('');
  const [dashSearch, setDashSearch] = useState('');
  const [dashSelectedJob, setDashSelectedJob] = useState(null);
  const [dashAppliedJobs, setDashAppliedJobs] = useState([]);
  const [helpMsg, setHelpMsg] = useState('');
  const [helpLoading, setHelpLoading] = useState(false);
  const [helpSuccess, setHelpSuccess] = useState(false);

  const toolRef = useRef(null);
  const dialRef = useRef(null);
  const introRef = useRef(null);
  const jobsOffsetRef = useRef(0);

  /* ─── API Fetches ─── */
  const [hasMore, setHasMore] = useState(true);
  const PAGE_SIZE = 100;

  useEffect(() => {
    fetch(`${API}/api/roles`).then(r => r.json()).then(d => setRoles(Array.isArray(d) ? d : [])).catch(() => { });
    fetch(`${API}/api/locations`).then(r => r.json()).then(d => setLocations(Array.isArray(d) ? d : [])).catch(() => { });
    fetch(`${API}/api/stats`).then(r => r.json()).then(d => setStats(d && typeof d === "object" ? d : { total: 0, safe: 0, caution: 0, risky: 0 })).catch(() => { });
    fetch(`${API}/api/jobs?limit=10000`).then(r => r.json()).then((data) => setAllJobs(dedupeJobs(Array.isArray(data) ? data : []))).catch(() => { });
  }, []);

  // Re-fetch all jobs + stats when switching to insights so new scraped data always appears
  useEffect(() => {
    if (viewMode === 'insights') {
      fetch(`${API}/api/jobs?limit=10000`).then(r => r.json()).then((data) => setAllJobs(dedupeJobs(Array.isArray(data) ? data : []))).catch(() => { });
      fetch(`${API}/api/stats`).then(r => r.json()).then(d => setStats(d && typeof d === "object" ? d : { total: 0, safe: 0, caution: 0, risky: 0 })).catch(() => { });
    }
    if (viewMode === 'dashboard' && !user) setViewMode('threat');
    if (viewMode === 'help' && !user) setViewMode('threat');
  }, [viewMode, user]);

  // Fetch user interactions when logged in
  useEffect(() => {
    if (!user) { setInteractions({}); return; }
    console.log("[ShieldDB] Fetching interactions for user:", user.id);
    fetch(`${API}/api/interactions?user_id=${encodeURIComponent(user.id)}`)
      .then(r => r.ok ? r.json() : [])
      .then((data) => {
        const list = Array.isArray(data) ? data : [];
        console.log("[ShieldDB] Interactions loaded:", list.length, "records");
        const map = {};
        list.forEach(i => { map[i.job_id] = i; });
        setInteractions(map);
      })
      .catch(() => { });
  }, [user]);

  useEffect(() => {
    if (!user || viewMode !== 'dashboard') return;
    console.log("[ShieldDB] Fetching applied jobs for dashboard, user_id:", user.id);
    fetch(`${API}/api/interactions/applied?user_id=${encodeURIComponent(user.id)}`)
      .then(r => r.ok ? r.json() : [])
      .then((data) => {
        const jobs = Array.isArray(data) ? data : [];
        console.log("[ShieldDB] Dashboard: loaded", jobs.length, "applied jobs");
        setDashAppliedJobs(jobs);
      })
      .catch(() => setDashAppliedJobs([]));
  }, [user, viewMode, interactions]);

  const dashJobs = dashAppliedJobs.filter(job => {
    const interaction = interactions[job.id];
    if (!interaction?.applied) return false;
    if (interaction.rejected) return false;
    const q = dashSearch.toLowerCase();
    const textMatch = !q || job.title.toLowerCase().includes(q) || job.company.toLowerCase().includes(q) || (job.location && job.location.toLowerCase().includes(q));
    const roleMatch = !dashRole || normalizeBaseRole(job.role) === dashRole;
    const locMatch = !dashLocation || (job.location && job.location.toLowerCase().includes(dashLocation.toLowerCase()));
    return textMatch && roleMatch && locMatch;
  });

  useEffect(() => {
    if (dashSelectedJob && !dashJobs.some(j => j.id === dashSelectedJob.id)) {
      setDashSelectedJob(dashJobs[0] || null);
    }
  }, [dashJobs, dashSelectedJob]);

  const toggleApplied = async (jobId) => {
    if (!user) {
      console.warn("[ShieldDB] toggleApplied: no user logged in");
      return;
    }
    const current = interactions[jobId];
    const newVal = !(current?.applied);
    console.log(`[ShieldDB] toggleApplied: job_id=${jobId}, user_id=${user.id}, new_value=${newVal}`);

    setInteractions(prev => ({
      ...prev,
      [jobId]: { ...prev[jobId], job_id: jobId, applied: newVal, rejected: prev[jobId]?.rejected || false },
    }));

    try {
      const res = await fetch(`${API}/api/interactions?user_id=${encodeURIComponent(user.id)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_id: jobId, applied: newVal }),
      });
      if (!res.ok) {
        const errText = await res.text();
        console.error(`[ShieldDB] toggleApplied failed: HTTP ${res.status}`, errText);
        setInteractions(prev => ({ ...prev, [jobId]: current }));
        return;
      }
      const data = await res.json();
      console.log("[ShieldDB] toggleApplied saved:", data);
      setInteractions(prev => ({ ...prev, [jobId]: data }));
    } catch (e) {
      console.error("[ShieldDB] toggleApplied network error:", e);
      setInteractions(prev => ({ ...prev, [jobId]: current }));
    }
  };

  const toggleRejected = async (jobId) => {
    if (!user) {
      console.warn("[ShieldDB] toggleRejected: no user logged in");
      return;
    }
    const current = interactions[jobId];
    const newVal = !(current?.rejected);
    console.log(`[ShieldDB] toggleRejected: job_id=${jobId}, user_id=${user.id}, new_value=${newVal}`);

    setInteractions(prev => ({
      ...prev,
      [jobId]: { ...prev[jobId], job_id: jobId, rejected: newVal, applied: prev[jobId]?.applied || false },
    }));

    try {
      const res = await fetch(`${API}/api/interactions?user_id=${encodeURIComponent(user.id)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_id: jobId, rejected: newVal }),
      });
      if (!res.ok) {
        const errText = await res.text();
        console.error(`[ShieldDB] toggleRejected failed: HTTP ${res.status}`, errText);
        setInteractions(prev => ({ ...prev, [jobId]: current }));
        return;
      }
      const data = await res.json();
      console.log("[ShieldDB] toggleRejected saved:", data);
      setInteractions(prev => ({ ...prev, [jobId]: data }));
    } catch (e) {
      console.error("[ShieldDB] toggleRejected network error:", e);
      setInteractions(prev => ({ ...prev, [jobId]: current }));
    }
  };

  // Pre-fetch jobs immediately and on filter changes
  const fetchJobs = useCallback((reset = true) => {
    setLoading(true);
    const params = new URLSearchParams();
    if (activeRole) params.set('role', activeRole);
    if (activeLocation) params.set('location', activeLocation);
    if (activeTab === 'internships') {
      params.set('job_type', 'Internship');
    } else {
      params.set('exclude_job_type', 'Internship');
    }
    params.set('limit', String(PAGE_SIZE));
    if (reset) jobsOffsetRef.current = 0;
    const currentOffset = jobsOffsetRef.current;
    params.set('offset', String(currentOffset));
    fetch(`${API}/api/jobs?${params.toString()}`)
      .then(r => r.json())
      .then(data => {
        const batch = Array.isArray(data) ? data : [];
        const newJobs = sortJobsByRecency(dedupeJobs(reset ? batch : [...jobs, ...batch]));
        jobsOffsetRef.current = reset ? batch.length : jobsOffsetRef.current + batch.length;
        setJobs(newJobs);
        setHasMore(batch.length === PAGE_SIZE);
        if (reset) setSelectedJob(newJobs[0] || null);
      })
      .catch(() => { })
      .finally(() => setLoading(false));
  }, [activeRole, activeLocation, activeTab, jobs]);

  // Fetch on mount + when filters or tab change
  useEffect(() => {
    fetchJobs(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeRole, activeLocation, activeTab]);

  /* ─── Tool reveal: show job results when the tool section is in view or user is filtering ─── */
  useEffect(() => {
    const el = toolRef.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([e]) => { if (e.isIntersecting) setToolRevealed(true); },
      { threshold: 0.05, rootMargin: "200px 0px" }
    );
    obs.observe(el);
    if (window.location.hash === "#tool") setToolRevealed(true);
    return () => obs.disconnect();
  }, []);

  // Show results as soon as user picks a filter (don't wait for scroll)
  useEffect(() => {
    if (activeRole || activeLocation || jobs.length > 0 || loading) {
      setToolRevealed(true);
    }
  }, [activeRole, activeLocation, jobs.length, loading]);

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

  /* ─── Salary parsing and insights computations ─── */
  const parseSalary = (salaryStr) => {
    if (!salaryStr || salaryStr.toLowerCase().includes("not disclosed")) return null;
    let str = salaryStr.replace(/,/g, '').toLowerCase();

    let matches = str.match(/(\d+\.?\d*)/g);
    if (!matches) return null;
    let numbers = matches.map(n => parseFloat(n)).filter(n => !isNaN(n));
    if (numbers.length === 0) return null;
    let value = numbers.length > 1 ? (numbers[0] + numbers[1]) / 2 : numbers[0];

    let hasLakh = /\d\s*l(?![a-ik-z])/i.test(str) || str.includes("lpa") || str.includes("lakh");

    if (hasLakh || str.includes("p.a") || str.includes("per annum") || str.includes("annum")) {
      value = value * 100000;
    } else if (str.includes("pm") || str.includes("per month") || str.includes("/month") || str.includes("monthly")) {
      value = value * 12;
    } else if (value < 100) {
      value = value * 100000;
    }
    return value;
  };

  // Derive unique clean city names that have at least one job (from all jobs, not just filtered)
  const CITIES_MAP = [
    "Mumbai", "Bangalore", "Bengaluru", "Delhi", "Hyderabad", "Ahmedabad", "Chennai", "Kolkata", "Pune",
    "Gurgaon", "Gurugram", "Noida", "Faridabad", "Ghaziabad", "Jaipur", "Lucknow", "Nagpur", "Indore",
    "Thane", "Bhopal", "Patna", "Vadodara", "Agra", "Nashik", "Rajkot", "Varanasi", "Amritsar",
    "Dehradun", "Kochi", "Chandigarh", "Guwahati", "Mysore", "Bhubaneswar", "Coimbatore", "Vijayawada",
    "Jodhpur", "Raipur", "Shimla", "Panaji", "Goa", "Pondicherry", "Puducherry", "Surat", "Visakhapatnam",
    "Mangalore", "Hubli", "Aurangabad",
  ];
  const extractCity = (raw) => {
    if (!raw) return null;
    const lower = raw.toLowerCase();
    if (lower.includes("remote") || lower.includes("work from home") || lower.includes("wfh")) return "Remote";
    for (const city of CITIES_MAP) {
      if (lower.includes(city.toLowerCase())) return city === "Bengaluru" ? "Bangalore" : city;
    }
    const first = raw.split(/[,|/]/)[0].trim();
    return first && first.length <= 40 ? first : null;
  };
  const insightsCitiesSet = new Set();
  allJobs.forEach(job => { const c = extractCity(job.location); if (c) insightsCitiesSet.add(c); });
  const insightsCities = Array.from(insightsCitiesSet).sort();

  const dashRoles = [...new Set(dashAppliedJobs.filter(j => interactions[j.id]?.applied && !interactions[j.id]?.rejected).map(j => normalizeBaseRole(j.role)).filter(Boolean))].sort();
  const dashLocations = [...new Set(dashAppliedJobs.filter(j => interactions[j.id]?.applied && !interactions[j.id]?.rejected).map(j => extractCity(j.location)).filter(Boolean))].sort();

  // Filtered jobs for Insights Dashboard
  const filteredInsightsJobs = allJobs.filter(job => {
    const roleMatch = !insightsRole || normalizeBaseRole(job.role) === insightsRole;
    const cityMatch = !insightsCity || (job.location && job.location.toLowerCase().includes(insightsCity.toLowerCase()));
    return roleMatch && cityMatch;
  });

  // Calculate Median & Top Salaries by Role
  const roleSalaries = {};
  filteredInsightsJobs.forEach(job => {
    const sal = parseSalary(job.salary);
    const baseRole = normalizeBaseRole(job.role);
    if (sal && baseRole) {
      if (!roleSalaries[baseRole]) {
        roleSalaries[baseRole] = [];
      }
      roleSalaries[baseRole].push(sal);
    }
  });

  const salaryDataByRole = Object.keys(roleSalaries).map(role => {
    const sals = roleSalaries[role].sort((a, b) => a - b);
    const top = sals[sals.length - 1];
    const mid = Math.floor(sals.length / 2);
    const median = sals.length % 2 !== 0 ? sals[mid] : (sals[mid - 1] + sals[mid]) / 2;
    return { role, median, top };
  }).sort((a, b) => b.median - a.median);

  // Job Distribution by Job Type
  const jobTypeCounts = { "Full Time": 0, "Part Time": 0, "Internship": 0 };
  filteredInsightsJobs.forEach(job => {
    if (job.job_type && jobTypeCounts[job.job_type] !== undefined) {
      jobTypeCounts[job.job_type]++;
    }
  });
  const jobTypeData = Object.keys(jobTypeCounts).map(type => ({
    type,
    count: jobTypeCounts[type]
  }));

  // Top Skills — filter out generic non-skill words
  const SKILL_BLACKLIST = new Set([
    "analysis", "analytics", "analyst", "business", "management", "manager", "developer", "engineer",
    "engineering", "development", "designing", "associate", "executive", "coordinator", "consultant",
    "consulting", "senior", "junior", "lead", "head", "intern", "internship", "trainee", "support",
    "service", "services", "operations", "operating", "requirement", "requirements",
    "requirement gathering", "documentation", "hiring", "urgent", "immediate", "opening", "openings",
    "freshers", "fresher", "experienced", "years", "experience", "work from home", "wfh", "remote",
    "hybrid", "onsite", "full time", "part time", "salary", "ctc", "lpa", "package", "data",
    "information", "system", "systems", "solution", "solutions", "technology", "technologies",
    "technical", "market", "sales", "research", "testing", "implementation", "integration",
    "deployment", "delivery", "client", "customer", "vendor", "stakeholder", "product", "project",
    "program", "quality", "performance", "optimization", "improvement", "strategy", "strategic",
    "planning", "process", "reporting", "report", "presentation", "good", "strong", "excellent",
    "ability", "understanding", "knowledge", "candidate", "profile", "job", "role", "position",
    "company", "team", "department", "accounting", "backend development", "business analysis", "business analytics",
    "data analysis", "data analytics", "content writing", "cyber security", "analytical", "front end", "frontend development",
    "graphic designing", "network engineering", "product management", "project management", "system administration", "translation", "video editing", "adobe",
    "quality analysis",

  ]);
  const toTitleCase = (s) => s.replace(/\w\S*/g, w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase());

  const isRoleVariant = (skillLower, roleLower) => {
    if (!roleLower) return false;
    const roleWords = roleLower.split(/\s+/);
    const skillWords = skillLower.split(/\s+/);
    if (skillLower === roleLower) return true;
    if (skillWords.length >= roleWords.length) return false;
    const stemOf = (w) => w.replace(/(?:ing|tion|ics|ous|ive|al|ly|ment|ence|ance|ist|ery|ity)$/, '');
    const roleStems = roleWords.map(stemOf);
    const skillStems = skillWords.map(stemOf);
    if (skillStems.length > roleStems.length) return false;
    return skillStems.every((ss, i) => roleStems.some(rs => ss === rs || rs.startsWith(ss) || ss.startsWith(rs)));
  };

  const skillCounts = {};
  filteredInsightsJobs.forEach(job => {
    if (job.skills && Array.isArray(job.skills)) {
      const roleLower = (job.role || '').toLowerCase();
      job.skills.forEach(skill => {
        const trimmed = skill.trim();
        if (!trimmed) return;
        const lower = trimmed.toLowerCase();
        if (SKILL_BLACKLIST.has(lower)) return;
        if (isRoleVariant(lower, roleLower)) return;
        const normalized = toTitleCase(trimmed);
        skillCounts[normalized] = (skillCounts[normalized] || 0) + 1;
      });
    }
  });
  const topSkillsData = Object.keys(skillCounts)
    .map(skill => ({ skill, count: skillCounts[skill] }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 8);

  // KPIs
  const totalListings = filteredInsightsJobs.length;
  const parsedSalaries = filteredInsightsJobs.map(j => parseSalary(j.salary)).filter(s => s !== null);
  const avgSalary = parsedSalaries.length > 0 ? parsedSalaries.reduce((a, b) => a + b, 0) / parsedSalaries.length : 0;
  const topPayingRole = salaryDataByRole.length > 0 ? salaryDataByRole[0] : null;

  // Salary-ranked job list (shown when a role is selected)
  const jobsWithSalary = filteredInsightsJobs
    .map(j => ({ ...j, _sal: parseSalary(j.salary) }))
    .filter(j => j._sal !== null)
    .sort((a, b) => b._sal - a._sal);
  const medianSal = (() => {
    const sals = jobsWithSalary.map(j => j._sal).sort((a, b) => a - b);
    if (!sals.length) return 0;
    const mid = Math.floor(sals.length / 2);
    return sals.length % 2 !== 0 ? sals[mid] : (sals[mid - 1] + sals[mid]) / 2;
  })();
  // Representative job at (or nearest to) the median salary
  const medianJob = (() => {
    if (!jobsWithSalary.length) return null;
    const sortedAsc = [...jobsWithSalary].sort((a, b) => a._sal - b._sal);
    const midIdx = Math.floor(sortedAsc.length / 2);
    return sortedAsc.length % 2 !== 0 ? sortedAsc[midIdx] : sortedAsc[midIdx - 1];
  })();
  // Keep jobs from max salary down to median (inclusive), always including the median listing
  const salaryRankedJobs = (() => {
    const ranked = jobsWithSalary.filter(j => j._sal >= medianSal);
    if (medianJob && !ranked.some(j => j.id === medianJob.id)) {
      ranked.push(medianJob);
      ranked.sort((a, b) => b._sal - a._sal);
    }
    return ranked;
  })();


  return (
    <div className="page-wrapper">
      {/* ═══════════ NAVIGATION ═══════════ */}
      <nav className={`nav ${navDark && !entered ? "on-dark" : ""}`}>
        <a href="#" className="nav-logo" onClick={(e) => { e.preventDefault(); window.scrollTo({ top: 0, behavior: "smooth" }); }}>
          SHIELDDB<span className="nav-logo-sub">SAFE</span>
        </a>
        <div className="nav-tabs">
          <button className={`nav-tab-btn ${viewMode === 'threat' ? 'active' : ''}`} onClick={() => setViewMode('threat')}>Threat Scanner</button>
          <button className={`nav-tab-btn ${viewMode === 'insights' ? 'active' : ''}`} onClick={() => setViewMode('insights')}>Data Insights</button>
          {user && (
            <button className={`nav-tab-btn ${viewMode === 'dashboard' ? 'active' : ''}`} onClick={() => setViewMode('dashboard')}>Dashboard</button>
          )}
          {viewMode === 'threat' && (
            <a href="#tool" className="nav-tab-btn" onClick={(e) => { e.preventDefault(); document.getElementById('tool')?.scrollIntoView({ behavior: 'smooth' }); }}>Search Jobs</a>
          )}
          {user && (
            <button className={`nav-tab-btn ${viewMode === 'help' ? 'active' : ''}`} onClick={() => setViewMode('help')}>Help</button>
          )}
          {user ? (
            <button className="nav-tab-btn" onClick={async () => { const { supabase } = await import("@/lib/supabase"); supabase.auth.signOut(); }} style={{ marginLeft: 'auto' }}>Log Out</button>
          ) : (
            <a href="/login" className="nav-tab-btn" style={{ marginLeft: 'auto' }}>Log In</a>
          )}
        </div>
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
        <a href="#" onClick={(e) => { e.preventDefault(); setViewMode('threat'); setMenuOpen(false); }}>Threat Scanner</a>
        <a href="#" onClick={(e) => { e.preventDefault(); setViewMode('insights'); setMenuOpen(false); }}>Data Insights</a>
        {user && (
          <a href="#" onClick={(e) => { e.preventDefault(); setViewMode('dashboard'); setMenuOpen(false); }}>Dashboard</a>
        )}
        {viewMode === 'threat' && (
          <>
            <a href="#tool" onClick={() => setMenuOpen(false)}>Search Jobs</a>
          </>
        )}
        {user && (
          <a href="#" onClick={(e) => { e.preventDefault(); setViewMode('help'); setMenuOpen(false); }}>Help</a>
        )}
        {user ? (
          <a href="#" onClick={async (e) => { e.preventDefault(); const { supabase } = await import("@/lib/supabase"); supabase.auth.signOut(); setMenuOpen(false); }}>Log Out</a>
        ) : (
          <a href="/login" onClick={() => setMenuOpen(false)}>Log In</a>
        )}
      </div>

      {viewMode === 'threat' && (
        <>
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
                      <div className="problem-icon">
                        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="20" height="16" x="2" y="4" rx="2" /><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" /></svg>
                      </div>
                      <h3 className="problem-stat"><Counter to={73} suffix="%" /></h3>
                      <p className="problem-desc">of scam listings use<br /><strong>fake email domains</strong></p>
                    </div>
                  </Reveal>
                  <Reveal delay={3}>
                    <div className="problem-card">
                      <div className="problem-icon">
                        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="20" height="12" x="2" y="6" rx="2" /><circle cx="12" cy="12" r="2" /><path d="M6 12h.01M18 12h.01" /></svg>
                      </div>
                      <h3 className="problem-stat"><Counter to={45} suffix="%" /></h3>
                      <p className="problem-desc">demand <strong>upfront fees</strong><br />for &quot;processing&quot;</p>
                    </div>
                  </Reveal>
                  <Reveal delay={4}>
                    <div className="problem-card">
                      <div className="problem-icon">
                        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M16 2H8a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2Z" /><circle cx="12" cy="8" r="2" /><path d="M15 13a3 3 0 0 0-6 0" /></svg>
                      </div>
                      <h3 className="problem-stat"><Counter to={62} suffix="%" /></h3>
                      <p className="problem-desc">request <strong>Aadhaar/PAN</strong><br />before any interview</p>
                    </div>
                  </Reveal>
                </div>
              </div>
            </div>
          </section>

          {/* ═══════════ SCENE 3: ROTATING DIAL ═══════════ */}
          <div className="dial-container" id="dial" ref={dialRef}>
            <div className="dial-sticky">
              <div className="dial-label">THREAT ENGINE</div>

              <div className="dial-progress">
                <div className="dial-progress-fill" style={{ height: `${dialProgress * 100}%` }} />
              </div>
              <div className="dial-progress-count">
                {String(dialIndex + 1).padStart(2, "0")}
                <span className="dial-progress-total">/{THREAT_PARAMS.length}</span>
              </div>

              <div className="dial-arcs">
                <div
                  className="dial-wheel"
                  style={{ transform: `rotate(${dialRotation}deg)` }}
                >
                  <svg viewBox="0 0 560 560" xmlns="http://www.w3.org/2000/svg">
                    <circle cx="280" cy="280" r="220" className="dial-arc-circle" />
                    <circle cx="280" cy="280" r="150" className="dial-arc-circle" />
                    <circle cx="280" cy="280" r="80" className="dial-arc-circle" />
                    <line x1="0" y1="280" x2="560" y2="280" className="dial-arc-line" />
                    <line x1="280" y1="0" x2="280" y2="560" className="dial-arc-line" />
                    <line x1="60" y1="60" x2="500" y2="500" className="dial-arc-line" />
                    <line x1="500" y1="60" x2="60" y2="500" className="dial-arc-line" />
                    <line x1="140" y1="0" x2="420" y2="560" className="dial-arc-line" />
                    <line x1="420" y1="0" x2="140" y2="560" className="dial-arc-line" />
                  </svg>
                </div>

                {THREAT_PARAMS.map((param, i) => {
                  const pos = getDialPos(i, THREAT_PARAMS.length);
                  const isActive = dialIndex === i;
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
                      <span className="big-stat-num" style={{ color: "#f59e0b" }}><Counter to={stats.caution || 0} /></span>
                      <span className="big-stat-label">Caution (Verify)</span>
                    </div>
                  </Reveal>
                  <Reveal delay={4}>
                    <div className="big-stat">
                      <span className="big-stat-num stat-danger"><Counter to={stats.risky} /></span>
                      <span className="big-stat-label">Flagged Risky</span>
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
                  <div className="toolbar-row">
                    <div className="tool-tabs">
                      <button className={`tool-tab ${activeTab === 'jobs' ? 'active' : ''}`} onClick={() => setActiveTab('jobs')}>Jobs</button>
                      <button className={`tool-tab ${activeTab === 'internships' ? 'active' : ''}`} onClick={() => setActiveTab('internships')}>Internships</button>
                    </div>
                    <div className="select-wrap">
                      <span className="select-label">Position:</span>
                      <select
                        className="hero-select"
                        value={activeRole || ""}
                        onChange={(e) => setActiveRole(e.target.value || null)}
                      >
                        <option value="">All Positions ({stats.total} listings)</option>
                        {roles.map(r => <option key={r} value={r}>{r}</option>)}
                      </select>
                      <div className="select-chevron">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="6 9 12 15 18 9" /></svg>
                      </div>
                    </div>
                    <div className="select-wrap">
                      <span className="select-label">Location:</span>
                      <select
                        className="hero-select"
                        value={activeLocation || ""}
                        onChange={(e) => setActiveLocation(e.target.value || null)}
                      >
                        <option value="">All Locations</option>
                        {locations.map(loc => <option key={loc} value={loc}>{loc}</option>)}
                      </select>
                      <div className="select-chevron">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="6 9 12 15 18 9" /></svg>
                      </div>
                    </div>
                    <div className="search-wrap">
                      <svg className="search-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
                      <input type="text" className="search-input" placeholder="Search jobs..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} />
                    </div>
                  </div>
                </Reveal>

                {(toolRevealed || activeRole || activeLocation || jobs.length > 0 || loading) && (
                  <>
                    {loading && jobs.length === 0 ? (
                      <div className="empty-state">Loading...</div>
                    ) : (() => {
                      const query = searchQuery.toLowerCase();
                      const filteredJobs = sortJobsByRecency(jobs.filter(job => {
                        const textMatch = job.title.toLowerCase().includes(query) || job.company.toLowerCase().includes(query) || (job.location && job.location.toLowerCase().includes(query));
                        return textMatch;
                      }));

                      return filteredJobs.length === 0 ? (
                        <div className="empty-state">No {activeTab} found for this position matching your search.</div>
                      ) : (
                        <Reveal delay={2}>
                          <h3 className="job-list-heading">Verified Roles <span className="job-list-count">({filteredJobs.length} listings)</span></h3>
                          <div className="results-grid">
                            <div className="job-list-col">
                              <div className="job-list custom-scrollbar">
                                {filteredJobs.map((job) => {
                                  const info = si(job.score);
                                  const active = selectedJob?.id === job.id;
                                  return (
                                    <div key={job.id} onClick={() => setSelectedJob(job)} className={`job-card ${active ? "job-card-active" : ""}`}>
                                      <div className="job-card-inner">
                                        <div className={`score-ring ${info.cls}`}>
                                          <span className="score-num">{job.score ? `${Math.round(job.score.final_score)}%` : "—"}</span>
                                        </div>
                                        <div className="job-card-text">
                                          <p className="job-card-title">{job.title}</p>
                                          <p className="job-card-company">{job.company}{job.location && <span className="job-card-location"> · 📍 {job.location}</span>}</p>
                                        </div>
                                        <div className={`job-card-badge badge-${info.cls}`}>
                                          {info.label}
                                        </div>
                                        {user && interactions[job.id]?.applied && (
                                          <span style={{ fontSize: '0.7rem', fontWeight: 700, color: '#10b981', marginLeft: '4px' }}>✓</span>
                                        )}
                                      </div>
                                    </div>
                                  );
                                })}
                              </div>
                              {hasMore && (
                                <button className="load-more-btn" onClick={() => fetchJobs(false)} disabled={loading}>
                                  {loading ? 'Loading...' : 'Load More Jobs'}
                                </button>
                              )}
                            </div>

                            <div className="detail-col">
                              {selectedJob ? (
                                <div className="detail-panel">
                                  <div className="detail-header">
                                    <div className="detail-header-text">
                                      <h2 className="detail-title">{selectedJob.title}</h2>
                                      <div className="detail-meta">
                                        <span className="detail-company">{selectedJob.company}</span>
                                        {selectedJob.location && <span className="detail-location-badge">📍 {selectedJob.location}</span>}
                                        {selectedJob.url && <a href={selectedJob.url} target="_blank" rel="noreferrer" className="detail-link">View Original ↗</a>}
                                      </div>
                                    </div>
                                    {selectedJob.score && (() => {
                                      const info = si(selectedJob.score);
                                      return (
                                        <div className="detail-score-wrap">
                                          <div className={`score-ring big ${info.cls}`}><span className="score-num">{Math.round(selectedJob.score.final_score)}%</span></div>
                                          <span className="detail-score-label" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>SCAM SCORE <span style={{ fontSize: '0.7rem' }}>?</span></span>
                                        </div>
                                      );
                                    })()}
                                  </div>
                                  {user && selectedJob && (
                                    <div style={{ display: 'flex', gap: '8px', marginTop: '12px' }}>
                                      <button
                                        className={`interaction-btn interaction-btn--apply ${interactions[selectedJob.id]?.applied ? 'active' : ''}`}
                                        onClick={(e) => { e.stopPropagation(); toggleApplied(selectedJob.id); }}
                                      >
                                        {interactions[selectedJob.id]?.applied ? '✓ Applied' : 'Mark as Applied'}
                                      </button>
                                      <button
                                        className={`interaction-btn interaction-btn--reject ${interactions[selectedJob.id]?.rejected ? 'active' : ''}`}
                                        onClick={(e) => { e.stopPropagation(); toggleRejected(selectedJob.id); }}
                                      >
                                        {interactions[selectedJob.id]?.rejected ? '✗ Rejected' : 'Reject'}
                                      </button>
                                    </div>
                                  )}
                                  {selectedJob.description && (
                                    <div className="detail-description">
                                      {selectedJob.description}
                                    </div>
                                  )}
                                  {selectedJob.score && (
                                    <div className="detail-body">
                                      {(() => {
                                        const v = verd(selectedJob.score);
                                        if (!v) return null;
                                        return (
                                          <div className={`verdict-glass ${v.bg}`}>
                                            <div className={`verdict-glass-icon ${v.bg}-icon`}>{v.icon}</div>
                                            <div>
                                              <p className={`verdict-glass-title ${v.c}`}>{v.t}</p>
                                              <p className="verdict-glass-desc">{v.d}</p>
                                            </div>
                                          </div>
                                        );
                                      })()}
                                      <div>
                                        <h4 className="signals-heading">THREAT SIGNALS ({selectedJob.score.flags.length})</h4>
                                        <div className="signals-list">
                                          {selectedJob.score.flags.map((raw, i) => {
                                            let sev = "warn", lbl = "WARN", text = raw;
                                            if (raw.startsWith("CRIT:")) { sev = "crit"; lbl = "CRIT"; text = raw.slice(6); }
                                            else if (raw.startsWith("SAFE:")) { sev = "safe"; lbl = "SAFE"; text = raw.slice(6); }
                                            else if (raw.startsWith("WARN:")) { text = raw.slice(6); }
                                            return (
                                              <div key={i} className={`flag-pill flag-${sev}`}>
                                                <span className="flag-badge">{lbl}</span>
                                                <span className="flag-text">{text}</span>
                                              </div>
                                            );
                                          })}
                                          {selectedJob.score.flags.length === 0 && (
                                            <div className="flag-pill flag-safe">
                                              <span className="flag-badge">SAFE</span>
                                              <span className="flag-text">Verified globally as {selectedJob.company}</span>
                                            </div>
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
        </>
      )}

      {viewMode === 'insights' && (
        <section className="insights-section">
          <div className="insights-header">
            <h1 className="insights-title">Job Market Insights</h1>
            <p className="insights-subtitle">Real-time salary benchmarking, distributions, and top demanded skills in India</p>
          </div>

          {/* Slicers */}
          <div className="slicers-card">
            <div className="slicers-title">Slicers & Filters</div>
            <div className="slicers-grid">
              <div className="slicer-field">
                <span className="slicer-label">Job Role</span>
                <div className="slicer-select-wrap">
                  <select className="slicer-select" value={insightsRole} onChange={(e) => setInsightsRole(e.target.value)}>
                    <option value="">All Roles ({roles.length} roles)</option>
                    {roles.map(r => <option key={r} value={r}>{r}</option>)}
                  </select>
                  <div className="slicer-chevron">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="6 9 12 15 18 9" /></svg>
                  </div>
                </div>
              </div>
              <div className="slicer-field">
                <span className="slicer-label">City</span>
                <div className="slicer-select-wrap">
                  <select className="slicer-select" value={insightsCity} onChange={(e) => setInsightsCity(e.target.value)}>
                    <option value="">All Cities ({insightsCities.length} cities)</option>
                    {insightsCities.map(loc => <option key={loc} value={loc}>{loc}</option>)}
                  </select>
                  <div className="slicer-chevron">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="6 9 12 15 18 9" /></svg>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* KPIs */}
          <div className="kpi-row">
            <div className="kpi-card">
              <span className="kpi-label">Analyzed Listings</span>
              <span className="kpi-val">{totalListings}</span>
              <span className="kpi-desc">Total job postings in target segment</span>
            </div>
            <div className="kpi-card">
              <span className="kpi-label">Avg Annual Salary</span>
              <span className="kpi-val" style={{ color: 'var(--coral)' }}>
                {avgSalary > 0 ? `₹${Math.round(avgSalary / 100000).toFixed(1)}L` : '—'}
              </span>
              <span className="kpi-desc">Based on parsed compensation figures</span>
            </div>
            <div className="kpi-card">
              <span className="kpi-label">Top Paying Role</span>
              <span className="kpi-val" style={{ color: '#10b981', fontSize: '1.25rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', minHeight: '38px', display: 'flex', alignItems: 'center' }}>
                {topPayingRole ? topPayingRole.role : 'N/A'}
              </span>
              <span className="kpi-desc">
                {topPayingRole ? `Median: ₹${Math.round(topPayingRole.median / 100000).toFixed(1)}L PA` : 'No salary data'}
              </span>
            </div>
          </div>

          {/* Charts Grid */}
          <div className="charts-grid">
            {/* Median Salaries */}
            <div className="chart-card">
              <div className="chart-card-header">
                <h3 className="chart-title">Median Salary by Job Role</h3>
                <p className="chart-desc">Annual median salary values in INR (derived from parsed listings)</p>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                {salaryDataByRole.length === 0 ? (
                  <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>No salary data available. Try broadening your filter.</div>
                ) : (
                  salaryDataByRole.slice(0, 5).map((item, idx) => {
                    const maxVal = salaryDataByRole[0]?.median || 1;
                    const pct = Math.max(10, Math.min(100, (item.median / maxVal) * 100));
                    return (
                      <div key={idx} style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', fontWeight: '600' }}>
                          <span>{item.role}</span>
                          <span style={{ color: 'var(--coral)' }}>₹{Math.round(item.median).toLocaleString()}</span>
                        </div>
                        <div style={{ height: '24px', background: 'rgba(0,0,0,0.03)', borderRadius: '6px', overflow: 'hidden' }}>
                          <div style={{ width: `${pct}%`, height: '100%', background: 'linear-gradient(90deg, var(--coral), #ff8a75)', borderRadius: '6px', transition: 'width 0.6s ease' }} />
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>

            {/* Top Salaries */}
            <div className="chart-card">
              <div className="chart-card-header">
                <h3 className="chart-title">Top Salaries by Job Role</h3>
                <p className="chart-desc">Maximum salary offered for different enterprise positions</p>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                {salaryDataByRole.length === 0 ? (
                  <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>No salary data available. Try broadening your filter.</div>
                ) : (
                  salaryDataByRole.slice(0, 5).map((item, idx) => {
                    const maxVal = Math.max(...salaryDataByRole.map(d => d.top)) || 1;
                    const pct = Math.max(10, Math.min(100, (item.top / maxVal) * 100));
                    return (
                      <div key={idx} style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', fontWeight: '600' }}>
                          <span>{item.role}</span>
                          <span style={{ color: '#10b981' }}>₹{Math.round(item.top).toLocaleString()}</span>
                        </div>
                        <div style={{ height: '24px', background: 'rgba(0,0,0,0.03)', borderRadius: '6px', overflow: 'hidden' }}>
                          <div style={{ width: `${pct}%`, height: '100%', background: 'linear-gradient(90deg, #10b981, #6ee7b7)', borderRadius: '6px', transition: 'width 0.6s ease' }} />
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>

            {/* Job Types Count */}
            <div className="chart-card">
              <div className="chart-card-header">
                <h3 className="chart-title">Job Distribution by Job Type</h3>
                <p className="chart-desc">Breakdown of roles between Full Time, Part Time, and Internships</p>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                {jobTypeData.map((item, idx) => {
                  const maxVal = Math.max(...jobTypeData.map(d => d.count)) || 1;
                  const pct = Math.max(5, Math.min(100, (item.count / maxVal) * 100));
                  return (
                    <div key={idx} style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', fontWeight: '600' }}>
                        <span>{item.type}</span>
                        <span style={{ color: '#3b82f6' }}>{item.count} jobs</span>
                      </div>
                      <div style={{ height: '24px', background: 'rgba(0,0,0,0.03)', borderRadius: '6px', overflow: 'hidden' }}>
                        <div style={{ width: `${pct}%`, height: '100%', background: 'linear-gradient(90deg, #3b82f6, #93c5fd)', borderRadius: '6px', transition: 'width 0.6s ease' }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Top Skills */}
            <div className="chart-card">
              <div className="chart-card-header">
                <h3 className="chart-title">Top In-Demand Skills</h3>
                <p className="chart-desc">Frequency of technical keywords extracted from current job descriptions</p>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {topSkillsData.length === 0 ? (
                  <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>No skill tags indexed yet. Run the scraper to populate.</div>
                ) : (
                  topSkillsData.map((item, idx) => {
                    const maxVal = topSkillsData[0]?.count || 1;
                    const pct = Math.max(10, Math.min(100, (item.count / maxVal) * 100));
                    return (
                      <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <div style={{ width: '120px', fontSize: '0.75rem', fontWeight: '600', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {item.skill}
                        </div>
                        <div style={{ flex: 1, height: '16px', background: 'rgba(0,0,0,0.03)', borderRadius: '4px', overflow: 'hidden' }}>
                          <div style={{ width: `${pct}%`, height: '100%', background: 'linear-gradient(90deg, #8b5cf6, #c084fc)', borderRadius: '4px', transition: 'width 0.6s ease' }} />
                        </div>
                        <div style={{ width: '40px', fontSize: '0.75rem', fontWeight: '700', color: '#8b5cf6', textAlign: 'right' }}>
                          {item.count}
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          </div>

          {/* ── Salary-Ranked Job List (only when a role is selected) ── */}
          {insightsRole && (
            <div className="chart-card" style={{ marginTop: '0' }}>
              <div className="chart-card-header">
                <h3 className="chart-title">
                  💰 Top-Paying {insightsRole} Listings
                </h3>
                <p className="chart-desc">
                  Jobs ranked from highest to median salary
                  {insightsCity ? ` in ${insightsCity}` : ''} — {salaryRankedJobs.length} listing{salaryRankedJobs.length !== 1 ? 's' : ''} with disclosed salary
                </p>
              </div>
              {salaryRankedJobs.length === 0 ? (
                <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', padding: '12px 0' }}>
                  No salary data available for the selected filters. Try scraping more jobs for this role.
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {salaryRankedJobs.map((job, idx) => {
                    const salLPA = (job._sal / 100000).toFixed(1);
                    const isTop = idx === 0;
                    const isMedianEntry = medianJob && job.id === medianJob.id;
                    return (
                      <a
                        key={job.id || idx}
                        href={job.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{
                          display: 'flex', alignItems: 'center', gap: '14px',
                          padding: '12px 16px',
                          background: isTop
                            ? 'linear-gradient(135deg, rgba(251,191,36,0.12), rgba(251,191,36,0.04))'
                            : 'rgba(0,0,0,0.02)',
                          border: isTop
                            ? '1px solid rgba(251,191,36,0.35)'
                            : '1px solid rgba(0,0,0,0.06)',
                          borderRadius: '10px', textDecoration: 'none',
                          color: 'inherit', transition: 'all 0.2s ease', cursor: 'pointer',
                        }}
                        onMouseEnter={e => { e.currentTarget.style.transform = 'translateX(4px)'; e.currentTarget.style.boxShadow = '0 4px 16px rgba(0,0,0,0.08)'; }}
                        onMouseLeave={e => { e.currentTarget.style.transform = 'translateX(0)'; e.currentTarget.style.boxShadow = 'none'; }}
                      >
                        {/* Rank badge */}
                        <div style={{
                          minWidth: '34px', height: '34px', borderRadius: '50%',
                          background: isTop
                            ? 'linear-gradient(135deg, #fbbf24, #f59e0b)'
                            : isMedianEntry
                              ? 'linear-gradient(135deg, #6366f1, #8b5cf6)'
                              : 'rgba(0,0,0,0.07)',
                          color: (isTop || isMedianEntry) ? '#fff' : 'var(--text-muted)',
                          display: 'flex', alignItems: 'center', justifyContent: 'center',
                          fontSize: '0.7rem', fontWeight: '800', flexShrink: 0,
                        }}>
                          {isMedianEntry && !isTop ? '~' : `#${idx + 1}`}
                        </div>

                        {/* Job info */}
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{
                            fontSize: '0.88rem', fontWeight: '700',
                            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                          }}>
                            {job.title}
                            {isMedianEntry && (
                              <span style={{ marginLeft: '8px', fontSize: '0.68rem', fontWeight: '700', color: '#6366f1', background: 'rgba(99,102,241,0.1)', padding: '2px 8px', borderRadius: '10px' }}>
                                Median
                              </span>
                            )}
                          </div>
                          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                            {job.company}{job.location ? ` · ${job.location}` : ''}
                            {job.workplace_type ? ` · ${job.workplace_type}` : ''}
                          </div>
                        </div>

                        {/* Salary badge */}
                        <div style={{
                          fontSize: '0.85rem', fontWeight: '800', whiteSpace: 'nowrap',
                          color: isTop ? '#f59e0b' : '#10b981',
                          background: isTop ? 'rgba(251,191,36,0.1)' : 'rgba(16,185,129,0.08)',
                          padding: '4px 12px', borderRadius: '20px', flexShrink: 0,
                        }}>
                          ₹{salLPA}L
                        </div>

                        {/* Arrow */}
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
                          stroke="currentColor" strokeWidth="2.5"
                          style={{ opacity: 0.3, flexShrink: 0 }}>
                          <polyline points="9 18 15 12 9 6" />
                        </svg>
                      </a>
                    );
                  })}

                  {/* Median marker */}
                  <div style={{
                    display: 'flex', alignItems: 'center', gap: '10px',
                    padding: '8px 16px', marginTop: '4px',
                    background: 'rgba(99,102,241,0.06)',
                    border: '1px dashed rgba(99,102,241,0.3)',
                    borderRadius: '8px', fontSize: '0.78rem', color: '#6366f1',
                  }}>
                    <span style={{ fontWeight: '800' }}>~ Median</span>
                    <span>
                      ₹{(medianSal / 100000).toFixed(1)}L
                      {medianJob ? ` · ${medianJob.title} at ${medianJob.company}` : ''}
                      · Jobs below this salary are not listed
                    </span>
                  </div>
                </div>
              )}
            </div>
          )}
        </section>
      )}

      {viewMode === 'dashboard' && user && (
        <section className="insights-section">
          <div className="insights-header">
            <h1 className="insights-title">Your Dashboard</h1>
            <p className="insights-subtitle">Jobs you&apos;ve marked as applied — filter and track your applications</p>
          </div>

          <div className="slicers-card">
            <div className="slicers-title">Filters</div>
            <div className="slicers-grid">
              <div className="slicer-field">
                <label className="slicer-label">Position</label>
                <select className="slicer-select" value={dashRole} onChange={(e) => setDashRole(e.target.value)}>
                  <option value="">All Positions ({dashRoles.length})</option>
                  {dashRoles.map(r => <option key={r} value={r}>{r}</option>)}
                </select>
              </div>
              <div className="slicer-field">
                <label className="slicer-label">Location</label>
                <select className="slicer-select" value={dashLocation} onChange={(e) => setDashLocation(e.target.value)}>
                  <option value="">All Locations ({dashLocations.length})</option>
                  {dashLocations.map(loc => <option key={loc} value={loc}>{loc}</option>)}
                </select>
              </div>
              <div className="slicer-field">
                <label className="slicer-label">Search</label>
                <div className="search-wrap" style={{ maxWidth: '100%' }}>
                  <svg className="search-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
                  <input type="text" className="search-input" placeholder="Search applied jobs..." value={dashSearch} onChange={(e) => setDashSearch(e.target.value)} />
                </div>
              </div>
            </div>
          </div>

          <div style={{ padding: '0 32px', marginTop: '24px' }}>
            {dashAppliedJobs.filter(j => interactions[j.id]?.applied && !interactions[j.id]?.rejected).length === 0 ? (
              <div className="chart-card" style={{ textAlign: 'center', padding: '48px 24px' }}>
                <p style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-muted)' }}>You haven&apos;t applied to any jobs yet!</p>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '8px' }}>Head over to Search Jobs, find listings you like, and mark them as applied.</p>
                <button className="nav-tab-btn" style={{ marginTop: '16px', background: 'rgba(225,90,68,0.08)', color: 'var(--coral)' }} onClick={() => setViewMode('threat')}>Go to Search Jobs</button>
              </div>
            ) : dashJobs.length === 0 ? (
              <div className="chart-card" style={{ textAlign: 'center', padding: '48px 24px' }}>
                <p style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-muted)' }}>No applied jobs match your current filters</p>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '8px' }}>Try adjusting your search or filter criteria.</p>
                <button className="nav-tab-btn" style={{ marginTop: '16px', background: 'rgba(0,0,0,0.04)' }} onClick={() => { setDashSearch(''); setDashRole(''); setDashLocation(''); }}>Clear Filters</button>
              </div>
            ) : (
              <div className="results-grid">
                <div className="job-list-col">
                  <div className="job-list custom-scrollbar">
                    {dashJobs.map((job) => {
                      const info = si(job.score);
                      const active = dashSelectedJob?.id === job.id;
                      return (
                        <div key={job.id} onClick={() => setDashSelectedJob(job)} className={`job-card ${active ? "job-card-active" : ""}`}>
                          <div className="job-card-inner">
                            <div className={`score-ring ${info.cls}`}>
                              <span className="score-num">{job.score ? `${Math.round(job.score.final_score)}%` : "—"}</span>
                            </div>
                            <div className="job-card-text">
                              <p className="job-card-title">{job.title}</p>
                              <p className="job-card-company">{job.company}{job.location && <span className="job-card-location"> · 📍 {job.location}</span>}</p>
                            </div>
                            <div className={`job-card-badge badge-${info.cls}`}>
                              {info.label}
                            </div>
                            <span style={{ fontSize: '0.7rem', fontWeight: 700, color: '#10b981', marginLeft: '4px' }}>✓</span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
                <div className="detail-col">
                  {dashSelectedJob ? (
                    <div className="detail-panel">
                      <div className="detail-header">
                        <div className="detail-header-text">
                          <h2 className="detail-title">{dashSelectedJob.title}</h2>
                          <div className="detail-meta">
                            <span className="detail-company">{dashSelectedJob.company}</span>
                            {dashSelectedJob.location && <span className="detail-location-badge">📍 {dashSelectedJob.location}</span>}
                            {dashSelectedJob.url && <a href={dashSelectedJob.url} target="_blank" rel="noreferrer" className="detail-link">View Original ↗</a>}
                          </div>
                        </div>
                        {dashSelectedJob.score && (() => {
                          const info = si(dashSelectedJob.score);
                          return (
                            <div className="detail-score-wrap">
                              <div className={`score-ring big ${info.cls}`}><span className="score-num">{Math.round(dashSelectedJob.score.final_score)}%</span></div>
                              <span className="detail-score-label">SCAM SCORE</span>
                            </div>
                          );
                        })()}
                      </div>
                      <div style={{ display: 'flex', gap: '8px', marginTop: '12px' }}>
                        <button
                          className={`interaction-btn interaction-btn--apply ${interactions[dashSelectedJob.id]?.applied ? 'active' : ''}`}
                          onClick={() => toggleApplied(dashSelectedJob.id)}
                        >
                          {interactions[dashSelectedJob.id]?.applied ? '✓ Applied' : 'Mark as Applied'}
                        </button>
                        <button
                          className={`interaction-btn interaction-btn--reject ${interactions[dashSelectedJob.id]?.rejected ? 'active' : ''}`}
                          onClick={() => toggleRejected(dashSelectedJob.id)}
                        >
                          {interactions[dashSelectedJob.id]?.rejected ? '✗ Rejected' : 'Reject'}
                        </button>
                      </div>
                      {dashSelectedJob.description && (
                        <div className="detail-description">{dashSelectedJob.description}</div>
                      )}
                      {dashSelectedJob.score && (
                        <div className="detail-body">
                          <div>
                            <h4 className="signals-heading">THREAT SIGNALS ({dashSelectedJob.score.flags.length})</h4>
                            <div className="signals-list">
                              {dashSelectedJob.score.flags.map((raw, i) => {
                                let sev = "warn", lbl = "WARN", text = raw;
                                if (raw.startsWith("CRIT:")) { sev = "crit"; lbl = "CRIT"; text = raw.slice(6); }
                                else if (raw.startsWith("SAFE:")) { sev = "safe"; lbl = "SAFE"; text = raw.slice(6); }
                                else if (raw.startsWith("WARN:")) { text = raw.slice(6); }
                                return (
                                  <div key={i} className={`flag-pill flag-${sev}`}>
                                    <span className="flag-badge">{lbl}</span>
                                    <span className="flag-text">{text}</span>
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="detail-panel" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                      Select a job to view details
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </section>
      )}


      {viewMode === 'help' && user && (
        <section className="insights-section">
          <div className="insights-header">
            <h1 className="insights-title">Need Help or Have Feedback?</h1>
            <p className="insights-subtitle">We&apos;d love to hear from you. Send us a message and we&apos;ll get back to you shortly.</p>
          </div>
          <div style={{ maxWidth: 640, margin: '0 auto', padding: '0 1.5rem' }}>
            <div className="chart-card" style={{ padding: '2rem' }}>
              {!helpSuccess ? (
                <form onSubmit={async (e) => {
                  e.preventDefault();
                  if (!helpMsg.trim()) return;
                  setHelpLoading(true);
                  try {
                    const { data, error } = await supabase.functions.invoke("send-help-email", {
                      body: { user_email: user.email, message: helpMsg.trim() },
                    });
                    if (error) throw error;
                    if (data?.status === "sent" || data?.status === "logged") {
                      setHelpSuccess(true);
                      setHelpMsg('');
                    } else {
                      alert('Failed to send. Please try again.');
                    }
                  } catch (err) {
                    console.error("[Help] submit error:", err);
                    alert('Failed to send. Please try again.');
                  } finally {
                    setHelpLoading(false);
                  }
                }}>
                  <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-primary)' }}>
                    Your Message
                  </label>
                  <textarea
                    value={helpMsg}
                    onChange={(e) => setHelpMsg(e.target.value)}
                    rows={6}
                    placeholder="Describe your issue, question, or feedback..."
                    required
                    style={{
                      width: '100%',
                      padding: '0.75rem 1rem',
                      borderRadius: '0.5rem',
                      border: '1px solid var(--border)',
                      background: 'var(--bg-card)',
                      color: 'var(--text-primary)',
                      fontSize: '0.95rem',
                      resize: 'vertical',
                      fontFamily: 'inherit',
                    }}
                  />
                  <div style={{ marginTop: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <button
                      type="submit"
                      disabled={helpLoading || !helpMsg.trim()}
                      style={{
                        padding: '0.65rem 1.75rem',
                        borderRadius: '0.5rem',
                        border: 'none',
                        background: helpLoading ? 'var(--text-muted)' : 'var(--coral)',
                        color: '#fff',
                        fontWeight: 600,
                        fontSize: '0.9rem',
                        cursor: helpLoading ? 'not-allowed' : 'pointer',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                      }}
                    >
                      {helpLoading && (
                        <span style={{
                          width: 16, height: 16, border: '2px solid rgba(255,255,255,0.3)',
                          borderTopColor: '#fff', borderRadius: '50%', animation: 'spin 0.6s linear infinite', display: 'inline-block',
                        }} />
                      )}
                      {helpLoading ? 'Sending...' : 'Submit'}
                    </button>
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                      from {user.email}
                    </span>
                  </div>
                </form>
              ) : (
                <div style={{ textAlign: 'center', padding: '2rem 0' }}>
                  <div style={{ fontSize: '2.5rem', marginBottom: '0.75rem' }}>&#10003;</div>
                  <h3 style={{ color: 'var(--text-primary)', marginBottom: '0.5rem' }}>Message Sent Successfully!</h3>
                  <p style={{ color: 'var(--text-muted)', marginBottom: '1.5rem' }}>
                    Thank you for reaching out. We&apos;ll review your message and get back to you at <strong>{user.email}</strong>.
                  </p>
                  <button
                    onClick={() => setHelpSuccess(false)}
                    style={{
                      padding: '0.5rem 1.5rem', borderRadius: '0.5rem', border: '1px solid var(--coral)',
                      background: 'transparent', color: 'var(--coral)', fontWeight: 600, cursor: 'pointer',
                    }}
                  >
                    Send Another Message
                  </button>
                </div>
              )}
            </div>
          </div>
        </section>
      )}


      {/* ═══════════ FOOTER ═══════════ */}
      <footer className="site-footer">
        <p>ShieldDB — Built to protect job seekers.</p>
      </footer>
    </div>
  );
}
