<script setup>
import { computed, nextTick, ref } from "vue";
import { marked } from "marked";
import { sendChat } from "./api/chat";

marked.setOptions({ breaks: true, gfm: true });

const welcomeMessage = {
  role: "assistant",
  content: "你好，我是 Factory AI。请输入你的问题。",
  local: true,
};

const input = ref("");
const loading = ref(false);
const error = ref("");
const messages = ref([{ ...welcomeMessage }]);
const messageList = ref(null);
const canClear = computed(
  () => messages.value.length > 1 || input.value.trim() || error.value,
);

function renderMarkdown(content) {
  return marked.parse(content || "");
}

function clearConversation() {
  messages.value = [{ ...welcomeMessage }];
  input.value = "";
  error.value = "";
}

async function scrollToBottom() {
  await nextTick();
  if (messageList.value) {
    messageList.value.scrollTop = messageList.value.scrollHeight;
  }
}

async function submitMessage() {
  const content = input.value.trim();
  if (!content || loading.value) {
    return;
  }

  error.value = "";
  input.value = "";
  messages.value.push({ role: "user", content });
  const userMessageIndex = messages.value.length - 1;
  loading.value = true;
  await scrollToBottom();

  try {
    const requestMessages = messages.value.filter(
      (message) => message.role !== "system" && !message.local,
    );
    const result = await sendChat(requestMessages);
    messages.value.push(result.message);
  } catch (err) {
    messages.value.splice(userMessageIndex, 1);
    input.value = content;
    error.value = err.message || "聊天请求失败";
  } finally {
    loading.value = false;
    await scrollToBottom();
  }
}
</script>

<template>
  <main class="app-shell">
    <header class="topbar">
      <div>
        <h1>Factory AI Chat</h1>
        <p>本地 Qwen 多轮对话</p>
      </div>
      <div class="topbar-actions">
        <span class="service-pill">vLLM: localhost:8000</span>
        <button
          class="clear-button"
          type="button"
          :disabled="loading || !canClear"
          @click="clearConversation"
        >
          清空会话
        </button>
      </div>
    </header>

    <section ref="messageList" class="messages">
      <article
        v-for="(message, index) in messages"
        :key="`${message.role}-${index}`"
        class="message"
        :class="message.role"
      >
        <div class="role">
          {{ message.role === "user" ? "用户" : "Factory AI" }}
        </div>
        <div
          v-if="message.role === 'assistant'"
          class="content markdown-body"
          v-html="renderMarkdown(message.content)"
        ></div>
        <div v-else class="content">{{ message.content }}</div>
      </article>
      <article v-if="loading" class="message assistant">
        <div class="role">Factory AI</div>
        <div class="content">正在思考...</div>
      </article>
    </section>

    <p v-if="error" class="error">{{ error }}</p>

    <form class="composer" @submit.prevent="submitMessage">
      <textarea
        v-model="input"
        placeholder="输入问题，按 Ctrl+Enter 发送"
        :disabled="loading"
        @keydown.ctrl.enter.prevent="submitMessage"
      />
      <button type="submit" :disabled="loading || !input.trim()">
        {{ loading ? "发送中" : "发送" }}
      </button>
    </form>
  </main>
</template>
