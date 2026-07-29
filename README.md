<div align="center">

<!-- Animated Header Banner -->
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 220" width="100%" height="220">
  <defs>
    <!-- Background Gradient -->
    <linearGradient id="bgGradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0d1117">
        <animate attributeName="stop-color" values="#0d1117; #161b22; #1f242d; #0d1117" dur="10s" repeatCount="indefinite" />
      </stop>
      <stop offset="50%" stop-color="#161b22">
        <animate attributeName="stop-color" values="#161b22; #2d1b3f; #162a3f; #161b22" dur="10s" repeatCount="indefinite" />
      </stop>
      <stop offset="100%" stop-color="#0a0c10">
        <animate attributeName="stop-color" values="#0a0c10; #0d1117; #121820; #0a0c10" dur="10s" repeatCount="indefinite" />
      </stop>
    </linearGradient>

    <!-- Glowing Text Gradient -->
    <linearGradient id="textGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#FF416C">
        <animate attributeName="stop-color" values="#FF416C; #8A2387; #00F2FE; #FF416C" dur="6s" repeatCount="indefinite"/>
      </stop>
      <stop offset="50%" stop-color="#8A2387">
        <animate attributeName="stop-color" values="#8A2387; #E94057; #4FACFE; #8A2387" dur="6s" repeatCount="indefinite"/>
      </stop>
      <stop offset="100%" stop-color="#FF4B2B">
        <animate attributeName="stop-color" values="#FF4B2B; #F27121; #00C6FF; #FF4B2B" dur="6s" repeatCount="indefinite"/>
      </stop>
    </linearGradient>

    <!-- Subtitle Glow Gradient -->
    <linearGradient id="subGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#00F2FE"/>
      <stop offset="100%" stop-color="#4FACFE"/>
    </linearGradient>

    <!-- Card Border Gradient -->
    <linearGradient id="borderGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#FF416C" stop-opacity="0.8"/>
      <stop offset="50%" stop-color="#8A2387" stop-opacity="0.3"/>
      <stop offset="100%" stop-color="#00F2FE" stop-opacity="0.8"/>
    </linearGradient>

    <!-- Drop Shadow Filter -->
    <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="8" result="blur" />
      <feComposite in="SourceGraphic" in2="blur" operator="over" />
    </filter>
  </defs>

  <!-- Card Background -->
  <rect width="896" height="216" x="2" y="2" rx="20" ry="20" fill="url(#bgGradient)" stroke="url(#borderGrad)" stroke-width="2"/>

  <!-- Decorative Particle Circles -->
  <circle cx="80" cy="50" r="3" fill="#FF416C" opacity="0.6">
    <animate attributeName="r" values="2;5;2" dur="3s" repeatCount="indefinite"/>
    <animate attributeName="opacity" values="0.3;0.9;0.3" dur="3s" repeatCount="indefinite"/>
  </circle>
  <circle cx="820" cy="160" r="4" fill="#00F2FE" opacity="0.7">
    <animate attributeName="r" values="3;7;3" dur="4s" repeatCount="indefinite"/>
    <animate attributeName="opacity" values="0.4;1;0.4" dur="4s" repeatCount="indefinite"/>
  </circle>
  <circle cx="780" cy="40" r="2.5" fill="#F27121" opacity="0.5">
    <animate attributeName="r" values="1;4;1" dur="2.5s" repeatCount="indefinite"/>
  </circle>
  <circle cx="120" cy="170" r="3.5" fill="#8A2387" opacity="0.6">
    <animate attributeName="r" values="2;6;2" dur="3.5s" repeatCount="indefinite"/>
  </circle>

  <!-- Title Text -->
  <text x="450" y="85" text-anchor="middle" font-family="'Segoe UI', Ubuntu, Helvetica, sans-serif" font-weight="900" font-size="38" fill="url(#textGrad)" filter="url(#glow)" letter-spacing="2">
    GUEST ACCOUNT CHECKER
  </text>

  <!-- Subtitle Text -->
  <text x="450" y="125" text-anchor="middle" font-family="'Segoe UI', Ubuntu, Helvetica, sans-serif" font-weight="600" font-size="16" fill="url(#subGrad)" letter-spacing="1">
    ⚡ Bulk Free Fire Guest Verification Engine • Fast, Async & Precise ⚡
  </text>

  <!-- Feature Tags in SVG -->
  <g transform="translate(180, 150)">
    <!-- Tag 1 -->
    <rect x="0" y="0" width="130" height="28" rx="14" fill="#FF416C" fill-opacity="0.15" stroke="#FF416C" stroke-width="1"/>
    <text x="65" y="18" text-anchor="middle" font-family="sans-serif" font-size="11" font-weight="bold" fill="#FF416C">🔥 High Speed</text>

    <!-- Tag 2 -->
    <rect x="150" y="0" width="130" height="28" rx="14" fill="#8A2387" fill-opacity="0.15" stroke="#8A2387" stroke-width="1"/>
    <text x="215" y="18" text-anchor="middle" font-family="sans-serif" font-size="11" font-weight="bold" fill="#DDA0DD">🛡️ OAuth & Proto</text>

    <!-- Tag 3 -->
    <rect x="300" y="0" width="130" height="28" rx="14" fill="#00F2FE" fill-opacity="0.15" stroke="#00F2FE" stroke-width="1"/>
    <text x="365" y="18" text-anchor="middle" font-family="sans-serif" font-size="11" font-weight="bold" fill="#00F2FE">⚡ Async Concurrency</text>

    <!-- Tag 4 -->
    <rect x="450" y="0" width="130" height="28" rx="14" fill="#F27121" fill-opacity="0.15" stroke="#F27121" stroke-width="1"/>
    <text x="515" y="18" text-anchor="middle" font-family="sans-serif" font-size="11" font-weight="bold" fill="#F27121">📱 Termux Ready</text>
  </g>
