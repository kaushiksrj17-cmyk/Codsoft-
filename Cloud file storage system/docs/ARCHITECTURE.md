# System Architecture: Cloud File Storage System

**Project:** CODSOFT Cloud Computing Internship — Task 1  
**Architecture:** Decoupled Multi-Tier Cloud Application  
**Runtime:** Python 3.11 | Streamlit UI | Amazon S3 | SQLite 3 / PostgreSQL  

---

## 1. High-Level Architectural Overview

The **Cloud File Storage System** is built upon a decoupled cloud architecture designed to separate high-throughput binary object persistence from relational metadata indexing, access delegation, and user interface rendering.

```mermaid
graph TD
    Client([User Browser]) -->|HTTP / WebSockets| StreamlitUI[Streamlit Web Application Tier]
    
    subgraph AppTier [Application & Business Logic Tier]
        StreamlitUI --> Auth[Authentication & RBAC Engine<br/>src/auth.py & src/permissions.py]
        StreamlitUI --> FileService[File Lifecycle & Quota Orchestrator<br/>src/file_service.py & src/storage_quota.py]
        StreamlitUI --> SharingService[Cryptographic Share Service<br/>src/sharing.py]
        StreamlitUI --> Logger[Audit Trail Logger<br/>src/activity_logger.py]
    end

    subgraph StorageBoundary [Storage & Persistence Boundary]
        FileService -->|Metadata & Quota Updates| SQLiteDB[(SQLite Metadata Store<br/>data/cloud_storage.db)]
        SharingService -->|Tokens & Revocations| SQLiteDB
        Auth -->|User Credentials & Roles| SQLiteDB
        Logger -->|Immutable Audit Logs| SQLiteDB

        FileService -->|Boto3 / SigV4 / AES-256| S3Manager[AWS S3 Storage Manager<br/>src/aws_storage.py]
        SharingService -->|Presigned Download URL Generation| S3Manager
        S3Manager -->|TLS 1.3 REST API| AmazonS3[(Private Amazon S3 Bucket<br/>ap-south-1)]
    end

    Client -.->|Direct 5-Minute Presigned Download Stream| AmazonS3
```

---

## 2. Request Flow Architecture

The application enforces a strict unidirectional request flow that guarantees authorization, validation, and quota availability before any interaction with the cloud object store or metadata database occurs:

```text
[ 1. Streamlit UI Presentation ]
               │
               ▼
[ 2. Authentication & Authorization ]
   - Session State Validation (st.session_state["current_user"])
   - Role-Based Access Control (src/permissions.py: is_admin, can_view, can_download)
               │
               ▼
[ 3. File & Sharing Domain Services ]
   - Pre-flight Validation (src/file_validation.py: extension blacklist, filename sanitization, size checks)
   - Capacity Allocation (src/storage_quota.py: quota ceiling verification)
   - Cryptographic Token Minting (src/sharing.py: 256-bit URL-safe tokens)
               │
               ▼
[ 4. Metadata & Audit Persistence ]
   - Transactional SQLite Execution (src/database.py: PRAGMA foreign_keys = ON)
   - Metadata Insertion (files, file_versions, file_shares)
   - Immutable Activity Logging (activity_logs table)
               │
               ▼
[ 5. Private Amazon S3 Object Storage ]
   - User-Partitioned Keys: users/{user_id}/files/v{version}/{filename}
   - Server-Side Encryption: AES-256 (SSE-S3)
   - Presigned URL Generation: Short-lived (5-minute) SigV4 authenticated URLs
```

---

## 3. Boundaries: Metadata Store vs. Object Storage

A foundational design principle of this architecture is the clean separation of responsibilities between **Application Metadata** and **Binary Object Storage**.

| Attribute | Application Metadata Store (SQLite 3) | Cloud Object Store (Amazon S3) |
| :--- | :--- | :--- |
| **Location** | Local filesystem (`data/cloud_storage.db`) / RDS PostgreSQL | AWS Region `ap-south-1` (`cloud-file-storage-kaushik-2026`) |
| **Content Stored** | User accounts, password hashes, file names, sizes, MIME types, SHA-256 checksums, share tokens, expiration dates, revocation states, and audit trails. | Raw binary file payloads (encrypted with AES-256). |
| **Access Control** | Enforced via application logic and SQL parameterized queries. | Protected via AWS IAM least-privilege credentials and S3 Block Public Access. |
| **Bandwidth Impact** | Extremely low (small metadata queries, indexed lookups). | High throughput; offloaded directly to AWS edge/S3 infrastructure via presigned URLs. |
| **Direct Access** | Never accessible directly by the client browser. | Accessible only via time-limited, cryptographically signed SigV4 presigned URLs. |
| **Integrity** | ACID-compliant relational transactions with foreign key cascades. | S3 object versioning and SHA-256 checksum verification. |

---

## 4. Operational Workflows & Sequence Diagrams

### 4.1 End-to-End File Upload Workflow
When a tenant uploads a file, the application guarantees data integrity and prevents orphaned cloud objects via transactional rollback.

