<script setup>
import { nextTick, onMounted, ref } from "vue";
import LoginView from "./components/LoginView.vue";

const API_URL = "http://localhost:8001";

// ─── Auth state ───────────────────────────────────────────────────────────────
const authToken = ref(localStorage.getItem("taro_token") || "");
const authUsername = ref(localStorage.getItem("taro_username") || "");
const isAuthenticated = ref(false);

function onAuthenticated({ token, username }) {
  authToken.value = token;
  authUsername.value = username;
  isAuthenticated.value = true;
  // Load sidebar list but don't open any conversation — start fresh
  loadConversations(false);
}

async function logout() {
  try {
    await fetch(`${API_URL}/auth/logout`, {
      method: "POST",
      headers: { Authorization: `Bearer ${authToken.value}` },
    });
  } catch (_) {
    // best-effort
  }

  localStorage.removeItem("taro_token");
  localStorage.removeItem("taro_username");
  authToken.value = "";
  authUsername.value = "";
  isAuthenticated.value = false;
  conversations.value = [];
  messages.value = [];
  activeConversationId.value = null;
}

// ─────────────────────────────────────────────────────────────────────────────

const message = ref("");
const messages = ref([]);
const conversations = ref([]);
const activeConversationId = ref(null);

const loading = ref(false);
const loadingConversations = ref(false);

// Delete confirmation modal
const showDeleteModal = ref(false);
const pendingDeleteId = ref(null);

// Image attachment
const attachedImage = ref(null); // { dataUrl, base64, name }
const imageInputRef = ref(null);

const messagesContainer = ref(null);

async function loadConversations(openLast = false) {
  loadingConversations.value = true;

  try {
    const res = await fetch(`${API_URL}/conversations`);

    if (!res.ok) throw new Error(`HTTP error: ${res.status}`);

    conversations.value = await res.json();

    if (
      openLast &&
      conversations.value.length > 0 &&
      !activeConversationId.value
    ) {
      await openConversation(conversations.value[0].id);
    }
  } catch (error) {
    console.error("Failed to load conversations:", error);
  } finally {
    loadingConversations.value = false;
  }
}

async function createNewChat() {
  try {
    const res = await fetch(`${API_URL}/conversations`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: "New Chat" }),
    });

    if (!res.ok) throw new Error(`HTTP error: ${res.status}`);

    const conversation = await res.json();

    conversations.value.unshift({
      ...conversation,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    });

    activeConversationId.value = conversation.id;
    messages.value = [];

    await nextTick();
    scrollToBottom();
    return conversation.id;
  } catch (error) {
    console.error("Failed to create conversation:", error);
  }
}

async function openConversation(conversationId) {
  if (loading.value) return;

  try {
    const res = await fetch(`${API_URL}/conversations/${conversationId}`);

    if (!res.ok) throw new Error(`HTTP error: ${res.status}`);

    const data = await res.json();

    activeConversationId.value = conversationId;
    messages.value = data.messages || [];

    await nextTick();
    scrollToBottom();
  } catch (error) {
    console.error("Failed to open conversation:", error);
  }
}

function triggerImagePicker() {
  imageInputRef.value?.click();
}

function onImageSelected(event) {
  const file = event.target.files?.[0];
  if (!file) return;

  // Reset so the same file can be re-selected after clearing
  event.target.value = "";

  const reader = new FileReader();
  reader.onload = (e) => {
    const dataUrl = e.target.result;
    // Strip the "data:image/...;base64," prefix — Ollama wants raw base64
    const base64 = dataUrl.split(",")[1];
    attachedImage.value = { dataUrl, base64, name: file.name };
  };
  reader.readAsDataURL(file);
}

function clearImage() {
  attachedImage.value = null;
}

