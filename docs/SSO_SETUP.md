# Single Sign-On (SSO) Setup Guide

This guide explains how to configure Google and GitHub OAuth 2.0 credentials for the Semantic Plagiarism Detection System to enable Single Sign-On (SSO).

## Required Environment Variables

To enable SSO, add the following variables to your `.env` file:

```env
# Google OAuth Configuration
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret

# GitHub OAuth Configuration
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret

# Application Base URL (Used for OAuth redirect URIs)
APP_BASE_URL=http://localhost:8501
```

---

## Setting up Google OAuth 2.0

Follow these steps to obtain your `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`.

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project or select an existing one.
3. In the left sidebar, navigate to **APIs & Services > OAuth consent screen**.
4. Choose **External** (or Internal if using a Google Workspace) and click **Create**.
5. Fill in the required application details (App name, User support email, Developer contact information) and click **Save and Continue**.
6. (Optional) Add scopes if you wish, but the default email and profile scopes are sufficient. Click **Save and Continue**.
7. Navigate to **APIs & Services > Credentials**.
8. Click **+ CREATE CREDENTIALS** and select **OAuth client ID**.
9. Select **Web application** as the Application type.
10. Under **Authorized redirect URIs**, add the base URL of your application (e.g., `http://localhost:8501`).
11. Click **Create**.
12. Copy the **Client ID** and **Client Secret** and add them to your `.env` file as `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`.

---

## Setting up GitHub OAuth App

Follow these steps to obtain your `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET`.

1. Log in to GitHub and go to **Settings**.
2. In the left sidebar, scroll down and click on **Developer settings**.
3. In the left sidebar, click on **OAuth Apps**.
4. Click the **New OAuth App** button (or **Register a new application**).
5. Fill out the application details:
   - **Application name**: e.g., Semantic Plagiarism Detector
   - **Homepage URL**: e.g., `http://localhost:8501`
   - **Authorization callback URL**: This must be the base URL of your application, exactly as it appears in your browser (e.g., `http://localhost:8501`).
6. Click **Register application**.
7. Copy the **Client ID** and add it to your `.env` file as `GITHUB_CLIENT_ID`.
8. Click **Generate a new client secret**.
9. Copy the generated secret and add it to your `.env` file as `GITHUB_CLIENT_SECRET`.
