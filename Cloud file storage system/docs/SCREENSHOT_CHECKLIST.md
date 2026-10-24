# Submission Screenshot Checklist & Guidelines

**Project:** CODSOFT Cloud Computing Internship — Cloud File Storage System  
**Document Purpose:** Guide interns and evaluators in capturing clean, privacy-compliant screenshots for project documentation and final internship submission.  

---

## 1. Mandatory Privacy & Redaction Rules

> [!CAUTION]
> **STRICT COMPLIANCE REQUIRED:** Before submitting any screenshots, verify that no sensitive data is visible. Failure to follow these rules may compromise cloud security or violate internship evaluation criteria.

1. **Never Capture Real AWS Credentials:** Ensure AWS Access Key IDs, Secret Keys, or terminal environment variable assignments are never visible.
2. **Never Capture `.env` Files or Passwords:** Do not take screenshots of your text editor with `.env` open.
3. **Never Capture Full Share Tokens or Presigned URLs:** When capturing share links, blur or crop any raw token strings or full presigned URLs.
4. **Use Only Disposable Sample Files:** Use sample files with generic names such as `sample_presentation.pdf`, `cloud_notes.txt`, or `architecture_diagram.png`. Never capture personal photos, financial records, resumes, or identifiable documents.
5. **Mask Private Account Information:** If your operating system, browser username, or personal email appears in the URL bar or window border, crop or redact it.

---

## 2. Recommended Screenshot Checklist

Capture the following 12 screenshots to demonstrate all key project requirements:

| # | Screenshot Target | Suggested Filename | What to Show in the Screenshot |
| :-: | :--- | :--- | :--- |
| **01** | **Main Dashboard & Landing** | `01_dashboard_home.png` | Hero banner `"Cloud File Storage System"`, architecture cards, and navigation. |
| **02** | **S3 Connected Badge & Session** | `02_sidebar_session.png` | Sidebar showing green `"● Amazon S3 Connected"` badge (`ap-south-1`) and user quota progress bar. |
| **03** | **Upload Validation & Success** | `03_upload_success.png` | Upload panel showing AES-256 badge, selected disposable file, and green `"✅ Successfully uploaded"` banner with SHA-256 checksum. |
| **04** | **File Manager Explorer** | `04_file_manager_table.png` | `My Files` page showing the file table with category icons, sizes, version labels, and action buttons. |
| **05** | **Keyword Search & Filter** | `05_search_filter.png` | File table dynamically filtered using the search input or category dropdown. |
| **06** | **Version History Dialog** | `06_version_history.png` | Expanded version history modal showing `v1` version record, upload timestamp, and SHA-256 checksum. |
| **07** | **Shared Files Dashboard** | `07_shared_files_tabs.png` | `Shared Files` page showing telemetry metric cards and the `"Shared by Me"` / `"Shared with Me"` tabs. |
| **08** | **View-Only Share Access** | `08_view_only_share.png` | Opening a view-only link showing `"👁️ View-Only Access Enforced"` banner and confirming **no** download button exists. |
| **09** | **Download Share Access** | `09_download_share.png` | Opening a download link showing `"📥 Ready for Secure Download"` and the active download button. |
| **10** | **Revoked Link Denial** | `10_revoked_link_denial.png` | Refreshing a revoked share link showing the red/amber `"🚫 Access Denied: This share link has been revoked by the owner"` banner. |
| **11** | **Storage Analytics & Audit Log** | `11_storage_analytics.png` | `Storage Analytics` graphs, quota percentages, and `Activity History` audit log records. |
| **12** | **Terminal Test Results** | `12_pytest_results.png` | Clean PowerShell terminal output running `pytest -q` showing 181 passed (or 183 passed with live AWS enabled). |

---

## 3. Step-by-Step Manual Capture Instructions (Windows)

Because automated headless browser drivers cannot download browser binaries in offline/restricted network environments, capture these screenshots manually using the running Streamlit dashboard:

### Preparation
1. Start the Streamlit application in PowerShell:
   ```powershell
   .\scripts\run.ps1
   ```
2. Open your browser to: **`http://localhost:8501`**
3. Maximize your browser window (recommended resolution: 1920x1080 or 1440x900) and set browser zoom to 100%.

### Taking Screenshots on Windows
- **Capture Window / Selection:** Press <kbd>Windows</kbd> + <kbd>Shift</kbd> + <kbd>S</kbd> to open the Windows Snipping Tool, select **Window Snip** or **Rectangular Snip**, and click your browser window.
- **Save Location:** Save your images in PNG format inside the `assets/screenshots/` directory within the project root:
  ```text
  D:\Cloud_File_Storage_System\assets\screenshots\
  ```

---

## 4. Optional AWS Console Security Screenshots (Advanced)

If you have access to the AWS Management Console and wish to include cloud infrastructure proof in your submission report, capture:

1. **Amazon S3 Bucket Properties:**
   - Bucket name: `cloud-file-storage-kaushik-2026`
   - AWS Region: `ap-south-1` (Asia Pacific - Mumbai)
   - Default encryption: **Server-side encryption with Amazon S3 managed keys (SSE-S3, AES-256)**.
2. **Amazon S3 Block Public Access Settings:**
   - Setting: **Block *all* public access: On**.
   - Confirm all 4 public access checkboxes are enabled.

> [!NOTE]
> When capturing AWS Console screens, always blur or crop out your AWS Account ID in the top right header bar.
