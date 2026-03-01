import { useState, useRef, useEffect, useCallback } from "react";
import "./App.css";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

type Vector6D = {
  economic_role: string;
  price_tolerance: string;
  emotional_driver: string;
  technical_sophistication: string;
  time_abundance: string;
  risk_tolerance: string;
};

type Tester = {
  tester_id: string;
  name: string;
  bio: string;
  vector: Vector6D;
};

type RoundData = {
  round: number;
  style_assignments: Array<{
    candidate: number;
    style: string;
    target_tester?: string;
  }>;
  designer_prompts: Array<{ candidate: number; prompt: string }>;
  images: Array<{ candidate: number; url: string }>;
  critique: {
    winner: number;
    scores: Array<{ candidate: number; score: number; reasoning: string }>;
    improvement_suggestions: string;
    tester_reviews: unknown[];
  };
};

type PipelineResult = {
  session_id: string;
  user_prompt: string;
  testers: Tester[];
  rounds: RoundData[];
  wandb_url?: string;
};

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const CARD_W = 100;
const CARD_H = 100;
const CARD_GAP = 16;
const COL_GAP = 120;
const HEADER_H = 38;
const PAD_TOP = 24;
const PAD_LEFT = 32;

const MOCK: PipelineResult = {
  session_id: "demo_1709284000",
  user_prompt: "A meditation app for busy professionals",
  testers: [
    {
      tester_id: "t1",
      name: "Ava Chen",
      bio: "28-year-old product manager, always on her phone between meetings.",
      vector: {
        economic_role: "B2C",
        price_tolerance: "Mid",
        emotional_driver: "Convenience",
        technical_sophistication: "High",
        time_abundance: "Low",
        risk_tolerance: "Low",
      },
    },
    {
      tester_id: "t2",
      name: "Marcus Rivera",
      bio: "45-year-old VP of sales who wants to manage stress but is skeptical of wellness apps.",
      vector: {
        economic_role: "B2C",
        price_tolerance: "Premium",
        emotional_driver: "Status",
        technical_sophistication: "Medium",
        time_abundance: "Low",
        risk_tolerance: "Low",
      },
    },
    {
      tester_id: "t3",
      name: "Jun Tanaka",
      bio: "22-year-old junior developer exploring mindfulness for the first time.",
      vector: {
        economic_role: "B2C",
        price_tolerance: "Low",
        emotional_driver: "Exploration",
        technical_sophistication: "High",
        time_abundance: "High",
        risk_tolerance: "High",
      },
    },
  ],
  rounds: [
    {
      round: 1,
      style_assignments: [
        { candidate: 1, style: "Minimalist/Flat" },
        { candidate: 2, style: "Glassmorphism" },
        { candidate: 3, style: "Dark Mode First/Cyber" },
      ],
      designer_prompts: [
        { candidate: 1, prompt: "Clean white meditation screen with breathing circle and minimal controls…" },
        { candidate: 2, prompt: "Frosted glass cards floating over a gradient background showing session stats…" },
        { candidate: 3, prompt: "Dark theme with neon-accented breathing visualizer and ambient particle field…" },
      ],
      images: [
        { candidate: 1, url: "" },
        { candidate: 2, url: "" },
        { candidate: 3, url: "" },
      ],
      critique: {
        winner: 1,
        scores: [
          { candidate: 1, score: 8.2, reasoning: "Clean and calming, purpose immediately clear." },
          { candidate: 2, score: 7.1, reasoning: "Beautiful but slightly unclear hierarchy." },
          { candidate: 3, score: 6.5, reasoning: "Visually interesting but feels like a game, not meditation." },
        ],
        improvement_suggestions:
          "Make the primary CTA larger. Add session duration picker. Improve text contrast on candidate 3.",
        tester_reviews: [],
      },
    },
    {
      round: 2,
      style_assignments: [
        { candidate: 1, style: "Minimalist/Flat" },
        { candidate: 2, style: "Glassmorphism" },
        { candidate: 3, style: "Dark Mode First/Cyber" },
      ],
      designer_prompts: [
        { candidate: 1, prompt: "Refined minimal screen with larger Start button and session picker…" },
        { candidate: 2, prompt: "Glass cards with clearer text hierarchy and visible timer…" },
        { candidate: 3, prompt: "Dark theme toned down, improved contrast, added calm color accents…" },
      ],
      images: [
        { candidate: 1, url: "" },
        { candidate: 2, url: "" },
        { candidate: 3, url: "" },
      ],
      critique: {
        winner: 1,
        scores: [
          { candidate: 1, score: 9.0, reasoning: "Excellent clarity and calm feel. CTA is unmissable." },
          { candidate: 2, score: 7.8, reasoning: "Much improved hierarchy, glass effect still a bit heavy." },
          { candidate: 3, score: 7.3, reasoning: "Better contrast, feels more appropriate now." },
        ],
        improvement_suggestions: "Consider adding onboarding hint. Candidate 2 glass blur could be subtler.",
        tester_reviews: [],
      },
    },
  ],
  wandb_url: "https://wandb.ai/example/design-self-improve",
};

