# 🤖 TARO

> A personal AI assistant built with local AI.

TARO is an AI assistant built from the ground up using **Vue, FastAPI, Ollama, Llama 3.2, and SQLite**.

The goal is to create an AI that goes beyond simple conversations — with **memory, personalization, knowledge, tools, and eventually autonomous task execution**.

## 🛠️ Tech Stack

- **Frontend:** Vue.js + Vite
- **Backend:** FastAPI + Python
- **AI:** Ollama + Llama 3.2
- **Database:** SQLite

## ✨ Current Features

- 💬 AI conversations
- 🧠 Conversation history
- 💾 Persistent messages
- 🏷️ Automatic conversation titles
- 🤖 Custom TARO personality
- 🦙 Local AI inference with Ollama

## 🚧 Current Development

**Next milestone: Streaming TARO**

TARO will display AI responses progressively instead of waiting for the entire response to finish.

## 🗺️ Roadmap

- [x] AI Chat
- [x] Conversation History
- [x] SQLite Persistence
- [x] Automatic Chat Titles
- [ ] Streaming Responses
- [ ] Long-term Memory
- [ ] File & Document Knowledge
- [ ] AI Tools
- [ ] Web Search
- [ ] AI Agent Capabilities

## 🌱 Vision

TARO is not meant to be just another chatbot.

The goal is to build a personal AI assistant that can **remember, understand, learn from context, use tools, and actually help users get things done.**

---

Built by **E.Y.** 🤖✨

## 🔐 Google Authentication Setup

If you want to use **"Continue with Google"** after cloning TARO, you need to create your own Google OAuth credentials.

### 1. Create a Google Cloud Project

Go to:

https://console.cloud.google.com/

Create a new Google Cloud project, or use an existing project.

### 2. Configure Google Auth Platform

Go to:

**Google Auth Platform → Branding**

Configure the OAuth consent screen.

Recommended settings:

- **App name:** TARO
- **Audience:** External
- **Support email:** Your Google account email
- **Developer contact email:** Your email

You can leave the app in **Testing** mode while developing.

### 3. Create OAuth Client

Go to:

**Google Auth Platform → Clients → Create Client**

Select:

**Application type:** Web application

Give it a name, for example:

```text
TARO Web Client
```

### 4. Configure Authorized JavaScript Origins

Add:

```text
http://localhost:5173
```

This is the URL used by the TARO Vue frontend during development.

### 5. Configure Authorized Redirect URI

Add:

```text
http://localhost:8001/auth/google/callback
```

This is the callback endpoint used by the TARO FastAPI backend.

### 6. Copy Your Credentials

After creating the OAuth client, Google will provide:

- Client ID
- Client Secret

Keep the Client Secret private.

### 7. Configure TARO

In the backend terminal:

```bash
cd ~/TARO/backend
```

Set your credentials:

```bash
export GOOGLE_CLIENT_ID="your-client-id"
export GOOGLE_CLIENT_SECRET="your-client-secret"
```

Example:

```bash
export GOOGLE_CLIENT_ID="123456789-abc123.apps.googleusercontent.com"
export GOOGLE_CLIENT_SECRET="your-secret"
```

Do **not** commit these credentials to GitHub.

### 8. Start TARO

Start the backend:

```bash
cd ~/TARO/backend
python -m uvicorn main:app --reload
```

In another terminal, start the frontend:

```bash
cd ~/TARO/frontend
npm run dev
```

Open:

```text
http://localhost:5173
```

You can now use:

**Continue with Google**

### OAuth Configuration Summary

| Setting           | Value                                        |
| ----------------- | -------------------------------------------- |
| Application type  | Web application                              |
| JavaScript origin | `http://localhost:5173`                      |
| Redirect URI      | `http://localhost:8001/auth/google/callback` |
| Audience          | External                                     |
| Environment       | Development / Testing                        |

### ⚠️ Important

Every developer running TARO locally should create and use **their own Google OAuth credentials**.

Do not share your:

- Google Client Secret
- `.env` file
- OAuth credentials
