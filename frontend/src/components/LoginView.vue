<script setup>
import { onMounted, ref } from "vue";

const props = defineProps({
  apiUrl: { type: String, required: true },
});

const emit = defineEmits(["authenticated"]);

const mode = ref("login");
const username = ref("");
const email = ref("");
const password = ref("");
const confirmPassword = ref("");
const error = ref("");
const loading = ref(false);

function switchMode(m) {
  mode.value = m;
  error.value = "";
  username.value = "";
  email.value = "";
  password.value = "";
  confirmPassword.value = "";
}

async function submit() {
  error.value = "";

  if (mode.value === "register") {
    if (!username.value.trim() || !email.value.trim() || !password.value) {
      error.value = "Please fill in all fields.";
      return;
    }
    if (password.value.length < 6) {
      error.value = "Password must be at least 6 characters.";
      return;
    }
    if (password.value !== confirmPassword.value) {
      error.value = "Passwords do not match.";
      return;
    }
  } else {
    if (!email.value.trim() || !password.value) {
      error.value = "Please fill in all fields.";
      return;
    }
  }

  loading.value = true;

  try {
    const endpoint = mode.value === "login" ? "/auth/login" : "/auth/register";
    const body =
      mode.value === "login"
        ? { email: email.value.trim().toLowerCase(), password: password.value }
        : {
            username: username.value.trim(),
            email: email.value.trim().toLowerCase(),
            password: password.value,
          };

    const res = await fetch(`${props.apiUrl}${endpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    const data = await res.json();

    if (!res.ok) {
      error.value = data.detail || "Something went wrong.";
      return;
    }

    localStorage.setItem("taro_token", data.token);
    localStorage.setItem("taro_username", data.username);
    emit("authenticated", { token: data.token, username: data.username });
  } catch {
    error.value = "Could not connect to TARO. Is the backend running?";
  } finally {
    loading.value = false;
  }
}

function loginWithGoogle() {
  window.location.href = `${props.apiUrl}/auth/google`;
}

onMounted(() => {
  const params = new URLSearchParams(window.location.search);
  const token = params.get("token");
  const uname = params.get("username");
  const authError = params.get("auth_error");

  if (authError) {
    error.value =
      authError === "google_denied"
        ? "Google sign-in was cancelled."
        : "Google sign-in failed. Please try again.";
    window.history.replaceState({}, "", "/");
    return;
  }

  if (token && uname) {
    localStorage.setItem("taro_token", token);
    localStorage.setItem("taro_username", uname);
    window.history.replaceState({}, "", "/");
    emit("authenticated", { token, username: uname });
  }
});
</script>

<template>
  <div class="shell">
    <!-- Soft background orbs -->
    <div class="orb orb-1"></div>
    <div class="orb orb-2"></div>

    <div class="card" :class="{ wide: mode === 'register' }">
      <!-- Header -->
      <div class="card-head">
        <div class="avatar">
          <img src="../assets/taro-logo.png" alt="TARO" />
        </div>
        <h1>TARO</h1>
        <p>Your personal AI</p>
      </div>

      <!-- Google -->
      <button class="google-btn" @click="loginWithGoogle" :disabled="loading">
        <svg viewBox="0 0 24 24" width="16" height="16" style="flex-shrink: 0">
          <path
            fill="#4285F4"
            d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
          />
          <path
            fill="#34A853"
            d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
          />
          <path
            fill="#FBBC05"
            d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z"
          />
          <path
            fill="#EA4335"
            d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
          />
        </svg>
        Continue with Google
      </button>

      <!-- Divider -->
      <div class="divider"><span></span><em>or</em><span></span></div>

      <!-- Tabs -->
      <div class="tabs">
        <button
          :class="{ active: mode === 'login' }"
          @click="switchMode('login')"
        >
          Sign in
        </button>
        <button
          :class="{ active: mode === 'register' }"
          @click="switchMode('register')"
        >
          Create account
        </button>
      </div>

      <!-- Form -->
      <form @submit.prevent="submit">
        <!-- Register — 2 col grid -->
        <div v-if="mode === 'register'" class="grid-2">
          <div class="field">
            <label>Name</label>
            <input
              v-model="username"
              type="text"
              placeholder="Your name"
              autocomplete="name"
              :disabled="loading"
            />
          </div>
          <div class="field">
            <label>Password</label>
            <input
              v-model="password"
              type="password"
              placeholder="Min. 6 chars"
              autocomplete="new-password"
              :disabled="loading"
            />
          </div>
          <div class="field">
            <label>Email</label>
            <input
              v-model="email"
              type="email"
              placeholder="you@example.com"
              autocomplete="email"
              :disabled="loading"
            />
          </div>
          <div class="field">
            <label>Confirm password</label>
            <input
              v-model="confirmPassword"
              type="password"
              placeholder="Repeat password"
              autocomplete="new-password"
              :disabled="loading"
            />
          </div>
        </div>

        <!-- Login — single col -->
        <div v-else class="col-1">
          <div class="field">
            <label>Email</label>
            <input
              v-model="email"
              type="email"
              placeholder="you@example.com"
              autocomplete="email"
              :disabled="loading"
            />
          </div>
          <div class="field">
            <label>Password</label>
            <input
              v-model="password"
              type="password"
              placeholder="Enter your password"
              autocomplete="current-password"
              :disabled="loading"
            />
          </div>
        </div>

        <!-- Error -->
        <p v-if="error" class="error">{{ error }}</p>

        <!-- Submit -->
        <button type="submit" class="submit" :disabled="loading">
          <span v-if="loading" class="dots"
            ><span></span><span></span><span></span
          ></span>
          <span v-else>{{
            mode === "login" ? "Sign in" : "Create account"
          }}</span>
        </button>
      </form>

      <p class="hint">TARO runs locally. Your data stays private.</p>
    </div>
  </div>
</template>

<style scoped>
/* ── Shell ── */
.shell {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background:
    radial-gradient(
      ellipse 65% 55% at 10% 15%,
      rgba(130, 50, 180, 0.45) 0%,
      transparent 55%
    ),
    radial-gradient(
      ellipse 55% 65% at 90% 80%,
      rgba(190, 70, 130, 0.35) 0%,
      transparent 55%
    ),
    #080510;
  overflow: hidden;
}

.orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(70px);
  pointer-events: none;
  opacity: 0.6;
}
.orb-1 {
  width: 400px;
  height: 400px;
  background: rgba(150, 50, 200, 0.25);
  top: -120px;
  left: -80px;
  animation: drift 14s ease-in-out infinite alternate;
}
.orb-2 {
  width: 300px;
  height: 300px;
  background: rgba(190, 60, 130, 0.2);
  bottom: -80px;
  right: -60px;
  animation: drift 18s ease-in-out infinite alternate-reverse;
}

@keyframes drift {
  from {
    transform: translate(0, 0);
  }
  to {
    transform: translate(30px, 20px);
  }
}

/* ── Card ── */
.card {
  width: 340px;
  background: rgba(16, 9, 28, 0.6);
  backdrop-filter: blur(24px) saturate(150%);
  -webkit-backdrop-filter: blur(24px) saturate(150%);
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 18px;
  padding: 28px 24px 20px;
  box-shadow:
    0 24px 64px rgba(0, 0, 0, 0.55),
    inset 0 1px 0 rgba(255, 255, 255, 0.06);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.card.wide {
  width: 480px;
}

/* ── Header ── */
.card-head {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  margin-bottom: 2px;
}

.avatar {
  width: 52px;
  height: 52px;
  padding: 8px;
  border-radius: 14px;
  background: rgba(190, 80, 150, 0.15);
  border: 1px solid rgba(200, 110, 170, 0.18);
  box-shadow:
    0 4px 16px rgba(160, 50, 140, 0.2),
    inset 0 1px 0 rgba(255, 255, 255, 0.08);
  margin-bottom: 6px;
}
.avatar img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  border-radius: 6px;
}

.card-head h1 {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  color: #f0e8f8;
  letter-spacing: -0.3px;
}
.card-head p {
  margin: 0;
  font-size: 11px;
  color: rgba(190, 165, 215, 0.45);
}

/* ── Google ── */
.google-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 9px;
  padding: 9px 14px;
  border: 1px solid rgba(255, 255, 255, 0.09);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(8px);
  color: #ddd0ee;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}
.google-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.09);
  border-color: rgba(255, 255, 255, 0.14);
}
.google-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

/* ── Divider ── */
.divider {
  display: flex;
  align-items: center;
  gap: 10px;
}
.divider span {
  flex: 1;
  height: 1px;
  background: rgba(255, 255, 255, 0.06);
}
.divider em {
  font-style: normal;
  font-size: 10px;
  color: rgba(180, 155, 205, 0.35);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

/* ── Tabs ── */
.tabs {
  display: flex;
  gap: 3px;
  padding: 3px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 10px;
}
.tabs button {
  flex: 1;
  padding: 7px;
  border: 1px solid transparent;
  border-radius: 7px;
  background: transparent;
  color: rgba(190, 165, 215, 0.4);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}
.tabs button.active {
  background: rgba(190, 80, 155, 0.18);
  border-color: rgba(190, 80, 155, 0.22);
  color: #e0b0d0;
}
.tabs button:not(.active):hover {
  color: rgba(210, 185, 235, 0.7);
  background: rgba(255, 255, 255, 0.04);
}

/* ── Form layouts ── */
.grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.col-1 {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

/* ── Fields ── */
.field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.field label {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: rgba(190, 165, 215, 0.38);
  padding-left: 1px;
}

.field input {
  width: 100%;
  padding: 8px 11px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 8px;
  color: #f0e8f8;
  font-size: 12px;
  font-family: inherit;
  outline: none;
  transition:
    border-color 0.15s,
    background 0.15s;
}
.field input::placeholder {
  color: rgba(170, 145, 195, 0.28);
}
.field input:focus {
  border-color: rgba(190, 80, 155, 0.4);
  background: rgba(255, 255, 255, 0.06);
  box-shadow: 0 0 0 3px rgba(190, 70, 150, 0.08);
}
.field input:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* Kill browser autofill white/yellow background */
.field input:-webkit-autofill,
.field input:-webkit-autofill:hover,
.field input:-webkit-autofill:focus {
  -webkit-box-shadow: 0 0 0 100px rgba(16, 9, 28, 0.95) inset;
  -webkit-text-fill-color: #f0e8f8;
  caret-color: #f0e8f8;
  border-color: rgba(190, 80, 155, 0.35);
}

/* ── Error ── */
.error {
  margin: 0;
  padding: 8px 12px;
  background: rgba(210, 60, 80, 0.1);
  border: 1px solid rgba(210, 60, 80, 0.18);
  border-radius: 8px;
  color: #f09090;
  font-size: 12px;
  line-height: 1.4;
}

/* ── Submit ── */
.submit {
  width: 100%;
  padding: 10px;
  border: none;
  border-radius: 10px;
  background: linear-gradient(135deg, #c8609a, #9c3cbe);
  color: #fff;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s ease;
  box-shadow: 0 4px 18px rgba(160, 50, 180, 0.3);
  letter-spacing: 0.01em;
}
.submit:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 22px rgba(160, 50, 180, 0.42);
}
.submit:disabled {
  opacity: 0.55;
  cursor: not-allowed;
  transform: none;
}

.dots {
  display: flex;
  justify-content: center;
  gap: 5px;
}
.dots span {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.75);
  animation: pulse-dot 1.2s infinite ease-in-out;
}
.dots span:nth-child(2) {
  animation-delay: 0.15s;
}
.dots span:nth-child(3) {
  animation-delay: 0.3s;
}

@keyframes pulse-dot {
  0%,
  60%,
  100% {
    transform: translateY(0);
    opacity: 0.35;
  }
  30% {
    transform: translateY(-4px);
    opacity: 1;
  }
}

/* ── Hint ── */
.hint {
  margin: 0;
  font-size: 10px;
  color: rgba(170, 145, 195, 0.22);
  text-align: center;
}
</style>