/* ------------------------------------------------------------------ */
/*  Canvas drawing                                                     */
/* ------------------------------------------------------------------ */

function drawTimeline(
  canvas: HTMLCanvasElement,
  rounds: RoundData[],
  selectedImg: { round: number; candidate: number } | null,
  loadedImages: Map<string, HTMLImageElement>
) {
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  const cols = rounds.length;
  const totalW = PAD_LEFT + cols * (CARD_W + COL_GAP);
  const totalH = PAD_TOP + HEADER_H + 3 * (CARD_H + CARD_GAP) + 40;
  const dpr = window.devicePixelRatio || 1;

  canvas.width = totalW * dpr;
  canvas.height = totalH * dpr;
  canvas.style.width = `${totalW}px`;
  canvas.style.height = `${totalH}px`;
  ctx.scale(dpr, dpr);

  // background
  ctx.fillStyle = "#fff0e0";
  ctx.fillRect(0, 0, totalW, totalH);

  // subtle dotted grid
  ctx.fillStyle = "#fff0e0";
  for (let y = 0; y <= totalH; y += 18) {
    for (let x = 0; x <= totalW; x += 18) {
      ctx.beginPath();
      ctx.arc(x, y, 1, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  for (let ri = 0; ri < cols; ri++) {
    const rd = rounds[ri];
    const colX = PAD_LEFT + ri * (CARD_W + COL_GAP);

    // round header
    ctx.fillStyle = "#2F2A26";
    ctx.font = "800 20px Opaline, Adelora, system-ui, sans-serif";
    ctx.fillText(`Round ${rd.round}`, colX, PAD_TOP + 12);

    for (let ci = 0; ci < 3; ci++) {
      const cid = ci + 1;
      const x = colX;
      const y = PAD_TOP + HEADER_H + ci * (CARD_H + CARD_GAP);

      const isWinner = rd.critique.winner === cid;
      const isSelected =
        selectedImg?.round === rd.round && selectedImg?.candidate === cid;

      // card bg
      ctx.save();
      ctx.shadowColor = "rgba(0,0,0,0.05)";
      ctx.shadowBlur = 10;
      ctx.shadowOffsetX = 0;
      ctx.shadowOffsetY = 3;
      ctx.fillStyle = "#FFFFFF";
      ctx.beginPath();
      ctx.roundRect(x, y, CARD_W, CARD_H, 8);
      ctx.fill();

      // card border
      ctx.shadowColor = "rgba(0,0,0,0)";
      ctx.shadowBlur = 0;
      ctx.shadowOffsetX = 0;
      ctx.shadowOffsetY = 0;
      ctx.strokeStyle = "#E5DFD6";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.roundRect(x, y, CARD_W, CARD_H, 8);
      ctx.stroke();
      ctx.restore();

      // try to draw loaded image
      const imgKey = `${rd.round}-${cid}`;
      const img = loadedImages.get(imgKey);
      if (img && img.complete && img.naturalWidth > 0) {
        ctx.save();
        ctx.beginPath();
        ctx.roundRect(x + 2, y + 2, CARD_W - 4, CARD_H - 4, 6);
        ctx.clip();
        ctx.drawImage(img, x + 2, y + 2, CARD_W - 4, CARD_H - 4);
        ctx.restore();
      } else {
        // placeholder
        ctx.fillStyle = "#F1ECE2";
        ctx.beginPath();
        ctx.roundRect(x + 2, y + 2, CARD_W - 4, CARD_H - 4, 6);
        ctx.fill();
        ctx.fillStyle = "#6E665E";
        ctx.font = "600 17px Opaline, Adelora, system-ui, sans-serif";
        ctx.textAlign = "center";
        ctx.fillText(`C${cid}`, x + CARD_W / 2, y + CARD_H / 2 + 4);
        ctx.textAlign = "left";
      }

      // winner ring
      if (isWinner) {
        ctx.strokeStyle = "#FA7070";
        ctx.lineWidth = 2.5;
        ctx.beginPath();
        ctx.roundRect(x - 1, y - 1, CARD_W + 2, CARD_H + 2, 9);
        ctx.stroke();
      }

      // selection ring
      if (isSelected) {
        ctx.strokeStyle = "#B8B2A8";
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.roundRect(x - 3, y - 3, CARD_W + 6, CARD_H + 6, 11);
        ctx.stroke();
      }

      // score badge
      const score = rd.critique.scores.find((s) => s.candidate === cid);
      if (score) {
        const badgeX = x + CARD_W - 6;
        const badgeY = y + 6;
        ctx.fillStyle = isWinner ? "#FA7070" : "#E5DFD6";
        ctx.beginPath();
        ctx.arc(badgeX, badgeY, 14, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = "#2F2A26";
        ctx.font = "800 15px Opaline, Adelora, system-ui, sans-serif";
        ctx.textAlign = "center";
        ctx.fillText(score.score.toFixed(1), badgeX, badgeY + 3.5);
        ctx.textAlign = "left";
      }

      // style label
      const sa = rd.style_assignments.find((s) => s.candidate === cid);
      if (sa) {
        ctx.fillStyle = "#6E665E";
        ctx.font = "600 14px Opaline, Adelora, system-ui, sans-serif";
        const label =
          sa.style.length > 16 ? sa.style.slice(0, 15) + "…" : sa.style;
        ctx.fillText(label, x + 4, y + CARD_H - 5);
      }
    }

    // arrows to next round
    if (ri < cols - 1) {
      const nextColX = PAD_LEFT + (ri + 1) * (CARD_W + COL_GAP);
      const winnerCid = rd.critique.winner;
      const fromCi = winnerCid - 1;
      const fromX = colX + CARD_W + 4;
      const fromY =
        PAD_TOP + HEADER_H + fromCi * (CARD_H + CARD_GAP) + CARD_H / 2;

      for (let ci = 0; ci < 3; ci++) {
        const toX = nextColX - 4;
        const toY =
          PAD_TOP + HEADER_H + ci * (CARD_H + CARD_GAP) + CARD_H / 2;

        ctx.strokeStyle = ci === fromCi ? "#FA7070" : "#CFC8BE";
        ctx.lineWidth = ci === fromCi ? 2 : 1;
        ctx.beginPath();
        ctx.moveTo(fromX, fromY);

        const cpx = (fromX + toX) / 2;
        ctx.bezierCurveTo(cpx, fromY, cpx, toY, toX, toY);
        ctx.stroke();

        // arrowhead
        if (ci === fromCi) {
          const angle = Math.atan2(toY - fromY, toX - fromX);
          const headLen = 7;
          ctx.fillStyle = "#FA7070";
          ctx.beginPath();
          ctx.moveTo(toX, toY);
          ctx.lineTo(
            toX - headLen * Math.cos(angle - 0.4),
            toY - headLen * Math.sin(angle - 0.4)
          );
          ctx.lineTo(
            toX - headLen * Math.cos(angle + 0.4),
            toY - headLen * Math.sin(angle + 0.4)
          );
          ctx.closePath();
          ctx.fill();
        }
      }
    }
  }
}

function hitTestCanvas(
  e: React.MouseEvent<HTMLCanvasElement>,
  rounds: RoundData[]
): { round: number; candidate: number } | null {
  const rect = e.currentTarget.getBoundingClientRect();
  const mx = e.clientX - rect.left;
  const my = e.clientY - rect.top;

  for (let ri = 0; ri < rounds.length; ri++) {
    const rd = rounds[ri];
    const colX = PAD_LEFT + ri * (CARD_W + COL_GAP);
    for (let ci = 0; ci < 3; ci++) {
      const x = colX;
      const y = PAD_TOP + HEADER_H + ci * (CARD_H + CARD_GAP);
      if (mx >= x && mx <= x + CARD_W && my >= y && my <= y + CARD_H) {
        return { round: rd.round, candidate: ci + 1 };
      }
    }
  }
  return null;
}

/* ------------------------------------------------------------------ */
/*  App                                                                */
/* ------------------------------------------------------------------ */

function App() {
  const [prompt, setPrompt] = useState("A meditation app for busy professionals");
  const [rounds, setRounds] = useState(3);
  const [mockMode, setMockMode] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PipelineResult | null>(null);
  const [selectedImg, setSelectedImg] = useState<{
    round: number;
    candidate: number;
  } | null>(null);
  const [reportOpen, setReportOpen] = useState(false);
  const [expandedReviews, setExpandedReviews] = useState<Set<number>>(
    new Set()
  );
  const [loadedImages, setLoadedImages] = useState<
    Map<string, HTMLImageElement>
  >(new Map());

  const canvasRef = useRef<HTMLCanvasElement>(null);

  /* ---------- fetch pipeline ---------- */

  const runPipeline = useCallback(async () => {
    if (!prompt.trim()) return;

    if (mockMode) {
      setLoading(false);
      setError(null);
      setResult(MOCK);
      setSelectedImg(null);
      setReportOpen(false);
      setExpandedReviews(new Set());
      setLoadedImages(new Map());
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);
    setSelectedImg(null);
    setReportOpen(false);
    setExpandedReviews(new Set());
    setLoadedImages(new Map());

    try {
      const resp = await fetch("/api/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_prompt: prompt, rounds }),
      });
      if (!resp.ok) {
        if (resp.status === 404) {
          throw new Error("Failed to fetch");
        }
        const text = await resp.text();
        throw new Error(`Server ${resp.status}: ${text.slice(0, 300)}`);
      }
      const data: PipelineResult = await resp.json();
      setResult(data);
    } catch (err: unknown) {
      if (err instanceof Error) {
        // If the backend isn't running, load mock data for development
        if (
          err.message.includes("Failed to fetch") ||
          err.message.includes("NetworkError")
        ) {
          setResult(MOCK);
          setError("Backend unavailable — showing demo data.");
        } else {
          setError(err.message);
        }
      } else {
        setError("Unknown error");
      }
    } finally {
      setLoading(false);
    }
  }, [prompt, rounds, mockMode]);

  /* ---------- load images when result arrives ---------- */

  useEffect(() => {
    if (!result) return;
    const map = new Map<string, HTMLImageElement>();
    for (const rd of result.rounds) {
      for (const img of rd.images) {
        if (!img.url) continue;
        const key = `${rd.round}-${img.candidate}`;
        const el = new Image();
        el.crossOrigin = "anonymous";
        el.src = img.url;
        el.onload = () => setLoadedImages((prev) => new Map(prev).set(key, el));
        map.set(key, el);
      }
    }
    setLoadedImages(map);
  }, [result]);

  /* ---------- redraw canvas ---------- */

  useEffect(() => {
    if (!canvasRef.current || !result) return;
    drawTimeline(canvasRef.current, result.rounds, selectedImg, loadedImages);
  }, [result, selectedImg, loadedImages]);

  /* ---------- canvas click ---------- */

  const onCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!result) return;
    const hit = hitTestCanvas(e, result.rounds);
    setSelectedImg(hit);
  };

  /* ---------- derive selection info ---------- */

  const selRound = result?.rounds.find((r) => r.round === selectedImg?.round);
  const selScore = selRound?.critique.scores.find(
    (s) => s.candidate === selectedImg?.candidate
  );
  const selStyle = selRound?.style_assignments.find(
    (s) => s.candidate === selectedImg?.candidate
  );
  const selPrompt = selRound?.designer_prompts.find(
    (s) => s.candidate === selectedImg?.candidate
  );

  const started = loading || !!result;

  /* ---------- render ---------- */

  return (
    <div className={`app ${started ? "is-running" : "is-landing"}`}>
      {/* -------- header / input -------- */}
      <header className="header">
        <h1 className="title">Design Pipeline</h1>
        <div className="input-row">
          <textarea
            className="prompt-input"
            placeholder="Describe your product…"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            rows={2}
          />
          <div className="controls">
            <label className="rounds-label">
              Rounds
              <input
                type="number"
                className="rounds-input"
                min={1}
                max={10}
                value={rounds}
                onChange={(e) => setRounds(Number(e.target.value) || 1)}
              />
            </label>
            <label className="rounds-label">
              <input
                type="checkbox"
                checked={mockMode}
                onChange={(e) => setMockMode(e.target.checked)}
              />
              Mock mode
            </label>
            <button
              className="run-btn"
              onClick={runPipeline}
              disabled={loading || !prompt.trim()}
            >
              {loading ? "Running…" : mockMode ? "Run (Mock)" : "Run"}
            </button>
          </div>
        </div>
        {error && <p className="error-msg">{error}</p>}
        {loading && (
          <div className="loader-bar">
            <div className="loader-fill" />
          </div>
        )}
      </header>

      {/* -------- canvas timeline -------- */}
      {result && (
        <section className="timeline-section">
          <h2 className="section-title">Timeline</h2>
          <div className="canvas-wrap">
            <canvas
              ref={canvasRef}
              className="timeline-canvas"
              onClick={onCanvasClick}
            />
          </div>

          {/* selection detail */}
          {selectedImg && selRound && (
            <div className="selection-detail">
              <span className="sel-badge">
                Round {selectedImg.round} · Candidate {selectedImg.candidate}
                {selRound.critique.winner === selectedImg.candidate && (
                  <span className="winner-tag"> ★ Winner</span>
                )}
              </span>
              {selStyle && (
                <span className="sel-style">{selStyle.style}</span>
              )}
              {selScore && (
                <span className="sel-score">
                  {selScore.score.toFixed(1)}/10
                </span>
              )}
              {selPrompt && (
                <p className="sel-prompt">{selPrompt.prompt}</p>
              )}
              {selScore && (
                <p className="sel-reasoning">{selScore.reasoning}</p>
              )}
            </div>
          )}
        </section>
      )}

      {/* -------- audience / testers -------- */}
      {result && (
        <section className="audience-section">
          <h2 className="section-title">Audience / Testers</h2>
          <div className="testers-grid">
            {result.testers.map((t) => (
              <div key={t.tester_id} className="tester-card">
                <h3 className="tester-name">{t.name}</h3>
                <p className="tester-bio">{t.bio}</p>
                <div className="vector-grid">
                  {(
                    Object.entries(t.vector) as [
                      keyof Vector6D,
                      string,
                    ][]
                  ).map(([k, v]) => (
                    <div key={k} className="vector-item">
                      <span className="vector-key">
                        {k.replace(/_/g, " ")}
                      </span>
                      <span className="vector-val">{v}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* -------- report -------- */}
      {result && (
        <section className="report-section">
          <button
            className="report-toggle"
            onClick={() => setReportOpen(!reportOpen)}
          >
            {reportOpen ? "Hide report ▲" : "Read report ▼"}
          </button>

          {reportOpen && (
            <div className="report-body">
              {result.rounds.map((rd) => (
                <div key={rd.round} className="report-round">
                  <h3 className="report-round-title">
                    Round {rd.round}
                    <span className="report-winner">
                      {" "}
                      — Winner: Candidate {rd.critique.winner}
                    </span>
                  </h3>

                  <table className="scores-table">
                    <thead>
                      <tr>
                        <th>Candidate</th>
                        <th>Score</th>
                        <th>Reasoning</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rd.critique.scores.map((s) => (
                        <tr
                          key={s.candidate}
                          className={
                            s.candidate === rd.critique.winner
                              ? "winner-row"
                              : ""
                          }
                        >
                          <td>{s.candidate}</td>
                          <td>{s.score.toFixed(1)}</td>
                          <td>{s.reasoning}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>

                  <p className="suggestions">
                    <strong>Suggestions:</strong>{" "}
                    {rd.critique.improvement_suggestions}
                  </p>

                  {rd.critique.tester_reviews.length > 0 && (
                    <div className="reviews-toggle-wrap">
                      <button
                        className="reviews-toggle"
                        onClick={() => {
                          setExpandedReviews((prev) => {
                            const next = new Set(prev);
                            if (next.has(rd.round)) next.delete(rd.round);
                            else next.add(rd.round);
                            return next;
                          });
                        }}
                      >
                        {expandedReviews.has(rd.round)
                          ? "Hide tester reviews ▲"
                          : "Show tester reviews ▼"}
                      </button>
                      {expandedReviews.has(rd.round) && (
                        <pre className="reviews-json">
                          {JSON.stringify(
                            rd.critique.tester_reviews,
                            null,
                            2
                          )}
                        </pre>
                      )}
                    </div>
                  )}
                </div>
              ))}

              {result.wandb_url && (
                <p className="wandb-link">
                  W&B run:{" "}
                  <a
                    href={result.wandb_url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {result.wandb_url}
                  </a>
                </p>
              )}
            </div>
          )}
        </section>
      )}
    </div>
  );
}

export default App;
