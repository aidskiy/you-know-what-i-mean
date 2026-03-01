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

type ViewTransform = {
  scale: number;
  offsetX: number;
  offsetY: number;
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
  loadedImages: Map<string, HTMLImageElement>,
  view: ViewTransform,
  viewport: { width: number; height: number }
) {
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  const cols = rounds.length;
  const dpr = window.devicePixelRatio || 1;

  const vw = Math.max(1, Math.floor(viewport.width));
  const vh = Math.max(1, Math.floor(viewport.height));

  canvas.width = vw * dpr;
  canvas.height = vh * dpr;
  canvas.style.width = `${vw}px`;
  canvas.style.height = `${vh}px`;

  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

  // Screen-space background
  ctx.fillStyle = "#fff0e0";
  ctx.fillRect(0, 0, vw, vh);

  // subtle dotted grid
  ctx.fillStyle = "rgba(47, 42, 38, 0.06)";
  for (let y = 0; y <= vh; y += 18) {
    for (let x = 0; x <= vw; x += 18) {
      ctx.beginPath();
      ctx.arc(x, y, 1, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  ctx.save();
  ctx.translate(view.offsetX, view.offsetY);
  ctx.scale(view.scale, view.scale);

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
    if (ri < rounds.length - 1) {
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

  ctx.restore();
}

function hitTestCanvas(
  e: React.MouseEvent<HTMLCanvasElement>,
  rounds: RoundData[],
  view: ViewTransform
): { round: number; candidate: number } | null {
  const rect = e.currentTarget.getBoundingClientRect();
  const mx = e.clientX - rect.left;
  const my = e.clientY - rect.top;

  const worldX = (mx - view.offsetX) / view.scale;
  const worldY = (my - view.offsetY) / view.scale;

  for (let ri = 0; ri < rounds.length; ri++) {
    const rd = rounds[ri];
    const colX = PAD_LEFT + ri * (CARD_W + COL_GAP);
    for (let ci = 0; ci < 3; ci++) {
      const x = colX;
      const y = PAD_TOP + HEADER_H + ci * (CARD_H + CARD_GAP);
      if (
        worldX >= x &&
        worldX <= x + CARD_W &&
        worldY >= y &&
        worldY <= y + CARD_H
      ) {
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
  const [statusMsg, setStatusMsg] = useState<string | null>(null);
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

  // Lightbox state
  const [lightbox, setLightbox] = useState<{ round: number; candidate: number } | null>(null);

  const [isFullscreen, setIsFullscreen] = useState(false);
  const [view, setView] = useState<ViewTransform>({
    scale: 1,
    offsetX: 0,
    offsetY: 0,
  });
  const [isPanning, setIsPanning] = useState(false);
  const panStartRef = useRef<{
    x: number;
    y: number;
    offsetX: number;
    offsetY: number;
    pointerId: number;
  } | null>(null);
  const [fsViewport, setFsViewport] = useState<{ width: number; height: number }>(
    { width: 1, height: 1 }
  );

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const fsCanvasRef = useRef<HTMLCanvasElement>(null);
  const fsCanvasWrapRef = useRef<HTMLDivElement>(null);

  /* ---------- fetch pipeline ---------- */

  const runPipeline = useCallback(async () => {
    if (!prompt.trim()) return;

    if (mockMode) {
      setLoading(false);
      setError(null);
      setStatusMsg(null);
      setResult(MOCK);
      setSelectedImg(null);
      setReportOpen(false);
      setExpandedReviews(new Set());
      setLoadedImages(new Map());
      return;
    }

    setLoading(true);
    setError(null);
    setStatusMsg("Starting pipeline…");
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
        if (resp.status === 404) throw new Error("Failed to fetch");
        const text = await resp.text();
        throw new Error(`Server ${resp.status}: ${text.slice(0, 300)}`);
      }

      const reader = resp.body?.getReader();
      if (!reader) throw new Error("No response body");

      const decoder = new TextDecoder();
      let buffer = "";
      let sessionId = "";

      let testers: Tester[] = [];
      const roundsMap = new Map<number, RoundData>();

      const buildResult = (): PipelineResult => ({
        session_id: sessionId,
        user_prompt: prompt,
        testers,
        rounds: Array.from(roundsMap.values()).sort((a, b) => a.round - b.round),
      });

      const ensureRound = (roundNum: number): RoundData => {
        if (!roundsMap.has(roundNum)) {
          roundsMap.set(roundNum, {
            round: roundNum,
            style_assignments: [],
            designer_prompts: [],
            images: [],
            critique: { winner: 0, scores: [], improvement_suggestions: "", tester_reviews: [] },
          });
        }
        return roundsMap.get(roundNum)!;
      };

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        let eventType = "";
        for (const line of lines) {
          if (line.startsWith("event: ")) {
            eventType = line.slice(7).trim();
          } else if (line.startsWith("data: ") && eventType) {
            const data = JSON.parse(line.slice(6));

            switch (eventType) {
              case "status":
                setStatusMsg(data.message);
                break;

              case "testers":
                sessionId = data.session_id;
                testers = data.testers;
                setResult(buildResult());
                break;

              case "prompts": {
                const rd = ensureRound(data.round);
                rd.style_assignments = data.style_assignments;
                rd.designer_prompts = data.designer_prompts;
                setResult(buildResult());
                break;
              }

              case "image": {
                const rd = ensureRound(data.round);
                rd.images.push({ candidate: data.candidate, url: data.url });
                setResult(buildResult());
                const key = `${data.round}-${data.candidate}`;
                const el = new Image();
                el.crossOrigin = "anonymous";
                el.src = data.url;
                el.onload = () =>
                  setLoadedImages((prev) => new Map(prev).set(key, el));
                break;
              }

              case "critique": {
                const rd = ensureRound(data.round);
                rd.critique = data.critique;
                setResult(buildResult());
                break;
              }

              case "done":
                setStatusMsg(null);
                break;

              case "error":
                setError(data.message);
                break;
            }
            eventType = "";
          }
        }
      }
    } catch (err: unknown) {
      if (err instanceof Error) {
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
      setStatusMsg(null);
    }
  }, [prompt, rounds, mockMode]);

  /* ---------- load images when mock result is set ---------- */

  useEffect(() => {
    if (!result || !mockMode) return;
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
  }, [result, mockMode]);

  /* ---------- redraw inline canvas ---------- */

  useEffect(() => {
    if (!result) return;

    const cols = result.rounds.length;
    const worldW = PAD_LEFT + cols * (CARD_W + COL_GAP);
    const worldH = PAD_TOP + HEADER_H + 3 * (CARD_H + CARD_GAP) + 40;

    if (canvasRef.current && !isFullscreen) {
      drawTimeline(
        canvasRef.current,
        result.rounds,
        selectedImg,
        loadedImages,
        view,
        { width: worldW, height: worldH }
      );
    }

    if (fsCanvasRef.current && isFullscreen) {
      drawTimeline(
        fsCanvasRef.current,
        result.rounds,
        selectedImg,
        loadedImages,
        view,
        fsViewport
      );
    }
  }, [result, selectedImg, loadedImages, view, isFullscreen, fsViewport]);

  /* ---------- fullscreen canvas sizing ---------- */

  useEffect(() => {
    if (!isFullscreen) return;
    const el = fsCanvasWrapRef.current;
    if (!el) return;

    const update = () => {
      const r = el.getBoundingClientRect();
      setFsViewport({ width: r.width, height: r.height });
    };

    update();
    const ro = new ResizeObserver(() => update());
    ro.observe(el);
    window.addEventListener("resize", update);
    return () => {
      ro.disconnect();
      window.removeEventListener("resize", update);
    };
  }, [isFullscreen]);

  /* ---------- canvas click ---------- */

  const onCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!result) return;
    const hit = hitTestCanvas(e, result.rounds, view);
    setSelectedImg(hit);
    if (hit) {
      const key = `${hit.round}-${hit.candidate}`;
      if (loadedImages.has(key)) setLightbox(hit);
    }
  };

  /* ---------- zoom / pan handlers ---------- */

  const clampScale = (s: number) => Math.min(2.5, Math.max(0.6, s));

  const zoomTo = (
    nextScale: number,
    anchor: { x: number; y: number } | null,
    target: HTMLCanvasElement
  ) => {
    const rect = target.getBoundingClientRect();
    const mx = (anchor?.x ?? rect.width / 2) - rect.left;
    const my = (anchor?.y ?? rect.height / 2) - rect.top;

    setView((prev) => {
      const newScale = clampScale(nextScale);
      const worldX = (mx - prev.offsetX) / prev.scale;
      const worldY = (my - prev.offsetY) / prev.scale;
      const offsetX = mx - worldX * newScale;
      const offsetY = my - worldY * newScale;
      return { scale: newScale, offsetX, offsetY };
    });
  };

  const onCanvasWheel = (e: React.WheelEvent<HTMLCanvasElement>) => {
    const wantsZoom = isFullscreen || e.ctrlKey || e.metaKey;
    if (!wantsZoom) return;
    e.preventDefault();

    const zoomIntensity = 0.0015;
    const delta = -e.deltaY * zoomIntensity;
    const factor = Math.exp(delta);
    const target = e.currentTarget;
    zoomTo(view.scale * factor, { x: e.clientX, y: e.clientY }, target);
  };

  const onCanvasPointerDown = (e: React.PointerEvent<HTMLCanvasElement>) => {
    if (view.scale === 1) return;
    if (e.button !== 0) return;
    const target = e.currentTarget;
    target.setPointerCapture(e.pointerId);
    panStartRef.current = {
      x: e.clientX,
      y: e.clientY,
      offsetX: view.offsetX,
      offsetY: view.offsetY,
      pointerId: e.pointerId,
    };
    setIsPanning(true);
  };

  const onCanvasPointerMove = (e: React.PointerEvent<HTMLCanvasElement>) => {
    const start = panStartRef.current;
    if (!start) return;
    if (start.pointerId !== e.pointerId) return;
    const dx = e.clientX - start.x;
    const dy = e.clientY - start.y;
    setView((prev) => ({
      ...prev,
      offsetX: start.offsetX + dx,
      offsetY: start.offsetY + dy,
    }));
  };

  const endPan = (e: React.PointerEvent<HTMLCanvasElement>) => {
    const start = panStartRef.current;
    if (!start) return;
    if (start.pointerId !== e.pointerId) return;
    panStartRef.current = null;
    setIsPanning(false);
  };

  const zoomIn = (target: HTMLCanvasElement | null) => {
    if (!target) return;
    zoomTo(view.scale * 1.15, null, target);
  };

  const zoomOut = (target: HTMLCanvasElement | null) => {
    if (!target) return;
    zoomTo(view.scale / 1.15, null, target);
  };

  const resetView = () => setView({ scale: 1, offsetX: 0, offsetY: 0 });

  useEffect(() => {
    if (!isFullscreen && !lightbox) return;
    const onKeyDown = (ev: KeyboardEvent) => {
      if (ev.key === "Escape") {
        if (lightbox) setLightbox(null);
        else setIsFullscreen(false);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [isFullscreen, lightbox]);

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

  // Lightbox derivations
  const lbRound = result?.rounds.find((r) => r.round === lightbox?.round);
  const lbScore = lbRound?.critique.scores.find((s) => s.candidate === lightbox?.candidate);
  const lbStyle = lbRound?.style_assignments.find((s) => s.candidate === lightbox?.candidate);
  const lbImgKey = lightbox ? `${lightbox.round}-${lightbox.candidate}` : null;
  const lbImg = lbImgKey ? loadedImages.get(lbImgKey) : undefined;

  const started = loading || !!result;

  /* ---------- render ---------- */

  return (
    <div className={`app ${started ? "is-running" : "is-landing"}`}>
      {/* -------- header / input -------- */}
      <header className="header">
        <h1 className="title">Design ~ Storm</h1>
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
        {statusMsg && <p className="status-msg">{statusMsg}</p>}
      </header>

      {/* -------- canvas timeline -------- */}
      {result && (
        <section className="timeline-section">
          <div className="timeline-title-row">
            <h2 className="section-title">Timeline</h2>
            <button
              className="timeline-expand"
              onClick={() => setIsFullscreen(true)}
              type="button"
            >
              Expand
            </button>
          </div>
          <div className="canvas-wrap">
            <canvas
              ref={canvasRef}
              className={`timeline-canvas ${view.scale !== 1 ? "is-grabbable" : ""
                } ${isPanning ? "is-grabbing" : ""}`}
              onClick={onCanvasClick}
              onWheel={onCanvasWheel}
              onPointerDown={onCanvasPointerDown}
              onPointerMove={onCanvasPointerMove}
              onPointerUp={endPan}
              onPointerCancel={endPan}
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
              {selStyle && <span className="sel-style">{selStyle.style}</span>}
              {selScore && (
                <span className="sel-score">{selScore.score.toFixed(1)}/10</span>
              )}
              {selPrompt && <p className="sel-prompt">{selPrompt.prompt}</p>}
              {selScore && (
                <p className="sel-reasoning">{selScore.reasoning}</p>
              )}
            </div>
          )}
        </section>
      )}

      {result && isFullscreen && (
        <div className="timeline-overlay" role="dialog" aria-modal="true">
          <div className="timeline-overlay-inner">
            <div className="timeline-overlay-header">
              <div className="timeline-overlay-title">Timeline</div>
              <div className="timeline-overlay-controls">
                <button
                  type="button"
                  className="zoom-btn"
                  onClick={() => zoomOut(fsCanvasRef.current)}
                >
                  -
                </button>
                <button
                  type="button"
                  className="zoom-btn"
                  onClick={() => zoomIn(fsCanvasRef.current)}
                >
                  +
                </button>
                <button type="button" className="zoom-reset" onClick={resetView}>
                  Reset
                </button>
                <div className="zoom-readout">
                  {Math.round(view.scale * 100)}%
                </div>
              </div>
              <button
                className="timeline-overlay-close"
                onClick={() => setIsFullscreen(false)}
                type="button"
                aria-label="Close"
              >
                ×
              </button>
            </div>

            <div className="timeline-overlay-canvas" ref={fsCanvasWrapRef}>
              <canvas
                ref={fsCanvasRef}
                className={`timeline-canvas timeline-canvas--fullscreen ${view.scale !== 1 ? "is-grabbable" : ""
                  } ${isPanning ? "is-grabbing" : ""}`}
                onClick={onCanvasClick}
                onWheel={onCanvasWheel}
                onPointerDown={onCanvasPointerDown}
                onPointerMove={onCanvasPointerMove}
                onPointerUp={endPan}
                onPointerCancel={endPan}
              />
            </div>
          </div>
        </div>
      )}

      {/* -------- image lightbox -------- */}
      {lightbox && lbImg && (
        <div className="lb-overlay" onClick={() => setLightbox(null)}>
          <div className="lb-phone" onClick={(e) => e.stopPropagation()}>
            <div className="lb-phone-header">
              <span className="lb-label">
                Round {lightbox.round} · C{lightbox.candidate}
                {lbRound?.critique.winner === lightbox.candidate && (
                  <span className="winner-tag"> ★</span>
                )}
              </span>
              {lbStyle && <span className="sel-style">{lbStyle.style}</span>}
              {lbScore && <span className="sel-score">{lbScore.score.toFixed(1)}</span>}
              <button className="lb-close" onClick={() => setLightbox(null)}>×</button>
            </div>
            <img className="lb-img" src={lbImg.src} alt={`Round ${lightbox.round} Candidate ${lightbox.candidate}`} />
          </div>
        </div>
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
