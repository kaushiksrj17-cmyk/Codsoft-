# System Architecture: Cloud File Storage System

**Project:** CODSOFT Cloud Computing Internship — Task 1  
**Author:** Senior Cloud Architect & Python Developer  
**Status:** Phase 1 Foundation Active  

---

## 1. High-Level Architectural Overview

The **Cloud File Storage System** is structured as a decoupled, multi-tiered cloud application. It separates high-throughput binary object storage (delegated to Amazon Web Services S3) from relational metadata management, authorization checks, and UI rendering.

```mermaid
graph TD
    User([User Browser]) -->|HTTP / WebSockets| StreamlitUI[Streamlit Dashboard App]
    
    subgraph Application_Tier [Application & Business Logic Tier]
        StreamlitUI --> AppConfig[Config & Environment Loader]
        StreamlitUI --> FileValidation[Validation & Sanitization Engine]
        StreamlitUI --> PermissionEngine[RBAC & Permission Evaluator]
        StreamlitUI --> QuotaManager[Storage Quota Calculator]
        StreamlitUI --> SharingService[Cryptographic Token Service]
        StreamlitUI --> S3Manager[AWS S3 Boto3 Manager]
        StreamlitUI --> ActivityLogger[Audit Trail Logger]
    end

    subgraph Data_Tier [Persistence & Storage Tier]
        ActivityLogger --> MetadataDB[(SQLite / PostgreSQL Metadata Store)]
        QuotaManager --> MetadataDB
        PermissionEngine --> MetadataDB
        SharingService --> MetadataDB
        
        S3Manager -->|TLS 1.3 / SigV4| AmazonS3[(Amazon S3 Private Bucket)]
    end

    User -.->|Direct Download via Presigned URL| AmazonS3
```

---

## 2. Core Architectural Tiers

### 2.1 Presentation Tier (Streamlit Web Dashboard)
- **Framework:** Streamlit (Python 3.11 compatible).
- **Structure:** Modular multi-page architecture (`pages/`) with shared component design system (`components/`).
- **Design Philosophy:** Responsive-style layout with custom CSS tokens, modern metric cards, clear status indicators, and zero credential leakage.

### 2.2 Application & Logic Tier (`src/`)
- **`config.py`**: Centralized configuration reading from `.env`, with strict validation and safe handling of missing/dummy AWS credentials.
- **`file_validation.py`**: Defends the system against malicious inputs by enforcing:
  - Strict filename sanitization and directory traversal stripping.
  - Windows reserved system name blocking (`CON`, `PRN`, `AUX`, `NUL`, etc.).
  - File size boundary checks against configured ceilings.
  - Dangerous executable extension blacklisting (`.exe`, `.bat`, `.cmd`, `.sh`, `.ps1`, etc.).
  - SHA-256 data integrity checksum calculation.
- **`permissions.py`**: Role-based access control (RBAC) and object-level permissions (`viewer`, `downloader`, `editor`, `owner`, `admin`).
- **`storage_quota.py`**: Enforces user storage capacity limits, preventing buffer or bucket overflow.
- **`sharing.py`**: Generates cryptographically secure, high-entropy tokens (`secrets.token_urlsafe`) with configurable expiration windows and instant revocation.
- **`aws_storage.py`**: Wraps the Boto3 S3 client with standard retries, exponential backoff, and signature version 4 (`s3v4`).
- **`activity_logger.py`**: Records immutable security events, uploads, downloads, deletions, and access attempts.

### 2.3 Metadata Database Tier (Relational)
- **Development Engine:** SQLite 3 with enforced foreign keys (`PRAGMA foreign_keys = ON;`) and write-ahead logging.
- **Production Migration Target:** PostgreSQL (e.g., Amazon RDS PostgreSQL or Supabase).
- **Schema Design:** Standard SQL-92 compliant data types allowing direct export/import into PostgreSQL without ORM lock-in.

#### Database Entities:
1. `users`: Tenant profiles, hashed credentials, storage quotas, and used capacity.
2. `files`: File metadata, original names, sanitized S3 object keys, content types, SHA-256 hashes, and soft-delete flags.
3. `file_versions`: Historical iterations of uploaded files with version numbers and S3 object keys.
4. `file_shares`: Cryptographic share tokens, permission levels (`view`, `download`), expiration timestamps, and revocation states.
5. `activity_logs`: Immutable audit trail with user references, actions, IP addresses, and timestamps.

### 2.4 Cloud Object Storage Tier (Amazon S3)
- **Bucket Policy:** 100% Private bucket with **Block All Public Access** enabled.
- **Encryption:** Server-Side Encryption with Amazon S3 managed keys (`SSE-S3`, `AES-256`) enabled by default on all PUT operations.
- **Object Key Isolation:** Strict tenant partitioning using hierarchical prefixes:
  ```
  users/{user_id}/files/v{version_number}/{filename}
  ```

---

## 3. End-to-End Operational Flows

### 3.1 File Upload & Ingestion Flow
1. **User Action:** User selects a file to upload in the UI.
2. **Pre-flight Validation:** 
   - Filename is sanitized to eliminate path traversal characters (`..`, `/`, `\`).
   - File size is checked against `MAX_FILE_SIZE_MB`.
   - File extension is verified against the blacklisted executable list.
3. **Quota Verification:** User's remaining quota (`storage_quota_bytes - used_storage_bytes`) is calculated. If insufficient, upload is rejected immediately.
4. **Integrity Check:** SHA-256 checksum is calculated on the stream.
5. **S3 Ingestion:** Boto3 uploads the object with `ServerSideEncryption='AES256'` to `users/{user_id}/files/...`.
6. **Metadata Record:** A database transaction inserts the `files` record, updates `users.used_storage_bytes`, and logs the event to `activity_logs`.

### 3.2 File Download Flow (Presigned URLs)
1. **Request:** User clicks download for file ID `N`.
2. **Authorization:** System confirms requesting user is the owner, an administrator, or holds an active share token.
3. **Presigned URL Generation:** The server asks S3 for an authenticated, time-limited GET URL (default 3600 seconds) signed with SigV4.
4. **Direct Stream:** The user's browser streams the file directly from S3, eliminating application server bandwidth bottlenecks.
5. **Audit:** Download event is recorded in `activity_logs`.

### 3.3 Secure File Sharing Flow
1. **Link Creation:** Owner chooses expiration duration (e.g., 24 hours) and permission level (`view` or `download`).
2. **Token Minting:** Server generates a 256-bit URL-safe token and saves the record in `file_shares`.
3. **Recipient Access:** Recipient opens the URL containing the token.
4. **Verification:** System verifies that `is_revoked == 0` and `now() < expires_at`.
5. **Revocation:** Owner can click "Revoke" at any moment to invalidate the token immediately.

---

## 4. Migration Strategy: SQLite to PostgreSQL

To migrate to PostgreSQL for multi-user hosted deployments:
1. Update `DATABASE_PATH` in `.env` to a PostgreSQL connection URI:
   ```env
   DATABASE_URL=postgresql://user:password@rds-endpoint.amazonaws.com:5432/cloud_storage
   ```
2. Replace `sqlite3` driver connection in `src/database.py` with `psycopg2` or `psycopg3` connection pool.
3. Schema compatibility: Primary keys use `SERIAL` / `BIGSERIAL`, boolean columns map cleanly, and indexes match PostgreSQL syntax.
