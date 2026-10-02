# Authentication Setup for Development

Critique supports two sign-in methods. Both are optional for local browsing —
they are only needed to submit or manage projects.

## GitHub OAuth (optional)

### Step 1: Create a GitHub OAuth Application

1. Go to GitHub Settings > Developer settings > OAuth Apps
   https://github.com/settings/developers
2. Click **New OAuth App**
3. Fill in:
   - Application name: Critique (or Critique Dev)
   - Homepage URL: http://127.0.0.1:8000
   - Authorization callback URL: http://127.0.0.1:8000/auth/callback
4. Click **Register application**
5. Note the **Client ID** shown on the next page
6. Click **Generate a new client secret**
7. Copy both values into your `.env` file

### Step 2: Configure `.env`

```ini
GITHUB_CLIENT_ID=your_github_client_id_here
GITHUB_CLIENT_SECRET=your_github_client_secret_here
GITHUB_REDIRECT_URI=http://127.0.0.1:8000/auth/callback
```

### Step 3: Generate a Secret Key

Run this in PowerShell (or any terminal):

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Put the output in `SECRET_KEY` in your `.env` file.

### Step 4: Restart the App

Stop and restart the server. The header should show a **Login with GitHub**
button.

## Email Magic Links (optional)

Passwordless login: the user requests a link, and the email contains a
one-time URL valid for **15 minutes**. Emails are sent through
[Resend](https://resend.com).

### Step 1: Create a Resend Account

1. Sign up at https://resend.com and create an API key
2. Verify a sender address or domain in Resend

### Step 2: Configure `.env`

```ini
RESEND_API_KEY=re_your_api_key_here
EMAIL_FROM=login@example.com
```

### Step 3: Restart the App

Restart the server. No UI change is needed — the sign-in dialog already
offers **Continue with email**; with the keys set, requests now actually
deliver mail.

Notes:

- If `RESEND_API_KEY` is unset, email login requests are accepted but no mail
  is sent (send failures are swallowed) — GitHub login is unaffected.
- Magic-link requests always return the same generic success response, so the
  endpoint cannot be used to probe which email addresses have accounts.

## Local Development Without Either Provider

You can run the app and browse every public page with no authentication
configuration at all.