```mermaid
sequenceDiagram
    autonumber
    actor User as User Browser
    participant UI as Streamlit UI (pages/1_My_Files.py)
    participant FS as File Service (src/file_service.py)
    participant Val as File Validation (src/file_validation.py)
    participant Quota as Quota Engine (src/storage_quota.py)
    participant S3 as Amazon S3 (Boto3 Client)
    participant DB as SQLite DB (data/cloud_storage.db)

    User->>UI: Selects file to upload
    UI->>Val: Pre-flight check (filename, size, extension)
    Val-->>UI: Validation OK (or blocks if malicious/prohibited)
    UI->>Quota: check_quota_availability(user_id, file_size)
    Quota-->>UI: Quota OK (or raises QuotaExceededError)
    
    User->>UI: Clicks "Confirm & Upload to Amazon S3"
    UI->>FS: upload_file(user_id, file_bytes, filename)
    FS->>Val: Compute SHA-256 checksum
    FS->>S3: put_object(Key, Body, ServerSideEncryption='AES256')
    
    alt S3 Upload Successful
        FS->>DB: BEGIN TRANSACTION
        FS->>DB: INSERT into files & file_versions
        FS->>DB: UPDATE users.used_storage_bytes
        FS->>DB: INSERT into activity_logs (FILE_UPLOAD)
        FS->>DB: COMMIT TRANSACTION
        FS-->>UI: Upload success (filename, version, checksum)
        UI-->>User: Success banner rendered
    else Database Insertion Fails (Rollback Scenario)
        FS->>DB: ROLLBACK
        FS->>S3: delete_object(Key) [Compensating Cleanup]
        FS-->>UI: Raise exception & display error to user
    end
```

### 4.2 File Download Workflow (Presigned URL Delegation)
The application never proxies large binary streams through the web server, avoiding memory spikes and bandwidth bottlenecks.

```mermaid
sequenceDiagram
    autonumber
    actor User as User Browser
    participant UI as Streamlit UI (components/file_table.py)
    participant Perm as Permissions Engine (src/permissions.py)
    participant S3 as Amazon S3 (src/aws_storage.py)

    User->>UI: Clicks "⚡ Download"
    UI->>Perm: can_download_file(user_id, file_id)
    Perm-->>UI: Authorized (Owner, Admin, or Shared)
    UI->>S3: generate_presigned_download_url(s3_key, expires_in=300)
    S3-->>UI: Returns SigV4 presigned HTTPS URL
    UI-->>User: Displays direct download button / link
    User->>S3: GET /users/{user_id}/files/... (HTTPS directly to S3)
    S3-->>User: 200 OK + Binary Stream (AES-256 decrypted on download)
```

### 4.3 Secure File Sharing Lifecycle
Share links operate via cryptographically random tokens (`secrets.token_urlsafe(32)`):

1. **Generation:**
   - Owner selects permission level (`view` vs. `download`), expiration duration (1h, 24h, 72h, 168h), and optional recipient email.
   - Server mints a 256-bit entropy token and records it in `file_shares`.
2. **Access Evaluation:**
   - When loaded via `?share=<token>`, the server queries `file_shares`.
   - Validates that `is_revoked == 0` and `CURRENT_TIMESTAMP < expires_at`.
   - If `shared_with_email` is set, verifies that `current_user.email` matches the restricted email.
3. **Permission Enforcement:**
   - **View-Only:** Renders file metadata, owner, size, and SHA-256 checksum with an explicit banner `"👁️ View-Only Access Enforced"`. The S3 presigned URL generator is never called, and download buttons are completely stripped from the UI.
   - **Download:** Generates a 5-minute presigned download URL and renders `"📥 Ready for Secure Download"`.
4. **Instant Revocation:**
   - The file owner or an administrator can revoke the link at any time from the `"Shared by Me"` dashboard.
   - The database sets `is_revoked = 1`. Any subsequent access immediately fails with `"🚫 Access Denied: This share link has been revoked by the owner."`

---

## 5. Security & Isolation Controls

### 5.1 Multi-Tenant Prefix Isolation
Objects in Amazon S3 are partitioned strictly by tenant ID:
```
s3://cloud-file-storage-kaushik-2026/users/{user_id}/files/v{version_number}/{sanitized_filename}
```
All S3 operations require the caller's session `user_id`. Queries strictly filter `WHERE user_id = ?`, making cross-tenant metadata inspection or object retrieval impossible.

### 5.2 Server-Side Encryption (SSE-S3)
Every object uploaded through `S3StorageManager` explicitly includes:
```python
extra_args = {
    "ContentType": content_type,
    "ServerSideEncryption": "AES256",
}
```
This guarantees that data at rest in Amazon S3 is encrypted using 256-bit Advanced Encryption Standard keys managed by AWS.

### 5.3 Input Defense & Path Traversal Neutralization
`src/file_validation.py` enforces:
- Stripping directory separators (`/`, `\`) and traversal tokens (`..`).
- Blocking Windows reserved device names (`CON`, `PRN`, `AUX`, `NUL`, `COM1-9`, `LPT1-9`).
- Enforcing safe character whitelist (`[a-zA-Z0-9_.-]`).
- Prohibiting dangerous executable extensions (`.exe`, `.bat`, `.cmd`, `.sh`, `.ps1`, `.msi`, `.vbs`, etc.).

---

## 6. PostgreSQL Production Migration Path

The database schema in `src/database.py` is written in standard SQL-92 to ensure seamless transition from local SQLite to managed PostgreSQL (e.g., Amazon RDS PostgreSQL):

1. **Connection Layer:** Update `get_connection()` to utilize `psycopg2` or `psycopg3` connection pools when `DATABASE_URL` starts with `postgres://` or `postgresql://`.
2. **Auto-Increment Mapping:** SQLite's `INTEGER PRIMARY KEY AUTOINCREMENT` maps directly to PostgreSQL's `SERIAL` / `BIGSERIAL`.
3. **Foreign Keys:** SQLite explicitly requires `PRAGMA foreign_keys = ON;`, whereas PostgreSQL enforces foreign keys by default.
4. **Data Isolation:** All table definitions use standard constraints (`UNIQUE`, `NOT NULL`, `CHECK`), ensuring drop-in compatibility.
