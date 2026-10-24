# Beginner-Friendly AWS S3 Setup Checklist

**Project:** Cloud File Storage System  
**Task:** CODSOFT Cloud Computing Internship — Task 1  
**Target Storage Service:** Amazon Simple Storage Service (Amazon S3)  

> [!IMPORTANT]
> **Zero Automatic Resource Creation:** This project will **NEVER** automatically provision AWS cloud resources or incur cloud charges. You retain full control over when and how your S3 bucket is created in your AWS account.

---

## Prerequisites
- An active AWS Account (Eligible for AWS Free Tier: 5 GB standard S3 storage, 20,000 GET requests, 2,000 PUT requests per month for 12 months).
- Access to the [AWS Management Console](https://console.aws.amazon.com/).

---

## Step 1: Create a Dedicated IAM User (Least Privilege)

Do not use your AWS root user account for application access.

1. Navigate to the **IAM Console** (Search "IAM" in the AWS search bar).
2. Click **Users** in the left sidebar, then click **Create user**.
3. **User name:** Enter `cloud-storage-app-user`.
4. Click **Next** (leave "Provide user access to the AWS Management Console" unchecked).
5. In **Permissions options**, select **Attach policies directly**.
6. Click **Create policy**:
   - Switch to the **JSON** tab and paste the following policy (replace `YOUR-BUCKET-NAME` with your chosen bucket name):
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Sid": "BucketInspection",
         "Effect": "Allow",
         "Action": [
           "s3:ListBucket",
           "s3:GetBucketLocation"
         ],
         "Resource": "arn:aws:s3:::YOUR-BUCKET-NAME"
       },
       {
         "Sid": "ObjectOperations",
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
   - Click **Next**, name the policy `CloudStorageAppPolicy`, and click **Create policy**.
7. Return to the User creation tab, select `CloudStorageAppPolicy`, and click **Next** -> **Create user**.
8. Click on your newly created user (`cloud-storage-app-user`) -> **Security credentials** tab.
9. Under **Access keys**, click **Create access key**.
10. Select **Application running outside AWS** -> click **Next** -> **Create access key**.
11. **Download the `.csv` file** containing your `Access key ID` and `Secret access key`. Store it securely.

---

## Step 2: Create a Private Amazon S3 Bucket

1. Navigate to the **S3 Console** (Search "S3" in the AWS search bar).
2. Click the orange **Create bucket** button.
3. **Bucket name:** Enter a globally unique, DNS-compliant name (e.g., `cloud-storage-task1-yourname-2026`).
4. **AWS Region:** Select your preferred region (e.g., `us-east-1` or `ap-south-1`). Make a note of this region.
5. **Object Ownership:** Keep **ACLs disabled (recommended)**.
6. **Block Public Access settings for this bucket:**
   - Ensure the checkbox **Block *all* public access** is **CHECKED** (enabled).
   - All 4 sub-options should remain checked.
7. **Bucket Versioning:** (Optional but recommended) Click **Enable** if you wish to retain previous object versions in S3.
8. **Default encryption:**
   - Encryption type: **Server-side encryption with Amazon S3 managed keys (SSE-S3)**.
   - Bucket Key: **Enable**.
9. Click **Create bucket**.

---

## Step 3: Populate Your Local Environment Configuration

1. In your project root, copy the `.env.example` file to `.env`:
   ```powershell
   Copy-Item .env.example .env
   ```
2. Open `.env` in your editor and update the placeholders with your actual AWS values:
   ```env
   APP_ENV=development
   AWS_REGION=us-east-1
   S3_BUCKET_NAME=cloud-storage-task1-yourname-2026
   AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
   AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
   DATABASE_PATH=data/cloud_storage.db
   MAX_FILE_SIZE_MB=50
   DEFAULT_STORAGE_QUOTA_MB=500
   SHARE_LINK_MAX_EXPIRY_HOURS=168
   ```
3. Save the `.env` file. (Verify that `.env` is listed in your `.gitignore` to prevent committing it).

---

## Step 4: Verify Connectivity in Streamlit

1. Launch your application:
   ```powershell
   .\scripts\run.ps1
   ```
2. In the dashboard sidebar, navigate to **Settings (5_Settings.py)**.
3. Click the **🔍 Test AWS S3 Connectivity** button.
4. You should receive a green success notification:
   > `✅ Connection Succeeded: Bucket 'cloud-storage-task1-yourname-2026' is accessible.`

---

## Step 5: (Optional) Configure S3 CORS for Direct Browser Uploads

If you choose to use direct browser-to-S3 uploads in Phase 2:
1. Open your bucket in the S3 Console -> **Permissions** tab.
2. Scroll to **Cross-origin resource sharing (CORS)** and click **Edit**.
3. Paste the following configuration:
   ```json
   [
     {
       "AllowedHeaders": ["*"],
       "AllowedMethods": ["GET", "PUT", "POST", "HEAD"],
       "AllowedOrigins": ["http://localhost:8501", "http://127.0.0.1:8501"],
       "ExposeHeaders": ["ETag"]
     }
   ]
   ```
4. Click **Save changes**.