</svg>

<br/>

<!-- Animated Typing Terminal SVG -->
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 60" width="100%" height="60">
  <rect width="800" height="60" rx="10" fill="#0d1117" stroke="#30363d" stroke-width="1.5"/>
  <circle cx="20" cy="30" r="6" fill="#ff5f56"/>
  <circle cx="40" cy="30" r="6" fill="#ffbd2e"/>
  <circle cx="60" cy="30" r="6" fill="#27c93f"/>
  <text x="85" y="35" font-family="'Courier New', Courier, monospace" font-size="14" fill="#58a6ff" font-weight="bold">$</text>
  <text x="100" y="35" font-family="'Courier New', Courier, monospace" font-size="14" fill="#e6edf3">
    python3 guest_checker.py --json data/guests.json --concurrent 5
  </text>
  <rect x="635" y="22" width="8" height="18" fill="#58a6ff">
    <animate attributeName="opacity" values="1;0;1" dur="0.8s" repeatCount="indefinite"/>
  </rect>
</svg>

<br/><br/>

<!-- Badges Bar -->
[![Python Version](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20macOS%20%7C%20Windows%20%7C%20Termux-orange?style=for-the-badge&logo=android)](https://termux.dev/)
[![Free Fire Protocol](https://img.shields.io/badge/Protocol-Garena%20OB54-red?style=for-the-badge&logo=freefire)](https://ff.garena.com/)
[![Code Style](https://img.shields.io/badge/Code%20Style-AsyncIO-blueviolet?style=for-the-badge)](https://docs.python.org/3/library/asyncio.html)

<br/>

<!-- Animated Pulse Status Badge -->
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 650 30" width="650" height="30">
  <style>
    .pulse { animation: pulse 1.5s infinite; }
    @keyframes pulse { 0% { fill-opacity: 1; } 50% { fill-opacity: 0.3; } 100% { fill-opacity: 1; } }
  </style>
  <rect width="650" height="30" rx="6" fill="#161b22" stroke="#30363d" stroke-width="1"/>
  <circle cx="20" cy="15" r="5" fill="#2ea44f" class="pulse"/>
  <text x="32" y="19" font-family="sans-serif" font-size="11" font-weight="bold" fill="#7ee787">SYSTEM STATUS: ONLINE</text>
  <text x="210" y="19" font-family="sans-serif" font-size="11" fill="#8b949e">|</text>
  <text x="230" y="19" font-family="sans-serif" font-size="11" font-weight="bold" fill="#58a6ff">OAUTH GATEWAY: OPERATIONAL</text>
  <text x="440" y="19" font-family="sans-serif" font-size="11" fill="#8b949e">|</text>
  <text x="460" y="19" font-family="sans-serif" font-size="11" font-weight="bold" fill="#d2a8ff">PROTOBUF v4.24 READY</text>
</svg>

</div>

---

## 📖 Table of Contents

- [🌟 Overview](#-overview)
- [✨ Key Features](#-key-features)
- [❓ Why Use Guest Account Checker?](#-why-use-guest-account-checker)
- [🏛️ System Architecture](#️-system-architecture)
- [🔄 How It Works (Authentication Pipeline)](#-how-it-works-authentication-pipeline)
- [📊 Status Distribution & Metrics](#-status-distribution--metrics)
- [📋 Prerequisites](#-prerequisites)
- [🚀 Installation Guide](#-installation-guide)
  - [Option 1: Linux / macOS / Windows WSL](#option-1-linux--macos--windows-wsl)
  - [Option 2: Android Termux (Complete Walkthrough)](#option-2-android-termux-complete-walkthrough)
  - [Option 3: Virtual Environment (Recommended)](#option-3-virtual-environment-recommended)
- [💻 Usage & CLI Reference](#-usage--cli-reference)
  - [Command Arguments & Flags](#command-arguments--flags)
  - [Input File Formats](#input-file-formats)
  - [Output JSON Structure](#output-json-structure)
- [🐍 Programmatic Python API](#-programmatic-python-api)
- [🖼️ Interactive Visual Interface (ASCII Art)](#️-interactive-visual-interface-ascii-art)
- [🚨 Status Code & Error Reference](#-status-code--error-reference)
- [⚡ Performance Tuning & Concurrency](#-performance-tuning--concurrency)
- [🔧 Troubleshooting & FAQ](#-troubleshooting--faq)
- [📝 Changelog](#-changelog)
- [🤝 Contributing](#-contributing)
- [📜 License & Credits](#-license--credits)

---

## 🌟 Overview

**Free Fire Guest Account Checker** is a high-performance, asynchronous Python tool engineered to perform bulk verification and audit of Garena Free Fire guest accounts. 

Unlike traditional checkers that rely on browser emulation or heavy scraping frameworks, this tool communicates directly with Garena's official auth servers and game endpoint gateways using lightweight HTTPX requests and binary Protobuf packet decoding.

### What it does:
- 🔍 **Validates Credentials**: Checks whether guest UID and password credentials remain valid or revoked.
- 💀 **Detects Ban & Alive Status**: Distinguishes between active (`ALIVE`), banned (`BANNED`), dead (`DEAD`), or server-unreachable (`SERVER_DOWN`) accounts.
- 📊 **Extracts In-Depth Stats**: Pulls player nickname, account level, received likes, region, clan membership, signature, and account creation metadata.
- ⚡ **Asynchronous Concurrency**: Processes hundreds of accounts concurrently with configurable worker limits.
- 💾 **Automated Reports**: Generates detailed, structured JSON audit logs in `data/guest_report.json`.

---

## ✨ Key Features

- [x] **Direct Protobuf Integration**: Utilizes compiled `.proto` definitions (`data_pb2`, `dev_generator_pb2`, `MajorLoginRes_pb2`) for ultra-fast binary payload parsing.
- [x] **Dynamic Endpoint Resolution**: Automatically decrypts and extracts dynamic `GetLoginData` URLs returned from the MajorLogin authentication stage.
- [x] **OAuth Resiliency**: Determines account validity via OAuth token acquisition even when game login servers undergo maintenance (`503 Server Down`).
- [x] **Dual Source Support**: Reads guest account credentials seamlessly from both JSON files (`guests.json`, `level_accounts.json`) and SQLite database files (`guests.db`).
- [x] **Termux Optimized**: Fully compatible with Android Termux environments without requiring root privileges or heavy graphical dependencies.
- [x] **AES Crypto Suite**: Features AES-CBC encryption with PKCS7 padding to construct official Free Fire login request packets.
- [x] **Zero Memory Bloat**: Streamlined execution footprint utilizing PyCryptodome and HTTPX for minimal RAM usage under high concurrency.
- [x] **Pretty Terminal UI**: Displays real-time colored ANSI progress reports, tabular summary view, and formatted JSON output.

---

## ❓ Why Use Guest Account Checker?

| Feature / Aspect | Guest Account Checker | Traditional Selenium / Scraper | Manual In-Game Checking |
| :--- | :---: | :---: | :---: |
| **Speed per Account** | ⚡ **~200 ms** | 🐢 10-15 seconds | ⏳ 1-2 minutes |
| **Resource Usage** | 🪶 `< 30 MB RAM` | 🐘 `> 800 MB RAM` | 📱 Device Dependent |
| **Server Maintenance Detection** | ✅ **Supported** (OAuth layer) | ❌ Fails silently | ❌ Blocked at login |
| **Detailed Player Profile** | ✅ **Full Proto Extraction** | ⚠️ Partial text scraping | 👁️ Visual inspect |
| **Headless / CLI Execution** | ✅ **Native** | ⚠️ Requires Virtual Display | ❌ Not possible |
| **Termux Compatibility** | ✅ **100% Native** | ❌ Complex / Unstable | ❌ N/A |

---

## 🏛️ System Architecture

The following diagram illustrates how the Guest Account Checker coordinates input readers, asynchronous workers, crypto modules, and output formats:

<div align="center">

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 850 420" width="100%" height="420">
  <defs>
    <linearGradient id="boxGrad1" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#1f242d"/>
      <stop offset="100%" stop-color="#0d1117"/>
    </linearGradient>
    <linearGradient id="accentOrange" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#FF416C"/>
      <stop offset="100%" stop-color="#FF4B2B"/>
    </linearGradient>
    <linearGradient id="accentBlue" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#00F2FE"/>
      <stop offset="100%" stop-color="#4FACFE"/>
    </linearGradient>
    <linearGradient id="accentPurple" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#8A2387"/>
      <stop offset="100%" stop-color="#E94057"/>
    </linearGradient>
    <linearGradient id="accentGreen" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#11998e"/>
      <stop offset="100%" stop-color="#38ef7d"/>
    </linearGradient>
    <filter id="shadow" x="-10%" y="-10%" width="120%" height="120%">
      <feGaussianBlur stdDeviation="4" result="blur"/>
      <feComposite in="SourceGraphic" in2="blur" operator="over"/>
    </filter>
  </defs>

  <!-- Input Sources Box -->
  <g transform="translate(30, 40)">
    <rect width="220" height="150" rx="12" fill="url(#boxGrad1)" stroke="#FF416C" stroke-width="2" filter="url(#shadow)"/>
    <rect x="0" y="0" width="220" height="36" rx="12" fill="url(#accentOrange)"/>
    <text x="110" y="23" text-anchor="middle" font-family="sans-serif" font-weight="bold" fill="white" font-size="14">📥 Credentials Input</text>
    <text x="20" y="65" font-family="monospace" font-size="12" fill="#e6edf3">• data/guests.json</text>
    <text x="20" y="90" font-family="monospace" font-size="12" fill="#e6edf3">• data/level_accounts.json</text>
    <text x="20" y="115" font-family="monospace" font-size="12" fill="#e6edf3">• data/guests.db (SQLite)</text>
    <text x="20" y="140" font-family="monospace" font-size="12" fill="#8b949e">• CLI Arguments</text>
  </g>

  <!-- Async Engine Box -->
  <g transform="translate(315, 30)">
    <rect width="220" height="170" rx="12" fill="url(#boxGrad1)" stroke="#00F2FE" stroke-width="2" filter="url(#shadow)"/>
    <rect x="0" y="0" width="220" height="36" rx="12" fill="url(#accentBlue)"/>
    <text x="110" y="23" text-anchor="middle" font-family="sans-serif" font-weight="bold" fill="white" font-size="14">⚡ Async Checker Engine</text>
    <text x="20" y="62" font-family="sans-serif" font-size="12" fill="#e6edf3">guest_checker.py</text>
    <text x="20" y="85" font-family="sans-serif" font-size="11" fill="#8b949e">• Concurrency Semaphore</text>
    <text x="20" y="105" font-family="sans-serif" font-size="11" fill="#8b949e">• Asyncio Task Queue</text>
    <text x="20" y="125" font-family="sans-serif" font-size="11" fill="#8b949e">• HTTPX Connection Pool</text>
    <text x="20" y="148" font-family="sans-serif" font-size="11" fill="#8b949e">• Signal Handler</text>
  </g>

  <!-- Auth & Info Core Box -->
  <g transform="translate(600, 40)">
    <rect width="220" height="150" rx="12" fill="url(#boxGrad1)" stroke="#8A2387" stroke-width="2" filter="url(#shadow)"/>
    <rect x="0" y="0" width="220" height="36" rx="12" fill="url(#accentPurple)"/>
    <text x="110" y="23" text-anchor="middle" font-family="sans-serif" font-weight="bold" fill="white" font-size="14">🔐 Protocol & Crypto</text>
    <text x="20" y="65" font-family="sans-serif" font-size="11" fill="#e6edf3">• LevelAuth (OAuth 2.0)</text>
    <text x="20" y="88" font-family="sans-serif" font-size="11" fill="#e6edf3">• MajorLogin (AES CBC)</text>
    <text x="20" y="111" font-family="sans-serif" font-size="11" fill="#e6edf3">• GuestInfo (PersonalShow)</text>
    <text x="20" y="134" font-family="sans-serif" font-size="11" fill="#e6edf3">• Protobuf Decoders</text>
  </g>

  <!-- Output Box -->
  <g transform="translate(315, 250)">
    <rect width="220" height="130" rx="12" fill="url(#boxGrad1)" stroke="#38ef7d" stroke-width="2" filter="url(#shadow)"/>
    <rect x="0" y="0" width="220" height="36" rx="12" fill="url(#accentGreen)"/>
    <text x="110" y="23" text-anchor="middle" font-family="sans-serif" font-weight="bold" fill="white" font-size="14">📊 Output & Export</text>
    <text x="20" y="62" font-family="monospace" font-size="12" fill="#e6edf3">• Terminal ANSI Report</text>
    <text x="20" y="85" font-family="monospace" font-size="12" fill="#e6edf3">• guest_report.json</text>
    <text x="20" y="108" font-family="monospace" font-size="12" fill="#8b949e">• SQLite Status Sync</text>
  </g>

  <!-- Connective Arrows -->
  <path d="M 250 115 L 315 115" stroke="#FF416C" stroke-width="3" fill="none" marker-end="url(#arrow)"/>
  <path d="M 535 115 L 600 115" stroke="#00F2FE" stroke-width="3" fill="none" marker-end="url(#arrow)"/>
  <path d="M 425 200 L 425 250" stroke="#38ef7d" stroke-width="3" fill="none" marker-end="url(#arrow)"/>

  <!-- Arrowhead Marker -->
  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#00F2FE"/>
    </marker>
  </defs>
</svg>

</div>

---

## 🔄 How It Works (Authentication Pipeline)

The account verification lifecycle comprises **3 sequential stages**:

```
 ┌────────────────┐       ┌────────────────┐       ┌─────────────────────┐
 │    Stage 1     │       │    Stage 2     │       │       Stage 3       │
 │   OAuth Auth   │ ────> │   MajorLogin   │ ────> │  Player Personal    │
 │ (Account Check)│       │  (Gateway URL) │       │   Show (Protobuf)   │
 └────────────────┘       └────────────────┘       └─────────────────────┘
```

<div align="center">

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 820 300" width="100%" height="300">
  <defs>
    <linearGradient id="stage1" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#2d3748"/>
      <stop offset="100%" stop-color="#1a202c"/>
    </linearGradient>
  </defs>

  <!-- Stage 1 Card -->
  <g transform="translate(20, 30)">
    <rect width="240" height="230" rx="10" fill="url(#stage1)" stroke="#4A5568" stroke-width="2"/>
    <rect width="240" height="35" rx="10" fill="#3182CE"/>
    <text x="120" y="22" text-anchor="middle" font-family="sans-serif" font-weight="bold" fill="white" font-size="13">STAGE 1: OAuth Verification</text>
    <text x="15" y="60" font-family="sans-serif" font-size="11" fill="#E2E8F0">• Sends OpenID Request</text>
    <text x="15" y="80" font-family="sans-serif" font-size="11" fill="#CBD5E0">  UID + Password</text>
    <text x="15" y="110" font-family="sans-serif" font-size="11" fill="#E2E8F0">• Checks Garena Auth Server</text>
    <text x="15" y="140" font-family="sans-serif" font-size="11" fill="#68D391">✔ Returns: OAuth Token</text>
    <text x="15" y="165" font-family="sans-serif" font-size="11" fill="#FC8181">❌ If Invalid -> DEAD</text>
    <text x="15" y="190" font-family="sans-serif" font-size="11" fill="#E53E3E">❌ If Banned -> BANNED</text>
  </g>

  <!-- Connector 1 -->
  <path d="M 260 145 L 290 145" stroke="#3182CE" stroke-width="3" fill="none"/>
  <polygon points="290,140 300,145 290,150" fill="#3182CE"/>

  <!-- Stage 2 Card -->
  <g transform="translate(300, 30)">
    <rect width="240" height="230" rx="10" fill="url(#stage1)" stroke="#4A5568" stroke-width="2"/>
    <rect width="240" height="35" rx="10" fill="#805AD5"/>
    <text x="120" y="22" text-anchor="middle" font-family="sans-serif" font-weight="bold" fill="white" font-size="13">STAGE 2: MajorLogin Gateway</text>
    <text x="15" y="60" font-family="sans-serif" font-size="11" fill="#E2E8F0">• AES-CBC Encrypted Payload</text>
    <text x="15" y="80" font-family="sans-serif" font-size="11" fill="#CBD5E0">  Template Hex + Token</text>
    <text x="15" y="110" font-family="sans-serif" font-size="11" fill="#E2E8F0">• Parses Protobuf Response</text>
    <text x="15" y="140" font-family="sans-serif" font-size="11" fill="#68D391">✔ Extracts: Dynamic Server URL</text>
    <text x="15" y="165" font-family="sans-serif" font-size="11" fill="#CBD5E0">  AES Key & IV + Session JWT</text>
    <text x="15" y="190" font-family="sans-serif" font-size="11" fill="#F6AD55">⚠️ If 503 -> SERVER_DOWN</text>
  </g>

  <!-- Connector 2 -->
  <path d="M 540 145 L 570 145" stroke="#805AD5" stroke-width="3" fill="none"/>
  <polygon points="570,140 580,145 570,150" fill="#805AD5"/>

  <!-- Stage 3 Card -->
  <g transform="translate(580, 30)">
    <rect width="240" height="230" rx="10" fill="url(#stage1)" stroke="#4A5568" stroke-width="2"/>
    <rect width="240" height="35" rx="10" fill="#38A169"/>
    <text x="120" y="22" text-anchor="middle" font-family="sans-serif" font-weight="bold" fill="white" font-size="13">STAGE 3: PlayerPersonalShow</text>
    <text x="15" y="60" font-family="sans-serif" font-size="11" fill="#E2E8F0">• Encrypts Target UID</text>
    <text x="15" y="80" font-family="sans-serif" font-size="11" fill="#CBD5E0">  dev_generator protobuf</text>
    <text x="15" y="110" font-family="sans-serif" font-size="11" fill="#E2E8F0">• Queries GetPlayerPersonalShow</text>
    <text x="15" y="140" font-family="sans-serif" font-size="11" fill="#68D391">✔ Decodes data_pb2 AccountInfo</text>
    <text x="15" y="165" font-family="sans-serif" font-size="11" fill="#68D391">  (Level, Likes, Nick, Clan)</text>
    <text x="15" y="190" font-family="sans-serif" font-size="11" fill="#38A169">🎉 Status -> ALIVE</text>
  </g>
</svg>

</div>

---

## 📊 Status Distribution & Metrics

Below is an overview of how account statuses are categorized during check execution:

<div align="center">

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 180" width="100%" height="180">
  <rect width="700" height="180" rx="12" fill="#0d1117" stroke="#30363d" stroke-width="1.5"/>

  <!-- Meter Bar 1: ALIVE -->
  <g transform="translate(30, 25)">
    <text x="0" y="15" font-family="sans-serif" font-size="12" font-weight="bold" fill="#7ee787">ALIVE (Valid & Reachable)</text>
    <rect x="220" y="2" width="400" height="18" rx="9" fill="#21262d"/>
    <rect x="220" y="2" width="340" height="18" rx="9" fill="#238636"/>
    <text x="630" y="15" font-family="monospace" font-size="12" fill="#7ee787">85%</text>
  </g>

  <!-- Meter Bar 2: SERVER_DOWN -->
  <g transform="translate(30, 65)">
    <text x="0" y="15" font-family="sans-serif" font-size="12" font-weight="bold" fill="#d29922">SERVER_DOWN (OAuth Valid)</text>
    <rect x="220" y="2" width="400" height="18" rx="9" fill="#21262d"/>
    <rect x="220" y="2" width="40" height="18" rx="9" fill="#9e6a03"/>
    <text x="630" y="15" font-family="monospace" font-size="12" fill="#d29922">10%</text>
  </g>

  <!-- Meter Bar 3: BANNED -->
  <g transform="translate(30, 105)">
    <text x="0" y="15" font-family="sans-serif" font-size="12" font-weight="bold" fill="#f85149">BANNED (Suspended)</text>
    <rect x="220" y="2" width="400" height="18" rx="9" fill="#21262d"/>
    <rect x="220" y="2" width="16" height="18" rx="8" fill="#da3633"/>
    <text x="630" y="15" font-family="monospace" font-size="12" fill="#f85149">3%</text>
  </g>

  <!-- Meter Bar 4: DEAD -->
  <g transform="translate(30, 145)">
    <text x="0" y="15" font-family="sans-serif" font-size="12" font-weight="bold" fill="#8b949e">DEAD (Invalid Password)</text>
    <rect x="220" y="2" width="400" height="18" rx="9" fill="#21262d"/>
    <rect x="220" y="2" width="8" height="18" rx="4" fill="#484f58"/>
    <text x="630" y="15" font-family="monospace" font-size="12" fill="#8b949e">2%</text>
  </g>
</svg>

</div>

---

## 📋 Prerequisites

Before installing, ensure your environment meets the following requirements:

- **Python**: Version `3.9` or higher
- **Package Manager**: `pip` (Python Package Index)
- **C Compiler Tools** (for PyCryptodome on Termux / BSD systems)
- **Network**: Internet connection with HTTP/HTTPS access to Garena endpoints (`openfire.garena.com`)

---

## 🚀 Installation Guide

### Option 1: Linux / macOS / Windows WSL

1. **Clone the repository**:
   ```bash
   git clone https://github.com/ISMAILdz13/guest-account-checker.git
   cd guest-account-checker
   ```

2. **Install core dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Verify installation**:
   ```bash
   python3 guest_checker.py -h
   ```

---

### Option 2: Android Termux (Complete Walkthrough)

Termux users can easily run the checker directly on mobile devices:

```bash
# Step 1: Update package database & install prerequisites
pkg update && pkg upgrade -y
pkg install python git clang libcrypt -y

# Step 2: Clone repository
git clone https://github.com/ISMAILdz13/guest-account-checker.git
cd guest-account-checker

# Step 3: Upgrade pip & install wheel build dependencies
pip install --upgrade pip setuptools wheel

# Step 4: Install required Python packages
pip install -r requirements.txt

# Step 5: Run sample check
python3 guest_checker.py
```

> 💡 **Termux Tip**: If `pycryptodome` installation fails, ensure `clang` and `libcrypt` packages are installed via `pkg install clang libcrypt`.

---

### Option 3: Virtual Environment (Recommended)

Isolated python environments prevent library conflicts:

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On Linux / macOS:
source venv/bin/activate
# On Windows (PowerShell):
.env\Scripts\Activate.ps1

# Install dependencies inside venv
pip install -r requirements.txt
```

---

## 💻 Usage & CLI Reference

### Basic Command Execution

To check accounts using default sample data (`data/guests.json`):

```bash
python3 guest_checker.py
```

### Command Arguments & Flags

| Flag | Short | Type | Default | Description |
| :--- | :---: | :---: | :---: | :--- |
| `--json` | `-j` | Path | `data/guests.json` | Path to custom input JSON account file |
| `--concurrent` | `-c` | Integer | `3` | Maximum concurrent async workers (1-20) |
| `--help` | `-h` | Flag | None | Display CLI help menu and exit |

### Custom Input File Execution Examples

1. **Specify custom JSON file**:
   ```bash
   python3 guest_checker.py --json my_accounts.json
   ```

2. **Increase concurrency to 10 parallel workers**:
   ```bash
   python3 guest_checker.py --json data/guests.json --concurrent 10
   ```

3. **Check accounts from `level_accounts.json`**:
   ```bash
   python3 guest_checker.py --json data/level_accounts.example.json
   ```

---

### Input File Formats

The checker automatically detects and processes two standard input formats:

#### Format A: JSON Key-Value Map (`guests.json`)
```json
{
  "5842511863": {
    "password": "YOUR_GUEST_PASSWORD_HEX_1",
    "name": "BOT5S8F7S"
  },
  "5842511867": {
    "password": "YOUR_GUEST_PASSWORD_HEX_2",
    "name": "BOTWGC5RT"
  }
}
```

#### Format B: JSON Account List (`level_accounts.example.json`)
```json
[
  {
    "uid": "5842511863",
    "password": "YOUR_GUEST_PASSWORD_HEX_1",
    "name": "BOT5S8F7S"
  },
  {
    "uid": "5842511867",
    "password": "YOUR_GUEST_PASSWORD_HEX_2",
    "name": "BOTWGC5RT"
  }
]
```

---

### Output JSON Structure

When processing completes, results are exported to `data/guest_report.json`:

```json
{
  "timestamp": "2026-07-29T18:18:00.123456",
  "total_checked": 3,
  "summary": {
    "alive": 3,
    "banned": 0,
    "dead": 0,
    "server_down": 0,
    "error": 0
  },
  "accounts": [
    {
      "uid": "5842511863",
      "nickname": "🔥GUEST_PRO🔥",
      "status": "ALIVE",
      "level": 42,
      "likes": 1280,
      "region": "INDONESIA",
      "clan": "ALPHA_LEGION",
      "gender": "Male",
      "language": "EN",
      "checked_at": "2026-07-29T18:18:01.002100"
    }
  ]
}
```

---

## 🐍 Programmatic Python API

You can import and integrate the `LevelAuth` and `GuestInfo` modules into your own custom Python automation scripts:

```python
import asyncio
import httpx
from src.level.auth import LevelAuth
from src.level.guest_info import GuestInfo

async def verify_single_guest(uid: str, password_hex: str):
    async with httpx.AsyncClient(timeout=15.0) as http:
        # Step 1: Authenticate & obtain OAuth token
        auth = LevelAuth(http)
        oauth_res = await auth.login_guest(uid, password_hex)
        
        if not oauth_res.get("success"):
            print(f"[-] OAuth Login Failed: {oauth_res.get('error')}")
            return
        
        print(f"[+] OAuth Token Acquired: {oauth_res['token'][:15]}...")
        
        # Step 2: MajorLogin Gateway
        major_res = await auth.major_login(uid, oauth_res["token"])
        if not major_res.get("success"):
            print(f"[!] MajorLogin Gateway maintenance: {major_res.get('error')}")
            return
            
        # Step 3: Fetch Full Player Profile via Protobuf
        info_service = GuestInfo(http)
        player = await info_service._get_player_personal_show(uid, major_res["token"])
        
        if player:
            print(f"🎉 Account Active! Name: {player['nickname']} | Lvl: {player['level']} | Likes: {player['likes']}")

# Run async function
asyncio.run(verify_single_guest("5842511863", "a1b2c3d4e5f60718"))
```

---

## 🖼️ Interactive Visual Interface (ASCII Art)

Below is a representation of the colorful terminal interface rendered during check operations:

```
  ========================================
      GUEST ACCOUNT CHECKER  v1.0        
  ========================================

  Found 3 accounts:
  5842511863      BOT5S8F7S    (guests.json)
  5842511867      BOTWGC5RT    (guests.json)
  5842511864      BOT91X0NN    (guests.json)

  Checking 3 accounts...
  (OAuth works even if game servers are down)

  [1/3] 5842511863      ALIVE  lvl=42 likes=1280 nick=GUEST_PRO
  [2/3] 5842511867      ALIVE  lvl=15 likes=320  nick=FREE_BOT
  [3/3] 5842511864      BANNED oauth=alive, account suspended

  ========================================
    GUEST ACCOUNT REPORT
  ========================================

  UID             STATUS   NICK          LVL LIKES REGION CLAN        
  --------------- -------- ------------ ---- ----- ------ ------------
  5842511863      ALIVE    GUEST_PRO      42  1280 ID     ALPHA_LEGION
  5842511867      ALIVE    FREE_BOT       15   320 BR     None        
  5842511864      BANNED   SUSPENDED_1     1     0 US     None        

  ----------------------------------------
  Summary:
  Alive:       2
  Banned:      1
  Server Down: 0
  Total:       3
  ========================================

  Report saved to: data/guest_report.json

  Done!
```

---

## 🚨 Status Code & Error Reference

| Status Code | Meaning | Cause | Action Required |
| :--- | :--- | :--- | :--- |
| `ALIVE` | Account active and healthy | Account logged in successfully and profile extracted | None (Valid Account) |
| `SERVER_DOWN` | OAuth valid, game server down | Garena login servers returning `503 Service Unavailable` | Retry later or check server status |
| `BANNED` | Account suspended | Garena security ban triggered on guest account | Quarantine or remove account |
| `DEAD` | Credentials rejected | Incorrect password hex or deleted guest profile | Re-extract or regenerate guest account |
| `ERROR` | Network/Timeout error | Connection timeout, proxy failure, or rate limiting | Reduce concurrency or rotate IP |

---

## ⚡ Performance Tuning & Concurrency

To achieve maximum check throughput when auditing thousands of accounts:

1. **Adjust Concurrency**: Use `--concurrent 10` or higher on stable broadband connections.
2. **Batch Inputs**: Divide large input files into chunks of 1,000 accounts.
3. **Avoid Over-Threading**: Setting `--concurrent` higher than `20` may trigger temporary IP rate-limiting from Garena auth endpoints.

---

## 🔧 Troubleshooting & FAQ

<details>
<summary><b>❓ Q1: ModuleNotFoundError: No module named 'Crypto'</b></summary>
<br/>
This occurs when <code>pycryptodome</code> is missing or superseded by legacy <code>crypto</code>.<br/>
<b>Solution:</b><br/>

```bash
pip uninstall crypto pycrypto
pip install --upgrade pycryptodome
```
</details>

<details>
<summary><b>❓ Q2: MajorLogin returns 503 Server Down</b></summary>
<br/>
This indicates Garena game login gateway maintenance or patch updates in your target region.<br/>
<b>Note:</b> OAuth verification still completes, confirming credential validity. Detailed stats (level/likes) will resume when Garena maintenance completes.
</details>

<details>
<summary><b>❓ Q3: How do I generate new guest accounts?</b></summary>
<br/>
Guest accounts can be created using dynamic device generators. Look into the included protobuf definitions under <code>src/level/dev_generator_pb2.py</code>.
</details>

<details>
<summary><b>❓ Q4: Can this tool run on low-end hardware or Android?</b></summary>
<br/>
Yes! The memory footprint is under 30MB, making it ideal for low-spec VPS instances, Raspberry Pi, and Android phones running Termux.
</details>

---

## 📝 Changelog

### v1.0.0 (2026-07-29)
- 🎉 Initial public release.
- ⚡ Full asynchronous check engine supporting HTTPX.
- 🔐 OAuth 2.0 & MajorLogin AES payload handler.
- 📜 Protobuf response parser for player stats (Level, Likes, Clan, Region).
- 📊 Formatted terminal ANSI output & JSON report export.

---

## 🤝 Contributing

Contributions are welcome! Follow these steps to contribute:

1. Fork the repository (`https://github.com/ISMAILdz13/guest-account-checker`)
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'feat: Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📜 License & Credits

### License
Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for details.

### Author & Credits
- **Author**: [ISMAILdz13](https://github.com/ISMAILdz13)
- **Protocol Research & Protobuf Definitions**: Garena Free Fire OB54 Protocol Analysis.
- **Libraries Used**: `httpx`, `pycryptodome`, `protobuf`, `PyJWT`.

---

<div align="center">

**[⭐ Star this repository on GitHub](https://github.com/ISMAILdz13/guest-account-checker)** if you found it useful!

</div>
