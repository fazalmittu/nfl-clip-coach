# NFL Clip Coach

## The Problem

Coaches, analysts, and fans spend **hours** manually scrubbing through full NFL game footage to find specific plays. Want to see every 3rd-down conversion from the 4th quarter? That means fast-forwarding through a 3+ hour broadcast, squinting at the game clock, and mentally cross-referencing play-by-play logs. A single film session can eat up an entire afternoon just to pull 8-10 clips.

NFL teams have dedicated film rooms with expensive proprietary tools. Everyone else — aspiring coaches, fantasy analysts, film study enthusiasts — gets nothing. They're stuck with a YouTube video and a spreadsheet.

**NFL Clip Coach fixes this.** Type a question in plain English, get the exact clips instantly.

## What We Built

NFL Clip Coach is an AI-powered game film assistant. You type a natural language query — *"show me Brock Purdy's completions over 20 yards"* — and the system parses your intent, searches play-by-play data, maps matching plays to exact video timestamps, and serves up clipped footage ready to watch.

**Two modes:**

- **Video mode** — find and watch specific plays via natural language search
- **Chat mode** — ask analytical questions about the game and get AI-generated insights backed by real data, with the option to jump to relevant clips

```
                    ┌─────────────────────────┐
                    │  User types a question   │
                    └────────────┬─────────────┘
                                 │
                                 ▼
                          ┌────────────┐
                          │   Mode?    │
                          └──┬──────┬──┘
                             │      │
                    Video ◄──┘      └──► Chat
                             │      │
                             ▼      ▼
              ┌──────────────────┐  ┌──────────────────────┐
              │ Find matching    │  │ AI game analysis     │
              │ plays            │  │                      │
              └────────┬─────────┘  └──────────┬───────────┘
                       │                       │
                       ▼                       ▼
              ┌──────────────────┐  ┌──────────────────────┐
              │ Return timestamped│  │ Insight + optional   │
              │ clips            │  │ clip suggestions     │
              └────────┬─────────┘  └──────────┬───────────┘
                       │                       │
                       └───────────┬───────────┘
                                   ▼
                        ┌─────────────────────┐
                        │ Watch in video      │
                        │ player              │
                        └─────────────────────┘
```

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                  FRONTEND (React 19 + Vite + Tailwind)              │
│   ┌──────────────────┐  ┌────────────────────────────────────────┐  │
│   │    Chat Panel     │  │           Video Player                 │  │
│   │  (react-markdown) │  │  (HTML5 + custom controls + clips)    │  │
│   └────────┬─────────┘  └───────────────────┬────────────────────┘  │
└────────────┼────────────────────────────────┼───────────────────────┘
             │ POST /analyze                  │ seek & play
             ▼                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      BACKEND (FastAPI + Uvicorn)                    │
│                                                                     │
│  ┌───────────────────────┐          ┌────────────────────────────┐  │
│  │  CLIP SEARCH SERVICE  │          │   GAME ANALYST SERVICE     │  │
│  │  ┌─────────────────┐  │          │  ┌──────────────────────┐  │  │
│  │  │ Query Parser     │  │          │  │ Session Manager      │  │  │
│  │  │ (NL → filters)  │  │          │  │ (conversation hist.) │  │  │
│  │  └────────┬────────┘  │          │  └──────────┬───────────┘  │  │
│  │           ▼           │          │             ▼              │  │
│  │  ┌─────────────────┐  │          │  ┌──────────────────────┐  │  │
│  │  │ Filter Engine    │  │          │  │ Claude Chat          │  │  │
│  │  │ (pandas ops)    │  │          │  │ (game context +      │  │  │
│  │  └────────┬────────┘  │          │  │  code generation)    │  │  │
│  │           ▼           │          │  └──────────┬───────────┘  │  │
│  │  ┌─────────────────┐  │          │             ▼              │  │
│  │  │ Video Clip Svc   │  │          │  ┌──────────────────────┐  │  │
│  │  │ (timestamp map) │  │          │  │ Code Executor        │  │  │
│  │  └────────┬────────┘  │          │  │ (sandboxed pandas)   │  │  │
│  │           ▼           │          │  └──────────────────────┘  │  │
│  │  ┌─────────────────┐  │          └────────────────────────────┘  │
│  │  │ Video Indexer    │  │                                         │
│  │  │ (Gemini Vision) │  │                                         │
│  │  └─────────────────┘  │                                         │
│  └───────────────────────┘                                         │
└──────────────┬──────────────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         AI SERVICES                                 │
│  ┌──────────────────────────┐  ┌─────────────────────────────────┐  │
│  │    Claude Sonnet 4       │  │      Google Gemini Vision       │  │
│  │  (Anthropic)             │  │                                 │  │
│  │  • NL query parsing      │  │  • Frame analysis               │  │
│  │  • Conversational chat   │  │  • Game clock extraction        │  │
│  │  • Pandas code generation│  │  • Quarter / score detection    │  │
│  └──────────────────────────┘  └─────────────────────────────────┘  │
└──────────────┬──────────────────────────────┬───────────────────────┘
               │                              │
               ▼                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          DATA LAYER                                 │
