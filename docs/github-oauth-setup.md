# GitHub OAuth Setup for Development

## Step 1: Create GitHub OAuth Application

1. Go to GitHub Settings > Developer settings > OAuth Apps
   https://github.com/settings/developers
2. Click New OAuth App
3. Fill in:
   - Application name: Critique (or Critique Dev)
   - Homepage URL: http://127.0.0.1:8000
   - Authorization callback URL: http://127.0.0.1:8000/auth/callback
4. Click Register application
5. Note the Client ID shown on the next page
6. Click Generate a new client secret
7. Copy both values for the .env file

## Step 2: Create .env File

1. Copy .env.example to .env
2. Edit .env with your values

## Step 3: Generate a Secret Key

Run this in PowerShell:
python -c "import secrets; print(secrets.token_hex(32))"

## Step 4: Restart the App

Stop and restart the server. The app should show a Login with GitHub button.
