# Cloud File Storage System

[![Python Version](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/framework-Streamlit-red.svg)](https://streamlit.io/)
[![Cloud Storage](https://img.shields.io/badge/storage-Amazon%20S3-orange.svg)](https://aws.amazon.com/s3/)
[![Database](https://img.shields.io/badge/database-SQLite%20%7C%20PostgreSQL-lightgrey.svg)](https://www.sqlite.org/)
[![Internship](https://img.shields.io/badge/CODSOFT-Task%201-success.svg)](#)

Enterprise-grade cloud file storage application built with **Streamlit**, **Amazon Web Services (S3)**, **Boto3**, and a relational metadata store. Developed for the **CODSOFT Cloud Computing Internship — Task 1**.

---

## 1. Project Overview

The **Cloud File Storage System** provides a private, secure, and responsive web dashboard for uploading, managing, versioning, and sharing digital assets in the cloud. 

By offloading heavy file storage to **Amazon S3** and managing permissions, access counters, and quotas inside an isolated relational database, the system ensures zero bandwidth bottlenecks on the web application tier.

### Current Implementation Status: Phase 1 Foundation
This repository represents the completed **Phase 1: Project Foundation**. In this phase:
- The complete multi-page architecture and component design system are established.
- Core configuration, SQLite metadata database, authorization, file validation, sharing tokens, and quota calculation services are fully implemented and unit-tested.
- Safe development defaults prevent accidental cloud costs or connection failures when AWS credentials are not yet supplied.

---

## 2. Feature Matrix: Implemented vs Planned

| Feature Category | Capability | Phase 1 Foundation | Planned (Phase 2+) |
| :--- | :--- | :---: | :---: |
| **Architecture** | Streamlit Multi-Page Dashboard & Custom CSS | ✅ Active | — |
| **Configuration**| Centralized `.env` parsing with safe status masking | ✅ Active | — |
| **Metadata DB**  | Relational schema for users, files, versions, shares, audit logs | ✅ Active (SQLite) | Phase 4 (PostgreSQL) |
| **Security**     | Path traversal defense & executable extension blacklisting | ✅ Active | — |
| **Access Control**| RBAC (Admin/User) & object permissions (view/download/edit) | ✅ Active | — |
| **Quota Engine** | Quota ceiling enforcement & byte unit formatting | ✅ Active | — |
| **Sharing Engine**| Cryptographic 256-bit URL token generation & expiry checking | ✅ Active | — |
| **AWS S3 Client**| Boto3 client wrapper with retries & key builders | ✅ Scaffolding | Phase 2 (Live API) |
| **Cloud Storage**| Direct S3 multipart upload streaming & checksum verify | Scaffolding | 🔄 Phase 2 |
| **Direct Retrieval**| Time-limited presigned S3 download URLs | Scaffolding | 🔄 Phase 2 |
| **Versioning**   | Automatic file version increments & rollback in S3 | Architecture Ready | 🔄 Phase 3 |
| **Analytics**    | Storage breakdown, upload trends & intelligent-tiering advice | UI Preview | 🔄 Phase 3 |

---

## 3. Technology Stack

- **Application Language:** Python 3.11
- **Web UI & Dashboard:** Streamlit
- **Cloud Object Storage:** Amazon Simple Storage Service (Amazon S3)
- **AWS SDK:** Boto3 & Botocore (Signature Version 4)
- **Metadata Database:** SQLite 3 (Development) → PostgreSQL (Hosted Multi-User Deployment)
- **Security & Cryptography:** `bcrypt`, `secrets`, `hashlib` (SHA-256)
- **Testing Framework:** Pytest (Unit & Integration tests)
- **Environment Management:** Python `dotenv`

---

## 4. Project Directory Structure

```text
Cloud_File_Storage_System/
├── app.py                     # Main dashboard application entry point
├── requirements.txt           # Project dependencies
├── .env.example               # Configuration template with dummy placeholders
├── .gitignore                 # Excludes secrets, caches, databases, and uploads
├── README.md                  # Comprehensive documentation and setup guide
├── pytest.ini                 # Pytest configuration and test markers
├── src/                       # Core application services and business logic
│   ├── __init__.py
│   ├── config.py              # Environment configuration & safe AWS status
│   ├── database.py            # SQLite database layer & schema initialization
│   ├── auth.py                # Password hashing and strength validation
│   ├── aws_storage.py         # Amazon S3 Boto3 client manager
│   ├── file_validation.py     # Filename sanitization, path traversal & size check
│   ├── permissions.py         # Role-based access control & permission evaluator
│   ├── sharing.py             # Share token generation & expiry validation
│   ├── activity_logger.py     # Audit trail logging service
│   ├── storage_quota.py       # Storage quota calculation and formatting
│   └── file_versions.py       # File version tracking and numbering
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
│   ├── file_table.py          # File listing table and empty states
│   └── upload_panel.py        # Upload interface and policy indicators
├── assets/                    # Static image and branding assets
│   └── .gitkeep
├── tests/                     # Test suite
│   ├── __init__.py
│   ├── test_file_validation.py# File validation and security unit tests
│   ├── test_permissions.py    # RBAC and file permission unit tests
│   ├── test_database.py       # SQLite connection and schema integration tests
│   ├── test_sharing.py        # Share token and expiration unit tests
│   ├── test_storage_quota.py  # Quota calculation unit tests
│   └── test_aws_storage.py    # AWS configuration and key builder tests
├── scripts/                   # Automation scripts (Windows PowerShell)
│   ├── setup.ps1              # Environment provisioning and DB initialization
│   └── run.ps1                # Streamlit dashboard launch script
└── docs/                      # Architectural and deployment guides
    ├── ARCHITECTURE.md        # System architecture, data flow & tiers
    ├── SECURITY.md            # S3 private bucket, IAM & credential protection
    └── AWS_SETUP.md           # Step-by-step beginner S3 setup guide
```

---

## 5. Local Setup Instructions (Windows)

### Prerequisites
- Windows 10/11 with PowerShell 5.1+.
- Python 3.11+ installed and available on PATH (`python --version`).

### Automated Setup (Recommended)
Open PowerShell in the project directory and run the setup script:

```powershell
.\scripts\setup.ps1
```

The script will automatically:
1. Verify Python 3.11+.
2. Create an isolated virtual environment (`.venv`).
3. Upgrade `pip` and install all dependencies from `requirements.txt`.
4. Copy `.env.example` to `.env` if not present.
5. Initialize the local SQLite database schema inside `data/cloud_storage.db`.

### Manual Setup
If you prefer manual setup:

```powershell
# 1. Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

# 3. Create local configuration file
Copy-Item .env.example .env

# 4. Initialize database schema
python -c "from src.database import init_db; init_db()"
```

---

## 6. Running the Application

Execute the launch script:

```powershell
.\scripts\run.ps1
```

Or activate your virtual environment and start Streamlit:

```powershell
.\.venv\Scripts\streamlit run app.py
```

The dashboard will open in your default browser at:  
👉 **`http://localhost:8501`**

---

## 7. AWS S3 Setup Overview

By default, the application runs in **Development Mode** with zero cloud charges. When you are ready to connect a live private S3 bucket:

1. Refer to [docs/AWS_SETUP.md](file:///docs/AWS_SETUP.md) for step-by-step IAM and S3 bucket creation instructions.
2. Ensure your S3 bucket has **Block *all* public access** enabled.
3. Update your `.env` file with your bucket name, region, and IAM credentials:
   ```env
   AWS_REGION=us-east-1
   S3_BUCKET_NAME=your-bucket-name
   AWS_ACCESS_KEY_ID=AKIA...
   AWS_SECRET_ACCESS_KEY=...
   ```
4. Navigate to **Settings** (`pages/5_Settings.py`) and click **Test AWS S3 Connectivity** to verify access.

---

## 8. Running Pytest Test Suite

Execute the test suite using pytest inside the virtual environment:

```powershell
.\.venv\Scripts\pytest
```

To run specific markers:
```powershell
# Run only unit tests
.\.venv\Scripts\pytest -m unit

# Run integration tests
.\.venv\Scripts\pytest -m integration
```

---

## 9. Security & Compliance Notes

- **Never Commit Secrets:** `.env` and `*.db` are strictly excluded in `.gitignore`.
- **Private S3 Buckets Only:** All bucket access must use IAM authentication. Never enable public read or ACLs.
- **Input Sanitization:** Filenames are automatically scrubbed of path traversal characters (`..`, `/`, `\`) and Windows reserved device names.
- **Detailed Documentation:** Review [docs/SECURITY.md](file:///docs/SECURITY.md) and [docs/ARCHITECTURE.md](file:///docs/ARCHITECTURE.md).
