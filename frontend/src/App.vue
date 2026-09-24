<script setup>
import { nextTick, onMounted, ref } from "vue";

const API_URL = "http://localhost:8001";

const message = ref("");
const messages = ref([]);
const conversations = ref([]);
const activeConversationId = ref(null);

const loading = ref(false);
const loadingConversations = ref(false);

const messagesContainer = ref(null);

async function loadConversations() {
  loadingConversations.value = true;

  try {
    const res = await fetch(`${API_URL}/conversations`);

    if (!res.ok) throw new Error(`HTTP error: ${res.status}`);

    conversations.value = await res.json();

    if (conversations.value.length > 0 && !activeConversationId.value) {
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

async function sendMessage() {
  const text = message.value.trim();

  if (!text || loading.value) return;

  if (!activeConversationId.value) {
    await createNewChat();
  }

  const conversationId = activeConversationId.value;

  messages.value.push({ role: "user", content: text });

  message.value = "";
  loading.value = true;

  messages.value.push({ role: "assistant", content: "" });

  const assistantMessage = messages.value[messages.value.length - 1];

  await nextTick();
  scrollToBottom();

  try {
    const res = await fetch(
      `${API_URL}/conversations/${conversationId}/messages/stream`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: text }),
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
  if (!confirm("Delete this conversation?")) return;

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

onMounted(() => {
  loadConversations();
});
</script>

<template>
  <main class="app-shell">
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
        <span class="foot-label">Local AI · Private</span>
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
              <div class="msg-bubble user-bubble">{{ msg.content }}</div>
            </div>
          </template>
        </div>
      </div>

      <!-- Input -->
      <div class="input-area">
        <form class="input-form" @submit.prevent="sendMessage">
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
            :disabled="loading || !message.trim()"
            :class="{ active: message.trim() && !loading }"
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
  background: #0e0b12;
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
  background: #100d16;
  border-right: 1px solid rgba(255, 255, 255, 0.06);
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
  background: rgba(219, 112, 163, 0.15);
  padding: 5px;
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
  color: #6b5f7a;
}

.new-chat-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px 14px;
  border: 1px solid rgba(219, 112, 163, 0.25);
  border-radius: 10px;
  background: rgba(219, 112, 163, 0.08);
  color: #d47ab2;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.18s ease;
  letter-spacing: 0.01em;
}

.new-chat-btn:hover {
  background: rgba(219, 112, 163, 0.16);
  border-color: rgba(219, 112, 163, 0.45);
  color: #e896c8;
}

/* Conversation list */
.conv-list-wrap {
  flex: 1;
  overflow-y: auto;
  padding: 12px 10px;
  scrollbar-width: thin;
  scrollbar-color: rgba(255, 255, 255, 0.08) transparent;
}

.list-label {
  margin: 0 0 8px 6px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: #4a4058;
}

.list-empty {
  padding: 12px 6px;
  font-size: 12px;
  color: #4a4058;
  line-height: 1.5;
}

.conv-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.conv-item {
  position: relative;
  width: 100%;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 10px;
  border: none;
  border-radius: 9px;
  background: transparent;
  color: #8a7a96;
  text-align: left;
  cursor: pointer;
  transition: all 0.15s ease;
}

.conv-item:hover {
  background: rgba(255, 255, 255, 0.04);
  color: #c4b4d4;
}

.conv-item.active {
  background: rgba(219, 112, 163, 0.12);
  color: #e8c4d8;
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
  color: #4a4058;
}

.conv-item.active .conv-date {
  color: #9a7a8a;
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
  color: #6a5a76;
  cursor: pointer;
  transition: all 0.15s ease;
}

.conv-item:hover .conv-delete {
  opacity: 1;
}

.conv-delete:hover {
  background: rgba(220, 80, 100, 0.15);
  color: #e06070;
}

/* Footer */
.sidebar-foot {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 14px 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}

.foot-logo {
  width: 20px;
  height: 20px;
  object-fit: contain;
  border-radius: 5px;
  opacity: 0.5;
}

.foot-label {
  font-size: 11px;
  color: #4a4058;
}

/* ─── Chat area ────────────────────────────── */

.chat {
  flex: 1;
  min-width: 0;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f7f4f9;
}

/* Header */
.chat-header {
  height: 64px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 36px;
  background: rgba(247, 244, 249, 0.9);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
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
  scrollbar-color: rgba(0, 0, 0, 0.1) transparent;
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
  background: #efe8f6;
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
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 99px;
  background: #fff;
  color: #4a3a5a;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s ease;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
}

.chip:hover {
  background: #f0e8f8;
  border-color: rgba(180, 100, 160, 0.3);
  color: #7a3a6a;
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
  background: #ede0f4;
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
  background: #fff;
  color: #2a1e36;
  border-bottom-left-radius: 5px;
  box-shadow:
    0 1px 3px rgba(0, 0, 0, 0.06),
    0 4px 16px rgba(0, 0, 0, 0.04);
}

.user-bubble {
  background: linear-gradient(135deg, #c8609a, #a044c0);
  color: #fff;
  border-bottom-right-radius: 5px;
  box-shadow: 0 2px 12px rgba(168, 60, 180, 0.25);
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
  background: #fff;
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 18px;
  box-shadow:
    0 2px 8px rgba(0, 0, 0, 0.06),
    0 8px 32px rgba(0, 0, 0, 0.04);
  transition:
    border-color 0.2s,
    box-shadow 0.2s;
}

.input-form:focus-within {
  border-color: rgba(180, 80, 160, 0.35);
  box-shadow:
    0 2px 8px rgba(0, 0, 0, 0.06),
    0 8px 32px rgba(168, 60, 180, 0.1);
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
  background: #e0d0ec;
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
</style>
