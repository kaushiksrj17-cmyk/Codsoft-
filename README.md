# Cloud File Storage System

[![Python Version](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/framework-Streamlit-red.svg)](https://streamlit.io/)
[![Cloud Storage](https://img.shields.io/badge/storage-Amazon%20S3-orange.svg)](https://aws.amazon.com/s3/)
[![Database](https://img.shields.io/badge/database-SQLite%203-lightgrey.svg)](https://www.sqlite.org/)
[![Testing](https://img.shields.io/badge/tests-183%20collected-success.svg)](#8-running-automated-tests)
[![Internship](https://img.shields.io/badge/CODSOFT-Cloud%20Computing%20Task%201-success.svg)](#)

A secure, multi-tenant cloud storage web application built with **Streamlit**, **Amazon Web Services (S3)**, **Boto3**, and an isolated **relational metadata store**. Developed for the **CODSOFT Cloud Computing Internship — Task 1**.

---

## 1. Project Title & Summary

The **Cloud File Storage System** is a private cloud storage solution engineered to provide secure file ingestion, automated versioning, cryptographic link sharing, storage quota management, and comprehensive audit compliance.

By offloading binary payload persistence directly to **Amazon S3** with **Server-Side AES-256 encryption** and managing metadata, access tokens, and activity logs within an isolated relational database, the system ensures high scalability, tenant isolation, and zero bandwidth bottlenecks on the web application tier.

---

## 2. Problem Statement & Objectives

### Problem Statement
Traditional on-premises or single-tier file storage architectures suffer from severe scalability bottlenecks, complex access delegation, vulnerable credential management, and high risks of path traversal or unrestricted file upload attacks. Organizations require a decoupled cloud architecture where web servers handle metadata and authentication, while cloud object stores handle encrypted binary data.

### Core Objectives
1. **Decoupled Architecture:** Separate binary object storage (Amazon S3) from relational metadata tracking (SQLite / PostgreSQL).
2. **Zero-Trust Security:** Enforce tenant isolation, server-side AES-256 encryption, strict file validation (MIME, extensions, sizes, path traversal defense), and salted password hashing (`bcrypt`).
3. **Cryptographic Link Sharing:** Provide time-limited share links supporting granular permissions (`view` vs. `download`), instant revocation, and recipient email restrictions.
4. **Capacity Governance:** Prevent denial-of-wallet and storage exhaustion through strict quota accounting, real-time telemetry, and usage limits.
5. **Audit Compliance:** Maintain immutable records of all authentication events, file mutations, link creations, downloads, and revocations.

---

## 3. Main Features

- 👤 **Account Authentication & RBAC:** Salted bcrypt password hashing (`rounds=12`), complexity enforcement, user registration, and Role-Based Access Control (`admin` and `user`).
- 📤 **Pre-Flight File Validation:** Automatic MIME detection, dangerous executable blocking (`.exe`, `.bat`, `.cmd`, `.sh`, `.ps1`), path traversal neutralization (`../`), and size limits (default: 50 MB).
- ☁️ **Private Amazon S3 Integration:** Boto3 client utilizing Signature Version 4 (`s3v4`), user-isolated prefixes (`users/{user_id}/files/`), and mandatory AES-256 server-side encryption.
- 📦 **File Versioning:** Automatic version numbering (`v1`, `v2`, ...), version history tracking with SHA-256 data integrity checksums, and historical file retrieval.
- ⏱️ **Granular Link Sharing:**
  - **View-Only Links:** Grants file preview and metadata access while strictly stripping S3 download URLs and download buttons.
  - **Download Links:** Generates short-lived (5-minute) presigned S3 URLs directly to the client browser.
  - **Instant Revocation:** Invalidate active links on-demand with real-time access termination.
  - **Email-Restricted Shares:** Enforce identity-based access for specific recipient emails.
- 📊 **Storage Quotas & Telemetry:** Configurable tenant quotas (default: 500 MB), real-time usage calculation, dynamic progress indicators, and storage analytics by category.
- 📜 **Immutable Audit Logging:** Persistent tracking of all operations (`AUTH_LOGIN`, `FILE_UPLOAD`, `FILE_DOWNLOAD`, `SHARE_CREATE`, `SHARE_REVOKE`, etc.) with timestamps, user IDs, and client IP addresses.

---

## 4. Technology Stack

| Layer | Component | Technology | Description |
| :--- | :--- | :--- | :--- |
| **Runtime** | Core Language | Python 3.11 | Modern Python with static type hinting (`from __future__ import annotations`). |
| **Presentation** | Web Dashboard | Streamlit 1.35+ | Multi-page interactive application (`pages/`) with custom Inter styling. |
| **Cloud Storage** | Object Store | Amazon S3 | Private bucket in `ap-south-1` with Block Public Access and AES-256 encryption. |
| **Cloud SDK** | AWS Client | Boto3 & Botocore | Signature Version 4, exponential backoff retries, presigned URL generator. |
| **Metadata DB** | Relational Store | SQLite 3 | Embedded SQL-92 database with foreign keys (`PRAGMA foreign_keys = ON;`). |
| **Security** | Password & Tokens | `bcrypt` & `secrets` | Adaptive salted hashing (`rounds=12`) and 256-bit URL-safe token minting. |
| **Integrity** | Checksums | `hashlib` (SHA-256) | File-level cryptographic hashing for tamper detection. |
| **Testing** | Test Automation | Pytest 8.4+ | 183 automated tests covering unit, security, regression, and opt-in AWS tests. |

---

## 5. Architecture & Component Responsibilities

### Architectural Request Flow
```text
[ Browser / Client ]
        │
        ▼ (HTTP / WebSocket)
[ Streamlit UI Dashboard ] (Presentation Tier)
        │
        ├──► [ Authentication & Permissions ] (RBAC, bcrypt, session state)
        │
        ├──► [ File & Sharing Services ] (Validation, quotas, tokens, rollback)
        │           │
        │           ├──► [ SQLite Metadata Store ] (users, files, versions, shares, audit)
        │           │
        │           └──► [ Amazon S3 Storage Manager ] (Boto3, SigV4, AES-256)
        │                       │
        │                       ▼ (TLS 1.3 encrypted REST)
        │               [ Private Amazon S3 Bucket ]
        │
        ▼ (Direct Stream via 5-min Presigned GET URL)
[ Amazon S3 Binary Stream ] ──► [ Client Browser Download ]
```

### Module Responsibilities (`src/` & `components/`)
- `src/config.py`: Centralized environment configuration (`.env`), validation, and safe AWS status masking.
- `src/auth.py`: Password hashing, complexity validation, user registration, and authentication lookup.
- `src/permissions.py`: Role evaluation (`admin` vs. `user`) and object-level permissions (`can_view`, `can_download`, `can_delete`).
- `src/file_validation.py`: Filename sanitization, path traversal neutralization, prohibited extension blocking, and SHA-256 checksums.
- `src/storage_quota.py`: Tenant quota checks, percentage usage computation, and human-readable byte formatting.
- `src/file_service.py`: High-level file management orchestrator: pre-flight checks, S3 upload, metadata persistence, version increments, quota tracking, and compensating rollback on failure.
- `src/file_versions.py`: Version numbering (`v1`, `v2`, ...), version recording, and historical version listing.
- `src/sharing.py`: 256-bit URL-safe token minting, expiration verification, access checking, revocation, and recipient filtering.
- `src/aws_storage.py`: Boto3 S3 client manager: connectivity health checks, tenant key partitioning, upload/download operations, and presigned URL generation.
- `src/activity_logger.py`: Compliance audit logging into the `activity_logs` table.
- `components/sidebar.py`: Standardized navigation sidebar, AWS connectivity status pill, user profile card, and authentication forms.
- `components/upload_panel.py`: Active upload panel with policy badges, real-time validation, and progress spinners.
- `components/file_table.py`: File explorer rendering, version history dialogs, download link generation, and share dialogs.

---

## 6. Project Directory Structure

```text
D:\Cloud_File_Storage_System\
├── app.py                     # Main dashboard application entry point
├── requirements.txt           # Project runtime dependencies
├── .env.example               # Configuration template with dummy placeholders
├── .gitignore                 # Excludes secrets, local databases, virtual environments
├── pytest.ini                 # Pytest configuration and test markers
├── README.md                  # Complete project documentation and setup guide
├── src/                       # Core application services and business logic
│   ├── __init__.py
│   ├── config.py              # Environment configuration & safe AWS status
│   ├── database.py            # SQLite database layer & schema initialization
│   ├── auth.py                # Password hashing and strength validation
│   ├── aws_storage.py         # Amazon S3 Boto3 client manager
│   ├── file_service.py        # File lifecycle orchestrator & transactional compensation
│   ├── file_validation.py     # Filename sanitization, extension & size checks
│   ├── file_versions.py       # File version tracking and numbering
│   ├── permissions.py         # Role-based access control & permission evaluator
│   ├── sharing.py             # Share token generation, expiration & revocation
│   ├── storage_quota.py       # Storage quota calculation and formatting
│   └── activity_logger.py     # Audit trail logging service
├── pages/                     # Streamlit multi-page dashboard views
│   ├── 1_My_Files.py          # Personal file explorer and upload zone
│   ├── 2_Storage_Analytics.py # Quota distribution and analytics
│   ├── 3_Shared_Files.py      # Active share links and permissions
│   ├── 4_Activity_History.py  # Audit compliance logs
│   ├── 5_Settings.py          # AWS connectivity diagnostic & policy settings
│   └── 6_Admin.py             # Tenant administration console
├── components/                # Reusable UI component modules
│   ├── __init__.py
│   ├── sidebar.py             # Standardized navigation sidebar with status badge
│   ├── dashboard_cards.py     # Modern metric and feature cards
│   ├── file_table.py          # File listing table, dialogs, and empty states
│   └── upload_panel.py        # Upload interface and policy indicators
├── data/                      # Local storage directory (SQLite database)
│   └── cloud_storage.db       # SQLite metadata database (git-ignored)
├── docs/                      # Architectural and operational documentation
│   ├── ARCHITECTURE.md        # Detailed system architecture, data flows, and tiers
│   ├── DEMO_GUIDE.md          # 5-7 minute demonstration script and sequence
│   ├── SCREENSHOT_CHECKLIST.md# Screenshot capture guide and privacy warnings
│   ├── SECURITY.md            # S3 private bucket, IAM & credential protection
│   └── AWS_SETUP.md           # Step-by-step AWS S3 bucket and IAM setup guide
├── scripts/                   # Automation scripts (Windows PowerShell & Python)
│   ├── setup.ps1              # Environment provisioning and DB initialization
│   ├── run.ps1                # Streamlit dashboard launch script
│   └── verify_phase_5c.py     # Automated headless UI and workflow verification runner
└── tests/                     # Comprehensive test suite (183 tests)
    ├── __init__.py
    ├── test_auth.py           # Authentication and password hashing tests
    ├── test_aws_storage.py    # S3 client, key builders, and opt-in live AWS tests
    ├── test_database.py       # SQLite connection and schema integration tests
    ├── test_file_service.py   # Upload, download, rollback, and service tests
    ├── test_file_validation.py# File validation and security unit tests
    ├── test_permissions.py    # RBAC and file permission unit tests
    ├── test_regression_edge_cases.py # Quotas, versions, edge cases, failure recovery
    ├── test_security_audit.py # Multi-tenant isolation and security audit tests
    ├── test_sharing.py        # Share tokens, expiration, revocation, email limits
    └── test_storage_quota.py  # Quota calculation and byte formatting tests
```

---

## 7. Setup & Installation (Windows PowerShell)

### Prerequisites
- **Operating System:** Windows 10 or Windows 11.
- **Python:** Python 3.11+ installed and available on PATH (`python --version`).
- **Shell:** Windows PowerShell 5.1 or PowerShell 7+.

### Automated Installation (Recommended)
Open PowerShell in the project root directory and execute the automated setup script:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\setup.ps1
```

The script performs the following tasks:
1. Validates Python 3.11+.
2. Provisions a project-isolated virtual environment at `.venv`.
3. Installs all required packages from `requirements.txt`.
4. Copies `.env.example` to `.env` if not already present.
5. Initializes the SQLite metadata schema inside `data/cloud_storage.db`.

### Manual Installation
If you prefer setting up manually:

```powershell
# 1. Create and activate Python virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Upgrade pip and install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

# 3. Create local configuration from template
if (-not (Test-Path .env)) { Copy-Item .env.example .env }

# 4. Initialize database schema
python -c "from src.database import init_db; init_db()"
```

---

## 8. Environment Configuration (`.env`)

Configuration is managed via `.env`. A template is provided in `.env.example`.

> [!CAUTION]
> **Security Rule:** Never commit `.env` or real AWS credentials to version control. The `.env` file is excluded in `.gitignore`.

### Configuration Parameters
```env
# Application Environment (options: development, testing, staging, production)
APP_ENV=development

# AWS S3 Configuration (Region and Private Bucket)
AWS_REGION=ap-south-1
S3_BUCKET_NAME=your-bucket-name-placeholder

# AWS IAM Credentials (Least-Privilege User)
AWS_ACCESS_KEY_ID=YOUR_AWS_ACCESS_KEY_ID_PLACEHOLDER
AWS_SECRET_ACCESS_KEY=YOUR_AWS_SECRET_ACCESS_KEY_PLACEHOLDER

# Metadata Database Path
DATABASE_PATH=data/cloud_storage.db

# Storage & Upload Policies
MAX_FILE_SIZE_MB=50
DEFAULT_STORAGE_QUOTA_MB=500
SHARE_LINK_MAX_EXPIRY_HOURS=168
```

- When valid AWS credentials and bucket name are configured, the application connects to **Live Amazon S3**.
- If AWS credentials are left as placeholders, the application runs safely in **Development Mode** with zero cloud charges.

---

## 9. Launching the Application

Start the application using the PowerShell launcher script:

```powershell
.\scripts\run.ps1
```

Or start Streamlit directly through the virtual environment:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

The application will be accessible at:  
👉 **`http://localhost:8501`**

### First-Time Login
1. On initial startup with an empty database, expand **✨ Create Initial Profile** in the sidebar.
2. Enter your initial administrator credentials (e.g., username `admin`, strong password).
3. Click **Create & Sign In** to access your dashboard.

---

## 10. Running Automated Tests

The repository includes a comprehensive 183-test automated test suite.

### Standard Regression Suite (Mocked S3 — Safe for CI/CD)
To run all unit, security, quota, permissions, and regression tests without making external network calls:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```
*Expected baseline: **181 passed, 2 skipped** (the 2 skipped tests are opt-in live AWS tests).*

### Live AWS Integration Tests (Opt-In Only)
Live tests interact with the real AWS S3 bucket using dedicated, isolated test prefixes (`diagnostics/phase2-...`) and perform immediate cleanup.

```powershell
$env:RUN_AWS_INTEGRATION_TESTS="1"
.\.venv\Scripts\python.exe -m pytest -q tests/test_aws_storage.py -k "test_live_s3"
```
*Expected result: **2 passed** against the live bucket.*

### Python Bytecode Compilation Verification
To verify clean compilation across all modules without syntax errors:

```powershell
.\.venv\Scripts\python.exe -m compileall -q src components pages tests
```
*Expected result: Clean exit with code 0.*

---

## 11. Security Considerations

1. **Private S3 Storage:** The Amazon S3 bucket has **Block All Public Access** enabled. Direct public access is strictly prohibited.
2. **Server-Side Encryption:** All uploads enforce `ServerSideEncryption: 'AES256'` (`SSE-S3`).
3. **Signed Presigned URLs:** File downloads use short-lived (5-minute) SigV4 presigned URLs generated server-side after permission checks.
4. **Tenant Isolation:** Files are stored under user-scoped prefixes: `users/{user_id}/files/v{version}/{filename}`. Tenants cannot read or manipulate another tenant's objects.
5. **Defense in Depth:** Input validation scrubs directory traversal (`../`), blocks executable extensions (`.exe`, `.bat`), and enforces file size and storage quota limits.
6. **Credential Protection:** Secrets and `.env` files are excluded from Git. The UI and logs sanitize all credentials and display only masked endings (e.g., `clo***26`, `ends in 2L6B`).

---

## 12. Known Limitations & Operational Notes

- **Offline Browser Automation:** Playwright browser driver binaries cannot be downloaded in air-gapped or restricted offline environments (`HTTP 404` from Azureedge CDN). Headless testing is accomplished using Streamlit's official `streamlit.testing.v1.AppTest` and HTTP probing.
- **SQLite Concurrency:** SQLite is suitable for single-instance development and demonstration. For high-concurrency production deployments, migrate to a managed PostgreSQL instance (e.g., Amazon RDS) by updating `DATABASE_PATH` and connection pooling in `src/database.py`.
- **IAM Permission Scoping:** The application IAM user operates under least-privilege principles (`s3:PutObject`, `s3:GetObject`, `s3:DeleteObject`). Bucket-level management actions (such as reading encryption configurations) require separate administrative credentials.
