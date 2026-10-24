# CODSOFT Cloud Computing Internship

This repository contains the projects and assignments completed during the **CODSOFT Cloud Computing Internship**.

---

## Repository Structure

| Directory | Task / Project | Tech Stack | Status |
|---|---|---|---|
| 📁 **[Cloud file storage system](./Cloud%20file%20storage%20system/)** | **Task 1: Cloud File Storage System** | Python 3.11, Streamlit, Amazon S3, SQLite / PostgreSQL, Boto3 | ✅ **Completed & Verified** |

---

## Task 1: Cloud File Storage System Overview

The **[Cloud file storage system](./Cloud%20file%20storage%20system/)** is an enterprise-grade cloud storage engine built with:
- **Cloud Backend:** Amazon S3 object storage with SSE-S3 (AES-256) server-side encryption.
- **Direct Transfers:** Presigned SigV4 URLs for secure zero-proxy browser-to-S3 transfers.
- **Relational Metadata:** Fast indexing with SQLite / Amazon RDS PostgreSQL readiness.
- **Multi-Tenant Isolation:** Per-user partitioned prefixes (`users/{user_id}/files/`).
- **Cryptographic Sharing:** Time-limited SHA-256 signed public and email-restricted share tokens.
- **File Versioning:** Automatic archiving of historical versions when overwriting files.
- **Security Audit Trails:** Append-only activity history log.
- **UI:** Streamlit with Cyber-Obsidian AI dark theme.

For complete documentation, architecture, and setup instructions, see **[Cloud file storage system/README.md](./Cloud%20file%20storage%20system/README.md)**.