│  ┌──────────────────┐  ┌───────────────┐  ┌──────────────────────┐  │
│  │  Play-by-Play    │  │  Game Footage  │  │  .cache/index.json   │  │
│  │  CSV             │  │  (MP4)        │  │  (timestamp          │  │
│  │  182 plays ×     │  │  Full 3+ hr   │  │   mappings)          │  │
│  │  100+ columns    │  │  broadcast    │  │                      │  │
│  └──────────────────┘  └───────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

## Clip Search Pipeline

The core workflow — turning *"show me all Aidan Hutchinson sacks"* into playable video clips.

```
 ┌─────────────────────────────────────────┐
 │  User query:                            │
 │  "Show me Purdy's touchdowns"           │
 └──────────────────┬──────────────────────┘
                    │
                    ▼
 ┌─────────────────────────────────────────┐
 │  STEP 1: QUERY PARSING (Claude)        │
 │                                         │
 │  1. Select relevant column categories   │
 │     from 100+ available columns         │
 │                                         │
 │  2. Convert NL → structured JSON        │
 │     filters (column, operator, value)   │
 └──────────────────┬──────────────────────┘
                    │
                    ▼
 ┌─────────────────────────────────────────┐
 │  STEP 2: FILTER EXECUTION (Pandas)     │
 │                                         │
 │  • Apply filters to play-by-play       │
 │    DataFrame                            │
 │  • Supports: filter, sequence, drive,   │
 │    rank query types                     │
 │  • AND/OR logic at group level          │
 │                                         │
 │  Returns matching rows with metadata:   │
 │  quarter, time, players, yards, WPA     │
 └──────────────────┬──────────────────────┘
                    │
                    ▼
 ┌─────────────────────────────────────────┐
 │  STEP 3: TIMESTAMP MAPPING             │
 │                                         │
 │  For each matching play:                │
 │  • Look up game clock in video index    │
 │  • start = play_time − 5s buffer       │
 │  • end = start + base_duration          │
 │          + play_type bonuses            │
 │          + post-play buffer (15s)       │
 └──────────────────┬──────────────────────┘
                    │
                    ▼
 ┌─────────────────────────────────────────┐
 │  Return ClipTimestamp objects with      │
 │  rich metadata (players, scores, WPA)   │
 └──────────────────┬──────────────────────┘
                    │
                    ▼
 ┌─────────────────────────────────────────┐
 │  User clicks clip → video seeks        │
 │  to exact moment                        │
 └─────────────────────────────────────────┘
```

### Clip Duration Logic

Not all plays are equal. A 3-yard run doesn't need the same clip length as a 75-yard touchdown. The system dynamically calculates duration:

| Play Type | Base Duration | Bonuses |
|-----------|:---:|---------|
| Pass / Run | 20 s | + yards bonus |
| Kickoff / Punt | 25 s | — |
| Touchdown | base + 25 s | Celebration & replay |
| Turnover | base + 15 s | Return & aftermath |

All clips include a configurable post-play buffer (default 15 s).

## Video Indexing

The hardest problem: a play happens at **Q3 8:34** on the game clock, but *where* is that in a 3+ hour video file? Halftime, commercials, and replay breaks make the mapping non-linear.

```
 ┌──────────────────┐
 │  Full game MP4   │
 └────────┬─────────┘
          │
          ▼
 ┌─────────────────────────────────────────┐
 │  OpenCV samples frames                  │
 │  (every N seconds)                      │
 └──────────────────┬──────────────────────┘
                    │
                    ▼
 ┌─────────────────────────────────────────┐
 │  Send frames to Gemini Vision           │
 └──────────────────┬──────────────────────┘
                    │
                    ▼
 ┌─────────────────────────────────────────┐
 │  Extract from broadcast overlay:        │
 │  • Quarter number                       │
 │  • Game clock (MM:SS)                   │
 │  • Score display                        │
 └──────────────────┬──────────────────────┘
                    │
                    ▼
 ┌─────────────────────────────────────────┐
 │  Build mapping:                         │
 │  Q2_8:34  →  2397.15 video seconds     │
 │  Q3_12:00 →  4501.30 video seconds     │
 └──────────────────┬──────────────────────┘
                    │
                    ▼
 ┌─────────────────────────────────────────┐
 │  Cache to .cache/game.json              │
 │  (quarters, mappings, dead zones)       │
 └─────────────────────────────────────────┘


 AT QUERY TIME:

 ┌──────────────────┐
 │ Play at Q3 12:00 │
 └────────┬─────────┘
          │
          ▼
 ┌─────────────────────────────────────────┐
 │  Look up cached mapping                 │
 └──────┬──────────────────────┬───────────┘
        │                      │
   exact match            no match
        │                      │
        ▼                      ▼
 ┌──────────────┐   ┌─────────────────────┐
 │ Return video │   │ Interpolate from    │
 │ timestamp    │   │ nearest known       │
 │              │   │ frames              │
 └──────────────┘   └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Return video        │
                    │ timestamp           │
                    └─────────────────────┘
```

