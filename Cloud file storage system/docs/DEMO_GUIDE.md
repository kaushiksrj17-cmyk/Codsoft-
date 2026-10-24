# Demonstration Guide: Cloud File Storage System

**Project:** CODSOFT Cloud Computing Internship — Task 1  
**Target Duration:** 5 to 7 Minutes  
**Target Audience:** Technical Evaluators, Internship Reviewers, and System Architects  
**Author:** Cloud Computing Intern  

---

## 1. Demonstration Overview & Preparation

This guide outlines a professional, repeatable 5–7 minute walkthrough of the **Cloud File Storage System**. It demonstrates real-world cloud engineering concepts: decoupled metadata vs. object storage, server-side AES-256 encryption, role-based access control, time-limited presigned URLs, and cryptographic link sharing with instant revocation.

### Mandatory Pre-Demo Safety Rules
1. **Never use real personal, financial, or sensitive documents.** Use clearly identifiable disposable test files (e.g., `demo_document.txt`, `presentation_notes.txt`).
2. **Never expose `.env` contents, AWS secret keys, full share tokens, or presigned URLs on screen or in recordings.**
3. **Keep the application in a clean state.** Verify port `8501` is serving the application before starting your recording.

### Pre-Demo Setup (1 Minute Before Start)
1. Ensure the Streamlit server is running:
   ```powershell
   .\scripts\run.ps1
   ```
2. Open your browser to: **`http://localhost:8501`**
3. Prepare a small disposable text file on your desktop:
   - **Filename:** `cloud_architecture_notes.txt`
   - **Content:** `CODSOFT Cloud Computing Internship - Task 1 Demonstration Payload.` (Size: ~60 bytes)

---

## 2. Minute-by-Minute Demonstration Sequence

| Step | Duration | Focus Area | Key Demonstration Actions | Implementation Status |
| :---: | :---: | :--- | :--- | :---: |
| **1** | 0:00 – 0:45 | **Introduction & Problem Statement** | Explain architecture, decoupled S3 object store, and problem of web tier bandwidth exhaustion. | **Implemented & Verified** |
| **2** | 0:45 – 1:30 | **Dashboard, Status & Authentication** | Show S3 connection badge (`ap-south-1`), register or log into account, observe quota bar. | **Implemented & Verified** |
| **3** | 1:30 – 2:30 | **Pre-Flight Validation & Upload** | Demonstrate file upload policy, select disposable file, observe AES-256 badge and upload. | **Implemented & Verified** |
| **4** | 2:30 – 3:30 | **File Manager, Search, Filter & Sort** | Show file table, test search bar, filter by category (`Documents`), and test sort controls. | **Implemented & Verified** |
| **5** | 3:30 – 4:15 | **Direct Download & Version History** | Click Download (presigned URL), open version history dialog, observe SHA-256 checksum. | **Implemented & Verified** |
| **6** | 4:15 – 5:00 | **View-Only Link Sharing** | Generate View-Only share link, open link, demonstrate metadata display with download restricted. | **Implemented & Verified** |
| **7** | 5:00 – 5:45 | **Download Sharing & Immediate Revocation** | Generate Download link, verify download button, revoke link in dashboard, verify access denial. | **Implemented & Verified** |
| **8** | 5:45 – 6:30 | **Storage Analytics & Security Model** | Navigate to Analytics and Activity History, explain private S3 bucket and IAM least-privilege. | **Implemented & Verified** |
| **9** | 6:30 – 7:00 | **Automated Test Results & Conclusion** | Showcase 183 automated test suite results and conclude presentation. | **Implemented & Verified** |

---

## 3. Step-by-Step Demonstration Script

### Step 1: Introduction & Architecture (0:00 – 0:45)
- **Speaker Script:**
  > *"Welcome to the demonstration of the Cloud File Storage System, developed for the CODSOFT Cloud Computing Internship. In traditional web systems, uploading and downloading files through the application server creates heavy CPU and network bottlenecks. Our solution implements a decoupled cloud architecture: binary files are encrypted with AES-256 and stored directly in an Amazon S3 private bucket in the ap-south-1 region, while file metadata, user accounts, and cryptographic share links are managed transactionally in a relational metadata database."*
- **Visual:** Display the home dashboard at `http://localhost:8501`. Highlight the hero banner and architecture feature cards.

