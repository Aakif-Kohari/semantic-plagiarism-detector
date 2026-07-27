# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take the security of the **Semantic Plagiarism Detection System** seriously. If you believe you have discovered a security vulnerability in this project, please follow the procedure below to report it to us.

### How to Report

**Please do NOT open a public GitHub issue for security vulnerabilities.**

Instead, send a detailed email to the project maintainers with the following information:

1. Description of the vulnerability and potential impact.
2. Step-by-step instructions to reproduce the issue (including sample input files or payload snippets).
3. Any proposed mitigations or code patches.

### Response Timeline

- **Initial Acknowledgment:** Within 48 hours.
- **Vulnerability Assessment:** Within 5 business days.
- **Patch & Advisory Release:** Depends on severity, typically within 14 days.

Thank you for helping keep our application and users safe!

## File Upload Hardening & Validation

To help protect the application from malicious or unsafe file uploads, all uploaded files should be validated and sanitized before processing or storage.

### File Upload Sanitization

- Sanitize filenames to remove unsafe or unexpected characters.
- Generate server-side filenames instead of relying on user-provided names.
- Validate the file's MIME type in addition to its extension.
- Scan uploaded files for malicious content whenever practical.
- Store uploaded files outside the web root whenever possible.

### File Size Bounds

- Enforce a maximum file size limit for all uploads.
- Reject files that exceed the configured size limit.
- Apply stricter size limits for specific file types when appropriate to reduce resource usage.

### Extension Validation

- Use an allowlist of permitted file extensions.
- Reject executable or potentially dangerous file types such as `.exe`, `.bat`, `.cmd`, `.sh`, `.php`, and `.js` unless explicitly required.
- Do not rely solely on file extensions; verify that the file content matches the expected format.
- Normalize filenames before validation to prevent bypass techniques.

### Additional Recommendations

- Validate uploaded files before processing or storage.
- Log failed upload validation attempts for monitoring and auditing.
- Restrict upload functionality to authorized users where applicable.
- Keep file validation libraries and dependencies up to date.
