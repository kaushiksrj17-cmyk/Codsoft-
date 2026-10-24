# Security Architecture & Best Practices

**Project:** Cloud File Storage System  
**Task:** CODSOFT Cloud Computing Internship — Task 1  
**Classification:** Internal Developer & Deployment Guide  

---

## 1. Amazon S3 Private Bucket Enforcement

### 1.1 Strict Private Access Baseline
The storage system is architected under the zero-trust principle that **no public read or write access is ever permitted on the S3 bucket**.

- **Block Public Access (All 4 Flags Enabled):**
  - `BlockPublicAcls = True`
  - `IgnorePublicAcls = True`
  - `BlockPublicPolicy = True`
  - `RestrictPublicBuckets = True`
- **Default Encryption:** Enforce Server-Side Encryption with Amazon S3-managed keys (`SSE-S3` / AES-256) on all stored objects.
- **Enforce TLS / HTTPS Only:** Ensure the bucket policy rejects any insecure HTTP requests:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "EnforceTLSRequestsOnly",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:*",
      "Resource": [
        "arn:aws:s3:::YOUR-BUCKET-NAME",
        "arn:aws:s3:::YOUR-BUCKET-NAME/*"
      ],
      "Condition": {
        "Bool": {
          "aws:SecureTransport": "false"
        }
      }
    }
  ]
}
```

---

## 2. Least-Privilege IAM Permissions

Never use the AWS root account or administrative credentials for application operations. The application requires an IAM user with a dedicated policy limited strictly to the required S3 bucket actions.

### 2.1 Recommended IAM Policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowBucketInspection",
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket",
        "s3:GetBucketLocation"
      ],
      "Resource": "arn:aws:s3:::YOUR-BUCKET-NAME"
    },
    {
      "Sid": "AllowObjectOperations",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:GetObjectVersion"
      ],
      "Resource": "arn:aws:s3:::YOUR-BUCKET-NAME/*"
    }
  ]
}
```

---

## 3. Credential Protection & Management

1. **Zero Hardcoded Secrets:** AWS access keys and database credentials are never stored in source code, commit history, or client bundles.
2. **Environment Variable Injection:** Credentials must be supplied via local `.env` files or operating system environment variables.
3. **Repository Defense:** The `.gitignore` file strictly excludes `.env`, `*.pem`, `*.key`, and credential artifacts.
4. **Interface Sanitization:** The Streamlit dashboard and logging mechanisms mask credential values, displaying only the last 4 characters of access keys and never printing secret keys.
5. **Safe Development Defaults:** If AWS credentials are missing or contain placeholder values, the system enters a safe **Development Mode** without attempting real cloud network calls.

---

## 4. Multi-Tenant User Isolation

In a multi-user file storage system, one tenant must never access another tenant's files directly:

1. **Object Namespace Isolation:** Objects are physically separated within the S3 bucket using user-scoped prefix paths:
   ```
   users/{user_id}/files/{filename}
   ```
2. **Metadata-Level Authorization:** Every database query filtering files joins on `user_id = :current_user_id` or verifies explicit ownership before returning records.
3. **Download Token Signing:** Presigned URLs are only generated after the server validates that the requesting session has explicit read rights to the object key.

---

## 5. Input Validation & Defense-in-Depth

Untrusted user uploads represent a critical attack surface. The system enforces multi-layered validation in `src/file_validation.py`:

- **Path Traversal Defense:** Strips `../`, `..\`, leading slashes, and null bytes using `os.path.basename` and regex filtering.
- **Windows Reserved Device Names:** Blocks names such as `CON`, `PRN`, `AUX`, `NUL`, `COM1-9`, and `LPT1-9` that could disrupt local file operations.
- **Dangerous Executable Extension Blacklisting:** Blocks execution payloads including `.exe`, `.bat`, `.cmd`, `.sh`, `.ps1`, `.vbs`, and `.msi`.
- **Maximum Payload Ceilings:** Validates file size headers and binary streams against `MAX_FILE_SIZE_MB` to prevent denial-of-service and memory exhaustion.
- **Data Integrity:** Calculates and verifies SHA-256 hashes for all ingested files.

---

## 6. Secure Share Links & Expiration

1. **Cryptographically Secure Tokens:** Share tokens are minted using `secrets.token_urlsafe(32)`, providing 256 bits of entropy to resist brute-force enumeration attacks.
2. **Time-Limited Validity:** Share links are bound by `SHARE_LINK_MAX_EXPIRY_HOURS`. Once the timestamp expires, access is denied.
3. **Instant Revocation:** An owner can revoke any share link instantly, updating `is_revoked = 1` in the database.
4. **Access Logging:** Share link access attempts increment an access counter and generate an entry in the immutable `activity_logs` table.

---

## 7. Safe Deletion Protocol

- **Soft Delete Phase:** User file deletions mark `is_deleted = 1` in the metadata database, removing them from active views.
- **Permanent Purge:** Hard deletion initiates both an S3 `delete_object` API call and removes the metadata record within an atomic transaction.
- **Audit Logging:** Every deletion event records the timestamp, user ID, IP address, and target resource ID in `activity_logs`.