### Step 2: Cloud Connectivity & Authentication (0:45 – 1:30)
- **Speaker Script:**
  > *"Looking at the sidebar, the system performs a live connectivity check against Amazon S3, indicating our bucket is connected in ap-south-1. For authentication, we use salted bcrypt password hashing. Let's sign into our account. Notice that the sidebar immediately displays our account profile, role, used storage, and remaining storage quota with a real-time progress bar."*
- **Action:**
  1. Highlight the green **Amazon S3 Connected** status badge in the sidebar.
  2. Sign into an existing profile or register a new user using the sidebar.
  3. Point out the storage quota progress bar (e.g., `0.00 MB / 500.00 MB`).

### Step 3: File Upload & Pre-Flight Validation (1:30 – 2:30)
- **Speaker Script:**
  > *"Now we navigate to 'My Files'. The upload panel outlines our security constraints: maximum 50 megabytes per file, server-side AES-256 encryption, and private user prefix isolation. When we select a file, the system validates the filename, blocks directory traversal attempts, checks for prohibited executable extensions like .exe or .sh, and confirms remaining quota. Let's upload our disposable test file."*
- **Action:**
  1. Navigate to **📁 My Files** (`pages/1_My_Files.py`).
  2. Drag and drop `cloud_architecture_notes.txt` into the uploader.
  3. Show the preview card displaying filename, size, MIME type (`text/plain`), and category (`Documents`).
  4. Click **🚀 Confirm & Upload to Amazon S3**.
  5. Observe the success banner displaying the generated version `v1` and SHA-256 checksum prefix.

### Step 4: File Explorer, Search & Filtering (2:30 – 3:30)
- **Speaker Script:**
  > *"The uploaded file now appears in our file manager with its category icon, size, version label, and SHA-256 hash. Let's test the search toolbar. Searching for 'architecture' locates our file instantly, while searching for an unrelated term filters it out. We can also filter by categories such as Documents, Images, or Archives, and sort by date, name, or size."*
- **Action:**
  1. In the search bar, type `architecture` (file remains visible).
  2. Type `nonexistent` (table displays empty state). Clear the search bar.
  3. Switch **Filter Type** to `Documents`, then to `Images` (observing clean filtering).

### Step 5: Direct Download & Version History (3:30 – 4:15)
- **Speaker Script:**
  > *"When the owner clicks '⚡ Download', the application does not stream the file through Python memory. Instead, it generates a short-lived Amazon S3 presigned URL signed with AWS Signature Version 4, valid for 5 minutes. Let's also inspect version history. The version history dialog displays all historical iterations, timestamps, and SHA-256 checksums, allowing users to track modifications and verify data integrity."*
- **Action:**
  1. Click **⚡ Download** next to the file.
  2. Note the generation of the secure S3 download link.
  3. Expand the file details / version dialog to display the `v1` version record and SHA-256 checksum.

### Step 6: View-Only Share Link Generation (4:15 – 5:00)
- **Speaker Script:**
  > *"Collaborative sharing is a key requirement. Let's create a View-Only share link for this file. We select 'View Only' permission and a 1-hour expiration. The application mints a 256-bit cryptographically secure URL-safe token. When we open this link in the browser, notice that file metadata, owner information, and checksum are displayed, but the S3 download URL and download button are strictly stripped from the page to enforce the view-only restriction."*
- **Action:**
  1. Click **🔗 Share** on the file (or use **Shared Files** page).
  2. Select **Permission: 👁️ View Only**, **Expiration: 1 Hour**. Click **Generate Share Link**.
  3. Open the generated URL (`pages/3_Shared_Files.py?share=<token>`).
  4. Point out the blue banner: **`👁️ View-Only Access Enforced`**. Emphasize that no download button exists.

### Step 7: Download Sharing & Immediate Revocation (5:00 – 5:45)
- **Speaker Script:**
  > *"Now let's create a Download link. With download permissions, the page authorizes the token and provides a secure 5-minute presigned download button. What happens if the owner needs to revoke access? We return to the 'Shared by Me' dashboard and click '🚫 Revoke'. If an external party attempts to refresh or reuse the share link, access is immediately terminated with an explicit access denied notification."*
