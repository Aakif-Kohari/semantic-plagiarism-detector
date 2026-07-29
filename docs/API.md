# API Guide

This guide provides details on how to interact with the Semantic Plagiarism Detector API.

## Base URL

`http://localhost:8000`

## Authentication

The API uses Bearer token authentication for secured endpoints. Ensure you pass the token in the `Authorization` header.

## Endpoints

### POST /api/v1/auth/login

**Summary**: Authenticate user
**Description**: Authenticates a user and returns a session token.

**Request**: JSON containing email and password.
**Response**: JSON containing the authentication token.

**curl example**:
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
        "email":"user@example.com",
        "password":"password"
      }'
```

---

### POST /api/v1/scan

**Summary**: Scan Document
**Description**: Scan an uploaded document against the indexed corpus database for plagiarism.

**Request**: `multipart/form-data` containing the file to scan.
**Response**: JSON containing the plagiarism analysis results.

**curl example**:
```bash
curl -X POST http://localhost:8000/api/v1/scan \
  -H "Authorization: Bearer dev-bearer-token" \
  -F "file=@sample.pdf" \
  -F "threshold=0.59" \
  -F "top_k=3"
```