async function sendMessage() {
  const text = message.value.trim();
  const image = attachedImage.value;

  // Need at least text or an image
  if ((!text && !image) || loading.value) return;

  if (!activeConversationId.value) {
    await createNewChat();
  }

  const conversationId = activeConversationId.value;

  // Show user message — include image preview if attached
  messages.value.push({
    role: "user",
    content: text,
    imagePreview: image ? image.dataUrl : null,
  });

  message.value = "";
  const sentImage = image;
  attachedImage.value = null;
  loading.value = true;

  messages.value.push({ role: "assistant", content: "" });

  const assistantMessage = messages.value[messages.value.length - 1];

  await nextTick();
  scrollToBottom();

  try {
    const body = { content: text || " " };
    if (sentImage) body.image_base64 = sentImage.base64;

    const res = await fetch(
      `${API_URL}/conversations/${conversationId}/messages/stream`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      },
    );

    if (!res.ok) throw new Error(`HTTP error: ${res.status}`);
    if (!res.body) throw new Error("Streaming not supported.");

    const reader = res.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      assistantMessage.content += decoder.decode(value, { stream: true });

      await nextTick();
      scrollToBottom();
    }

    const remaining = decoder.decode();
    if (remaining) assistantMessage.content += remaining;

    await refreshConversationList();
  } catch (error) {
    console.error("Streaming error:", error);
    assistantMessage.content = "Something went wrong. Please try again.";
  } finally {
    loading.value = false;
  }
}

async function refreshConversationList() {
  try {
    const res = await fetch(`${API_URL}/conversations`);
    if (!res.ok) throw new Error(`HTTP error: ${res.status}`);
    conversations.value = await res.json();
  } catch (error) {
    console.error("Failed to refresh conversations:", error);
  }
}

async function deleteConversation(conversationId) {
  pendingDeleteId.value = conversationId;
  showDeleteModal.value = true;
}

async function confirmDelete() {
  const conversationId = pendingDeleteId.value;
  showDeleteModal.value = false;
  pendingDeleteId.value = null;

  try {
    const res = await fetch(`${API_URL}/conversations/${conversationId}`, {
      method: "DELETE",
    });

    if (!res.ok) throw new Error(`HTTP error: ${res.status}`);

    conversations.value = conversations.value.filter(
      (c) => c.id !== conversationId,
    );

    if (activeConversationId.value === conversationId) {
      activeConversationId.value = null;
      messages.value = [];

      if (conversations.value.length > 0) {
        await openConversation(conversations.value[0].id);
      }
    }
  } catch (error) {
    console.error("Failed to delete conversation:", error);
  }
}

function cancelDelete() {
  showDeleteModal.value = false;
  pendingDeleteId.value = null;
}

function scrollToBottom() {
  if (!messagesContainer.value) return;
  messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
}

function formatDate(dateString) {
  if (!dateString) return "";
  const date = new Date(dateString.replace(" ", "T") + "Z");
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleDateString([], { month: "short", day: "numeric" });
}

