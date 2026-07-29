<div align="center">

<!-- Animated Header Banner -->
![](assets/banner.svg)

<br/>

<!-- Animated Typing Terminal SVG -->
![](assets/graphic-1.svg)

<br/><br/>

<!-- Badges Bar -->
[![Python Version](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20macOS%20%7C%20Windows%20%7C%20Termux-orange?style=for-the-badge&logo=android)](https://termux.dev/)
[![Free Fire Protocol](https://img.shields.io/badge/Protocol-Garena%20OB54-red?style=for-the-badge&logo=freefire)](https://ff.garena.com/)
[![Code Style](https://img.shields.io/badge/Code%20Style-AsyncIO-blueviolet?style=for-the-badge)](https://docs.python.org/3/library/asyncio.html)

<br/>

<!-- Animated Pulse Status Badge -->
![](assets/status-badge.svg)

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

![](assets/status-badge-1.svg)

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

![](assets/status-badge-2.svg)

</div>

---

## 📊 Status Distribution & Metrics

Below is an overview of how account statuses are categorized during check execution:

<div align="center">

![](assets/graphic-5.svg)

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