- **Action:**
  1. Generate a share link with **Permission: ⚡ Download Allowed**.
  2. Open the link to show the **`📥 Ready for Secure Download`** card with the download button.
  3. In the **Shared Files** management dashboard (`pages/3_Shared_Files.py`), find the active share in **📤 Shared by Me** and click **🚫 Revoke**.
  4. Refresh the share link page and observe the warning: **`🚫 Access Denied: This share link has been revoked by the owner.`**

### Step 8: Telemetry, Audit History & Security (5:45 – 6:30)
- **Speaker Script:**
  > *"Let's review system telemetry. In 'Storage Analytics', users can monitor quota utilization, remaining capacity, and storage breakdown by file type. In 'Activity History', every single action—logins, uploads, link generations, and revocations—is recorded in an immutable audit trail. In terms of cloud security, our Amazon S3 bucket has 'Block All Public Access' enabled, and all objects are stored under isolated user prefixes with mandatory server-side AES-256 encryption."*
- **Action:**
  1. Navigate to **📊 Storage Analytics** (`pages/2_Storage_Analytics.py`) to show metric cards and category bars.
  2. Navigate to **📜 Activity History** (`pages/4_Activity_History.py`) to show recent audit log rows.
  3. Navigate to **👑 Admin** (`pages/6_Admin.py`) to demonstrate RBAC enforcement.

### Step 9: Automated Test Suite & Conclusion (6:30 – 7:00)
- **Speaker Script:**
  > *"To ensure reliability, the project includes an automated test suite of 183 tests covering password hashing, S3 client key builders, quota enforcement, file validation, security audits, and opt-in live AWS integration. In Phase 5C, all automated regression tests, live S3 uploads, and headless UI workflows passed with zero errors. Thank you for reviewing the Cloud File Storage System."*
- **Action:**
  1. Show terminal output of `pytest -q` demonstrating 181 passed (or 183 passed with live AWS enabled).
  2. Conclude presentation.

---

## 4. Feature Status Matrix for Evaluators

| Demonstrated Feature | Implementation State | Verification Evidence |
| :--- | :---: | :--- |
| **Streamlit Web Dashboard** | **Fully Implemented** | Verified live on `http://localhost:8501` (`HTTP 200 OK`). |
| **Bcrypt Authentication & RBAC** | **Fully Implemented** | Unit tests in `test_auth.py` and `test_permissions.py`. |
| **File Validation & Traversal Defense** | **Fully Implemented** | 20 unit tests in `test_file_validation.py`. |
| **Amazon S3 AES-256 Ingestion** | **Fully Implemented** | Live AWS integration verified in `test_aws_storage.py`. |
| **Presigned URL Downloads** | **Fully Implemented** | Live HTTP GET download verified in Phase 5C. |
| **File Versioning & SHA-256 Checksums** | **Fully Implemented** | Verified in `test_file_service.py` and UI version history. |
| **View-Only vs Download Sharing** | **Fully Implemented** | 34 sharing tests in `test_sharing.py` and UI AppTests. |
| **Instant Link Revocation** | **Fully Implemented** | Verified in `test_sharing.py` and live UI verification. |
| **Recipient Email Restrictions** | **Fully Implemented** | Verified in `test_sharing.py` and live UI verification. |
| **Storage Quota Accounting** | **Fully Implemented** | 10 quota tests in `test_storage_quota.py`. |
| **Immutable Audit Logging** | **Fully Implemented** | Database logging verified in `activity_logs` table. |

---

## 5. Frequently Asked Questions by Evaluators

1. **Q: Why are files not downloaded through the Python server?**  
   *A:* Streaming large files through the Python Streamlit process exhausts web server memory and bandwidth. Using Amazon S3 presigned URLs delegates binary delivery directly to AWS's global edge infrastructure, keeping the web tier lightweight and responsive.

2. **Q: How is cross-tenant data access prevented?**  
   *A:* S3 object keys are partitioned by tenant (`users/{user_id}/files/v{version}/{filename}`). All metadata database queries strictly enforce user identity filters (`WHERE user_id = ?`). Attempting to download or revoke another user's file raises an explicit `PermissionError`.

3. **Q: What happens if an S3 upload succeeds but database saving fails?**  
   *A:* `upload_file()` in `src/file_service.py` implements transactional compensation. If the database commit raises an exception, the newly uploaded S3 object is immediately deleted via a compensating cleanup call before propagating the error, preventing orphaned storage costs.