onMounted(async () => {
  // Verify the stored token is still valid
  const token = localStorage.getItem("taro_token");

  if (token) {
    try {
      const res = await fetch(`${API_URL}/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (res.ok) {
        const data = await res.json();
        authToken.value = token;
        authUsername.value = data.username;
        isAuthenticated.value = true;
        await loadConversations(false);
        return;
      }
    } catch (_) {
      // backend unreachable — fall through to login
    }

    // Token invalid or expired — clear it
    localStorage.removeItem("taro_token");
    localStorage.removeItem("taro_username");
  }

  isAuthenticated.value = false;
});
</script>

<template>
  <!-- Show login if not authenticated -->
  <LoginView
    v-if="!isAuthenticated"
    :api-url="API_URL"
    @authenticated="onAuthenticated"
  />

  <main v-else class="app-shell">
    <!-- ── SIDEBAR ── -->
    <aside class="sidebar">
      <!-- Brand -->
      <div class="sidebar-top">
        <div class="brand">
          <div class="brand-icon">
            <img src="./assets/taro-logo.png" alt="TARO" class="logo-img" />
          </div>
          <div class="brand-text">
            <span class="brand-name">TARO</span>
            <span class="brand-sub">Personal AI</span>
          </div>
        </div>

        <button class="new-chat-btn" @click="createNewChat" title="New chat">
          <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
            <path
              d="M7.5 1v13M1 7.5h13"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
            />
          </svg>
          New Chat
        </button>
      </div>

      <!-- Conversation list -->
      <div class="conv-list-wrap">
        <p class="list-label">Recent</p>

        <div v-if="loadingConversations" class="list-empty">Loading…</div>

        <div v-else-if="conversations.length === 0" class="list-empty">
          No chats yet. Start one!
        </div>

        <div v-else class="conv-list">
          <button
            v-for="conv in conversations"
            :key="conv.id"
            class="conv-item"
            :class="{ active: activeConversationId === conv.id }"
            @click="openConversation(conv.id)"
          >
            <div class="conv-body">
              <span class="conv-title">{{ conv.title }}</span>
              <span class="conv-date">{{ formatDate(conv.updated_at) }}</span>
            </div>
            <button
              class="conv-delete"
              title="Delete"
              @click.stop="deleteConversation(conv.id)"
            >
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                <path
                  d="M1 1l10 10M11 1L1 11"
                  stroke="currentColor"
                  stroke-width="1.6"
                  stroke-linecap="round"
                />
              </svg>
            </button>
          </button>
        </div>
      </div>

      <!-- Footer -->
      <div class="sidebar-foot">
        <img src="./assets/taro-logo.png" alt="TARO" class="foot-logo" />
        <span class="foot-username">{{ authUsername }}</span>
        <button class="logout-btn" title="Sign out" @click="logout">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path
              d="M5 2H2a1 1 0 00-1 1v8a1 1 0 001 1h3M9 10l3-3-3-3M12 7H5"
              stroke="currentColor"
              stroke-width="1.5"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
          </svg>
        </button>
      </div>
    </aside>

    <!-- ── CHAT AREA ── -->
    <section class="chat">
      <!-- Header -->
      <header class="chat-header">
        <div class="header-title">
          {{
            conversations.find((c) => c.id === activeConversationId)?.title ||
            "TARO"
          }}
        </div>
        <div class="header-status">
          <span class="pulse"></span>
          Online
        </div>
      </header>

      <!-- Messages -->
      <div ref="messagesContainer" class="messages">
        <!-- Welcome -->
        <div v-if="messages.length === 0 && !loading" class="welcome">
          <div class="welcome-logo">
            <img src="./assets/taro-logo.png" alt="TARO" class="logo-img" />
          </div>
          <h2 class="welcome-title">Hey, I'm TARO.</h2>
          <p class="welcome-sub">Your personal AI. Ask me anything.</p>

          <div class="welcome-chips">
            <button class="chip" @click="message = 'What can you do?'">
              What can you do?
            </button>
            <button
              class="chip"
              @click="message = 'Tell me something interesting'"
            >
              Tell me something interesting
            </button>
            <button
              class="chip"
              @click="message = 'Help me think through an idea'"
            >
              Help me think through an idea
            </button>
          </div>
        </div>

        <!-- Message rows -->
        <div
          v-for="(msg, index) in messages"
          :key="msg.id || index"
          class="msg-row"
          :class="msg.role"
        >
          <!-- Assistant -->
          <template v-if="msg.role === 'assistant'">
            <div class="msg-avatar">
              <img src="./assets/taro-logo.png" alt="TARO" class="logo-img" />
            </div>
            <div class="msg-body">
              <span class="msg-sender">TARO</span>
              <div class="msg-bubble assistant-bubble">
                <template v-if="!msg.content && loading">
                  <div class="thinking">
                    <span></span><span></span><span></span>
                  </div>
                </template>
                <template v-else>{{ msg.content }}</template>
              </div>
            </div>
          </template>

          <!-- User -->
          <template v-else>
            <div class="msg-body user-body">
              <!-- Image attachment preview in message -->
              <img
                v-if="msg.imagePreview"
                :src="msg.imagePreview"
                class="msg-image-preview"
                alt="Attached image"
              />
              <div v-if="msg.content" class="msg-bubble user-bubble">
                {{ msg.content }}
              </div>
            </div>
          </template>
        </div>
      </div>

      <!-- Input -->
      <div class="input-area">
        <!-- Attached image preview strip -->
        <Transition name="preview">
          <div v-if="attachedImage" class="image-preview-strip">
            <div class="image-preview-card">
              <img
                :src="attachedImage.dataUrl"
                :alt="attachedImage.name"
                class="image-preview-thumb"
              />
              <button
                class="image-preview-remove"
                @click="clearImage"
                title="Remove"
              >
                <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                  <path
                    d="M1 1l8 8M9 1L1 9"
                    stroke="currentColor"
                    stroke-width="1.8"
                    stroke-linecap="round"
                  />
                </svg>
              </button>
            </div>
            <span class="image-preview-name">{{ attachedImage.name }}</span>
          </div>
        </Transition>

        <form class="input-form" @submit.prevent="sendMessage">
          <!-- Hidden file input -->
          <input
            ref="imageInputRef"
            type="file"
            accept="image/*"
            class="file-input-hidden"
            @change="onImageSelected"
          />

          <!-- Attach button -->
          <button
            type="button"
            class="attach-btn"
            :class="{ 'has-image': attachedImage }"
            :disabled="loading"
            title="Attach image"
            @click="triggerImagePicker"
          >
            <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
              <path
                d="M12.5 7.5l-4.5 4.5a3.5 3.5 0 01-4.95-4.95l5-5a2 2 0 012.83 2.83l-5 5a.5.5 0 01-.71-.71l4.5-4.5"
                stroke="currentColor"
                stroke-width="1.5"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
            </svg>
          </button>

          <input
            v-model="message"
            class="input-field"
            placeholder="Message TARO…"
            :disabled="loading"
            autocomplete="off"
            @keydown.enter.exact.prevent="sendMessage"
          />
          <button
            type="submit"
            class="send-btn"
            :disabled="loading || (!message.trim() && !attachedImage)"
            :class="{ active: (message.trim() || attachedImage) && !loading }"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path
                d="M2 8h12M9 3l5 5-5 5"
                stroke="currentColor"
                stroke-width="1.8"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
            </svg>
          </button>
        </form>
        <p class="input-hint">TARO can make mistakes. Verify important info.</p>
      </div>
    </section>

    <!-- ── DELETE MODAL ── -->
    <Transition name="modal">
      <div
        v-if="showDeleteModal"
        class="modal-backdrop"
        @click.self="cancelDelete"
      >
        <div class="modal">
          <div class="modal-icon">
            <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
              <path
                d="M8 4h6M3 7h16M5 7l1 11a2 2 0 002 2h6a2 2 0 002-2l1-11"
                stroke="currentColor"
                stroke-width="1.7"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
              <path
                d="M9 11v4M13 11v4"
                stroke="currentColor"
                stroke-width="1.7"
                stroke-linecap="round"
              />
            </svg>
          </div>
          <div class="modal-body">
            <h3 class="modal-title">Delete conversation?</h3>
            <p class="modal-desc">
              This can't be undone. The conversation and all its messages will
              be permanently removed.
            </p>
          </div>
          <div class="modal-actions">
            <button class="modal-btn modal-btn--cancel" @click="cancelDelete">
              Cancel
            </button>
            <button class="modal-btn modal-btn--confirm" @click="confirmDelete">
              Delete
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </main>
</template>

<style scoped>
/* ─── Reset & base ─────────────────────────── */
*,
*::before,
*::after {
  box-sizing: border-box;
}

.app-shell {
  display: flex;
  width: 100%;
  height: 100vh;
  overflow: hidden;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  /* Rich gradient background — the glass sidebar blurs through this */
  background:
    radial-gradient(
      ellipse 60% 50% at 10% 20%,
      rgba(140, 60, 180, 0.35) 0%,
      transparent 60%
    ),
    radial-gradient(
      ellipse 50% 60% at 80% 80%,
      rgba(200, 80, 140, 0.25) 0%,
      transparent 55%
    ),
    radial-gradient(
      ellipse 40% 40% at 50% 50%,
      rgba(80, 40, 120, 0.2) 0%,
      transparent 70%
    ),
    #0a0710;
  color: #e8e0ee;
}

.logo-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  border-radius: 6px;
}

/* ─── Sidebar ──────────────────────────────── */

.sidebar {
  width: 260px;
  min-width: 260px;
  height: 100vh;
  display: flex;
  flex-direction: column;
  /* Glass panel */
  background: rgba(18, 10, 28, 0.45);
  backdrop-filter: blur(24px) saturate(160%);
  -webkit-backdrop-filter: blur(24px) saturate(160%);
  border-right: 1px solid rgba(255, 255, 255, 0.07);
  box-shadow: inset -1px 0 0 rgba(255, 255, 255, 0.04);
}

/* Brand */
.sidebar-top {
  padding: 22px 16px 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.brand {
  display: flex;
  align-items: center;
  gap: 11px;
  margin-bottom: 18px;
}

.brand-icon {
  width: 38px;
  height: 38px;
  flex-shrink: 0;
  border-radius: 11px;
  overflow: hidden;
  background: rgba(219, 112, 163, 0.18);
  padding: 5px;
  box-shadow: 0 2px 8px rgba(200, 80, 150, 0.2);
}

.brand-text {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.brand-name {
  font-size: 17px;
  font-weight: 700;
  color: #f0e8f6;
  letter-spacing: -0.3px;
}

.brand-sub {
  font-size: 11px;
  color: rgba(200, 180, 220, 0.45);
}

.new-chat-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px 14px;
  border: 1px solid rgba(219, 112, 163, 0.22);
  border-radius: 10px;
  background: rgba(219, 112, 163, 0.08);
  backdrop-filter: blur(8px);
  color: #d47ab2;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.18s ease;
  letter-spacing: 0.01em;
}

.new-chat-btn:hover {
  background: rgba(219, 112, 163, 0.18);
  border-color: rgba(219, 112, 163, 0.45);
  color: #e896c8;
  box-shadow: 0 0 16px rgba(200, 80, 150, 0.15);
}

/* Conversation list */
.conv-list-wrap {
  flex: 1;
  overflow-y: auto;
  padding: 12px 10px;
  scrollbar-width: thin;
  scrollbar-color: rgba(255, 255, 255, 0.06) transparent;
}

.list-label {
  margin: 0 0 8px 6px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: rgba(180, 160, 200, 0.3);
}

.list-empty {
  padding: 12px 6px;
  font-size: 12px;
  color: rgba(180, 160, 200, 0.3);
  line-height: 1.5;
}

.conv-list {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.conv-item {
  position: relative;
  width: 100%;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 10px;
  border: none;
  border-radius: 10px;
  background: transparent;
  color: rgba(200, 180, 220, 0.55);
  text-align: left;
  cursor: pointer;
  transition: all 0.15s ease;
}

.conv-item:hover {
  background: rgba(255, 255, 255, 0.05);
  color: #d4c4e4;
  border: 1px solid rgba(255, 255, 255, 0.06);
  /* Subtle inner glass card on hover */
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.06);
}

/* Reset default border for non-hover state */
.conv-item {
  border: 1px solid transparent;
}

.conv-item.active {
  background: rgba(200, 96, 160, 0.14);
  border-color: rgba(200, 96, 160, 0.22);
  color: #ecc8de;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.08),
    0 2px 12px rgba(180, 60, 130, 0.12);
}

.conv-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.conv-title {
  font-size: 13px;
  font-weight: 500;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  line-height: 1.35;
}

.conv-date {
  font-size: 10px;
  color: rgba(180, 160, 200, 0.3);
}

.conv-item.active .conv-date {
  color: rgba(220, 170, 200, 0.5);
}

.conv-delete {
  opacity: 0;
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  display: grid;
  place-items: center;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: rgba(180, 140, 180, 0.4);
  cursor: pointer;
  transition: all 0.15s ease;
}

.conv-item:hover .conv-delete {
  opacity: 1;
}

.conv-delete:hover {
  background: rgba(220, 80, 100, 0.18);
  color: #e06070;
}

/* Footer */
.sidebar-foot {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 14px 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  background: rgba(0, 0, 0, 0.1);
}

.foot-logo {
  width: 20px;
  height: 20px;
  object-fit: contain;
  border-radius: 5px;
  opacity: 0.35;
  flex-shrink: 0;
}

.foot-username {
  flex: 1;
  font-size: 12px;
  font-weight: 600;
  color: rgba(200, 180, 220, 0.5);
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.logout-btn {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: rgba(180, 140, 180, 0.4);
  cursor: pointer;
  transition: all 0.15s ease;
}

.logout-btn:hover {
  background: rgba(220, 80, 100, 0.15);
  color: #e06878;
}

/* ─── Chat area ────────────────────────────── */

.chat {
  flex: 1;
  min-width: 0;
  height: 100vh;
  display: flex;
  flex-direction: column;
  /* Frosted light panel — sits over the gradient background */
  background: rgba(247, 244, 249, 0.6);
  backdrop-filter: blur(32px) saturate(150%);
  -webkit-backdrop-filter: blur(32px) saturate(150%);
}

/* Header */
.chat-header {
  height: 64px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 36px;
  background: rgba(247, 244, 249, 0.55);
  backdrop-filter: blur(20px) saturate(160%);
  -webkit-backdrop-filter: blur(20px) saturate(160%);
  border-bottom: 1px solid rgba(180, 140, 200, 0.15);
  box-shadow: 0 1px 0 rgba(255, 255, 255, 0.6) inset;
}

.header-title {
  font-size: 15px;
  font-weight: 650;
  color: #1e1826;
  letter-spacing: -0.2px;
  max-width: 60%;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.header-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: #9a8aaa;
}

.pulse {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #5cc98a;
  box-shadow: 0 0 0 0 rgba(92, 201, 138, 0.4);
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% {
    box-shadow: 0 0 0 0 rgba(92, 201, 138, 0.4);
  }
  70% {
    box-shadow: 0 0 0 6px rgba(92, 201, 138, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(92, 201, 138, 0);
  }
}

/* Messages */
.messages {
  flex: 1;
  overflow-y: auto;
  padding: 36px clamp(16px, 8vw, 120px) 24px;
  scroll-behavior: smooth;
  scrollbar-width: thin;
  scrollbar-color: rgba(160, 120, 180, 0.15) transparent;
}

/* Welcome */
.welcome {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  gap: 0;
}

.welcome-logo {
  width: 72px;
  height: 72px;
  padding: 10px;
  border-radius: 24px;
  /* Glass logo container */
  background: rgba(230, 210, 248, 0.5);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 1px solid rgba(200, 160, 230, 0.3);
  box-shadow:
    0 4px 24px rgba(160, 80, 200, 0.12),
    inset 0 1px 0 rgba(255, 255, 255, 0.7);
  margin-bottom: 20px;
}

.welcome-title {
  margin: 0 0 8px;
  font-size: 28px;
  font-weight: 700;
  color: #1a1422;
  letter-spacing: -0.5px;
}

.welcome-sub {
  margin: 0 0 28px;
  font-size: 14px;
  color: #9a8aaa;
}

.welcome-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
  max-width: 480px;
}

.chip {
  padding: 9px 16px;
  border: 1px solid rgba(180, 120, 200, 0.2);
  border-radius: 99px;
  /* Glass chip */
  background: rgba(255, 255, 255, 0.45);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  color: #4a3a5a;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s ease;
  box-shadow:
    0 1px 4px rgba(0, 0, 0, 0.05),
    inset 0 1px 0 rgba(255, 255, 255, 0.7);
}

.chip:hover {
  background: rgba(240, 220, 255, 0.6);
  border-color: rgba(180, 100, 160, 0.35);
  color: #7a3a6a;
  box-shadow:
    0 4px 16px rgba(160, 80, 180, 0.1),
    inset 0 1px 0 rgba(255, 255, 255, 0.8);
}

/* Message rows */
.msg-row {
  display: flex;
  gap: 12px;
  margin-bottom: 28px;
}

.msg-row.user {
  justify-content: flex-end;
}

.msg-avatar {
  width: 32px;
  height: 32px;
  flex-shrink: 0;
  padding: 5px;
  border-radius: 10px;
  /* Glass avatar */
  background: rgba(220, 190, 240, 0.45);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border: 1px solid rgba(200, 160, 230, 0.25);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.6);
  margin-top: 2px;
}

.msg-body {
  max-width: min(680px, 75%);
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.user-body {
  align-items: flex-end;
}

.msg-sender {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: #b090c0;
  padding: 0 4px;
}

.msg-bubble {
  padding: 13px 17px;
  border-radius: 18px;
  font-size: 14px;
  line-height: 1.6;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.assistant-bubble {
  /* Glass card for TARO responses */
  background: rgba(255, 255, 255, 0.55);
  backdrop-filter: blur(16px) saturate(140%);
  -webkit-backdrop-filter: blur(16px) saturate(140%);
  color: #2a1e36;
  border: 1px solid rgba(200, 160, 230, 0.2);
  border-bottom-left-radius: 5px;
  box-shadow:
    0 2px 12px rgba(160, 80, 180, 0.07),
    0 8px 32px rgba(0, 0, 0, 0.05),
    inset 0 1px 0 rgba(255, 255, 255, 0.8);
}

.user-bubble {
  background: linear-gradient(135deg, #c8609a, #a044c0);
  color: #fff;
  border-bottom-right-radius: 5px;
  box-shadow:
    0 2px 12px rgba(168, 60, 180, 0.25),
    inset 0 1px 0 rgba(255, 255, 255, 0.15);
}

/* Thinking dots */
.thinking {
  display: flex;
  gap: 5px;
  padding: 4px 2px;
}

.thinking span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #c090d0;
  animation: think 1.3s infinite ease-in-out;
}

.thinking span:nth-child(2) {
  animation-delay: 0.18s;
}
.thinking span:nth-child(3) {
  animation-delay: 0.36s;
}

@keyframes think {
  0%,
  60%,
  100% {
    transform: translateY(0);
    opacity: 0.35;
  }
  30% {
    transform: translateY(-5px);
    opacity: 1;
  }
}

/* ─── Input area ───────────────────────────── */

.input-area {
  padding: 12px clamp(16px, 8vw, 120px) 20px;
}

.input-form {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 8px 8px 20px;
  /* Glass input bar */
  background: rgba(255, 255, 255, 0.5);
  backdrop-filter: blur(20px) saturate(150%);
  -webkit-backdrop-filter: blur(20px) saturate(150%);
  border: 1px solid rgba(180, 130, 210, 0.2);
  border-radius: 18px;
  box-shadow:
    0 4px 24px rgba(160, 80, 180, 0.08),
    0 1px 0 rgba(255, 255, 255, 0.9) inset;
  transition:
    border-color 0.2s,
    box-shadow 0.2s;
}

.input-form:focus-within {
  border-color: rgba(180, 80, 160, 0.4);
  box-shadow:
    0 4px 24px rgba(160, 80, 180, 0.12),
    0 0 0 3px rgba(180, 80, 160, 0.08),
    0 1px 0 rgba(255, 255, 255, 0.9) inset;
}

.input-field {
  flex: 1;
  min-width: 0;
  padding: 8px 0;
  border: none;
  outline: none;
  background: transparent;
  font-size: 14px;
  color: #1e1826;
  font-family: inherit;
}

.input-field::placeholder {
  color: #b8a8c8;
}

.send-btn {
  width: 38px;
  height: 38px;
  flex-shrink: 0;
  display: grid;
  place-items: center;
  border: none;
  border-radius: 12px;
  background: rgba(210, 190, 230, 0.5);
  color: #9878b0;
  cursor: pointer;
  transition: all 0.18s ease;
}

.send-btn.active {
  background: linear-gradient(135deg, #c8609a, #a044c0);
  color: #fff;
  box-shadow: 0 4px 14px rgba(168, 60, 180, 0.3);
}

.send-btn.active:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 18px rgba(168, 60, 180, 0.4);
}

.send-btn:disabled:not(.active) {
  opacity: 0.4;
  cursor: not-allowed;
}

.input-hint {
  margin: 7px 0 0;
  text-align: center;
  font-size: 10px;
  color: #b8a8c8;
}

/* ─── Responsive ───────────────────────────── */

@media (max-width: 720px) {
  .sidebar {
    width: 220px;
    min-width: 220px;
  }

  .chat-header {
    padding: 0 20px;
  }
}

@media (max-width: 580px) {
  .sidebar {
    display: none;
  }

  .messages {
    padding: 24px 16px 16px;
  }

  .input-area {
    padding: 8px 12px 16px;
  }
}

/* ─── Delete modal ─────────────────────────── */

.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 100;
  display: grid;
  place-items: center;
  background: rgba(10, 6, 18, 0.65);
  backdrop-filter: blur(6px);
}

.modal {
  width: min(400px, calc(100vw - 40px));
  /* Glass modal card */
  background: rgba(28, 18, 42, 0.65);
  backdrop-filter: blur(28px) saturate(160%);
  -webkit-backdrop-filter: blur(28px) saturate(160%);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 20px;
  padding: 28px 28px 24px;
  box-shadow:
    0 24px 60px rgba(0, 0, 0, 0.45),
    0 0 0 1px rgba(255, 255, 255, 0.04) inset,
    inset 0 1px 0 rgba(255, 255, 255, 0.06);
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.modal-icon {
  width: 46px;
  height: 46px;
  display: grid;
  place-items: center;
  border-radius: 13px;
  background: rgba(220, 70, 90, 0.12);
  color: #e06878;
}

.modal-title {
  margin: 0 0 6px;
  font-size: 17px;
  font-weight: 700;
  color: #f0e8f8;
  letter-spacing: -0.2px;
}

.modal-desc {
  margin: 0;
  font-size: 13px;
  color: #7a6a8a;
  line-height: 1.55;
}

.modal-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

.modal-btn {
  padding: 10px 22px;
  border-radius: 11px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  transition: all 0.15s ease;
}

.modal-btn--cancel {
  background: rgba(255, 255, 255, 0.06);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  color: #9a8aaa;
}

.modal-btn--cancel:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.14);
  color: #c4b4d4;
}

.modal-btn--confirm {
  background: rgba(220, 70, 90, 0.15);
  color: #e06878;
  border: 1px solid rgba(220, 70, 90, 0.25);
}

.modal-btn--confirm:hover {
  background: rgba(220, 70, 90, 0.25);
  border-color: rgba(220, 70, 90, 0.45);
  color: #f08090;
}

/* Modal transition */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s ease;
}

.modal-enter-active .modal,
.modal-leave-active .modal {
  transition:
    opacity 0.2s ease,
    transform 0.2s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from .modal,
.modal-leave-to .modal {
  opacity: 0;
  transform: scale(0.95) translateY(8px);
}

/* ─── Image input & preview ────────────────── */

.file-input-hidden {
  display: none;
}

.attach-btn {
  flex-shrink: 0;
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border: none;
  border-radius: 10px;
  background: transparent;
  color: #9a82b0;
  cursor: pointer;
  transition: all 0.15s ease;
}

.attach-btn:hover:not(:disabled) {
  background: rgba(180, 100, 160, 0.12);
  color: #c090d0;
}

.attach-btn.has-image {
  color: #c8609a;
  background: rgba(200, 96, 154, 0.15);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.3);
}

.attach-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.image-preview-strip {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 4px 10px;
}

.image-preview-card {
  position: relative;
  flex-shrink: 0;
}

.image-preview-thumb {
  width: 52px;
  height: 52px;
  border-radius: 10px;
  object-fit: cover;
  border: 1px solid rgba(200, 160, 230, 0.25);
  box-shadow:
    0 2px 8px rgba(160, 80, 180, 0.12),
    inset 0 1px 0 rgba(255, 255, 255, 0.4);
  display: block;
}

.image-preview-remove {
  position: absolute;
  top: -6px;
  right: -6px;
  width: 18px;
  height: 18px;
  display: grid;
  place-items: center;
  border: none;
  border-radius: 50%;
  background: rgba(40, 20, 60, 0.7);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  color: #c0a0d0;
  cursor: pointer;
  transition: all 0.15s ease;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.2);
}

.image-preview-remove:hover {
  background: rgba(194, 78, 112, 0.85);
  color: #fff;
}

.image-preview-name {
  font-size: 11px;
  color: #9a8aaa;
  max-width: 160px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

/* Image in message bubble */
.msg-image-preview {
  max-width: 280px;
  max-height: 220px;
  border-radius: 14px;
  object-fit: cover;
  display: block;
  border: 1px solid rgba(200, 160, 230, 0.2);
  box-shadow:
    0 4px 20px rgba(160, 80, 180, 0.12),
    inset 0 1px 0 rgba(255, 255, 255, 0.3);
}

/* Preview strip enter/leave transition */
.preview-enter-active,
.preview-leave-active {
  transition:
    opacity 0.2s ease,
    transform 0.2s ease;
}

.preview-enter-from,
.preview-leave-to {
  opacity: 0;
  transform: translateY(6px);
}
</style>