The indexer also detects **dead zones** (halftime, ads, timeouts with no visible game clock) and skips them during processing.

## Chat Analysis Mode

For analytical questions, Claude acts as a game analyst with full access to the play-by-play dataset.

```
 User                Frontend           FastAPI            Claude Sonnet 4     Code Executor
  │                     │                  │                     │                  │
  │ "What was the       │                  │                     │                  │
  │  turnover           │                  │                     │                  │
  │  differential?"     │                  │                     │                  │
  │────────────────────►│                  │                     │                  │
  │                     │ POST /analyze    │                     │                  │
  │                     │ (mode=chat)      │                     │                  │
  │                     │─────────────────►│                     │                  │
  │                     │                  │ System prompt       │                  │
  │                     │                  │ (game summary +     │                  │
  │                     │                  │  columns + history) │                  │
  │                     │                  │────────────────────►│                  │
  │                     │                  │                     │                  │
  │                     │                  │ Response with       │                  │
  │                     │                  │ ```python block     │                  │
  │                     │                  │◄────────────────────│                  │
  │                     │                  │                     │                  │
  │                     │                  │ Execute pandas code │                  │
  │                     │                  │ (only pd + df       │                  │
  │                     │                  │  available)         │                  │
  │                     │                  │────────────────────────────────────────►│
  │                     │                  │                     │                  │
  │                     │                  │ Code result         │                  │
  │                     │                  │◄────────────────────────────────────────│
  │                     │                  │                     │                  │
  │                     │                  │ "Summarize this     │                  │
  │                     │                  │  in natural         │                  │
  │                     │                  │  language"          │                  │
  │                     │                  │────────────────────►│                  │
  │                     │                  │                     │                  │
  │                     │                  │ Human-readable      │                  │
  │                     │                  │ answer              │                  │
  │                     │                  │◄────────────────────│                  │
  │                     │                  │                     │                  │
  │                     │ Response +       │                     │                  │
  │                     │ clip suggestions │                     │                  │
  │                     │◄─────────────────│                     │                  │
  │                     │                  │                     │                  │
  │ Analysis +          │                  │                     │                  │
  │ "Find clips" CTA   │                  │                     │                  │
  │◄────────────────────│                  │                     │                  │
  │                     │                  │                     │                  │
```

Claude can write and execute Python/pandas code against the full dataset to answer complex statistical questions, then translates the raw output into a natural language response.

## Tech Stack

| Layer | Technology | Purpose |
|:------|:-----------|:--------|
| **Frontend** | React 19, TypeScript 5.9, Vite 7 | UI framework + build tooling |
| **Styling** | Tailwind CSS 4 | Utility-first styling |
| **Backend** | FastAPI, Uvicorn, Python 3.13 | Async API server |
| **Data** | Pandas 2.0, Pydantic 2.0 | DataFrame ops + validation |
| **Video** | OpenCV 4.10, Pillow 10 | Frame extraction + image processing |
| **Query AI** | Claude Sonnet 4 (Anthropic) | NL parsing, chat, code generation |
| **Vision AI** | Google Gemini Vision | Game clock extraction from frames |
| **Storage** | CSV + JSON cache | Play-by-play data + video index |
| **Rendering** | react-markdown | Display AI analysis responses |

## Vision

NFL Clip Coach is a starting point. The same architecture — **natural language query → structured search → timestamped media retrieval** — generalizes far beyond one game:

- **Multi-game support** — index an entire season, search across games
- **Team & player dashboards** — aggregate tendencies, track performance over weeks
- **Coaching integration** — export clip packages for practice film review
- **Live game analysis** — real-time indexing during broadcasts
- **Other sports** — the NL-to-clip pipeline works for any sport with play-by-play data

The goal: **make professional-grade film study accessible to anyone with a game recording and a question.**
