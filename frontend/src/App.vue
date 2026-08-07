<script setup>
import { computed, nextTick, onMounted, ref } from "vue";
import DOMPurify from "dompurify";
import { marked } from "marked";
import { sendChat } from "./api/chat";
import {
  adminLogin,
  clearAdminToken,
  fetchAdminApiSummary,
  getStoredAdminToken,
  storeAdminToken,
} from "./api/admin";

marked.setOptions({ breaks: true, gfm: true });

const welcomeMessage = {
  role: "assistant",
  content: "你好，我是 Factory AI。请输入你的问题。",
  local: true,
};

const activeView = ref("chat");
const input = ref("");
const loading = ref(false);
const error = ref("");
const messages = ref([{ ...welcomeMessage }]);
const messageList = ref(null);
const adminPassword = ref("");
const adminToken = ref(getStoredAdminToken());
const adminLoading = ref(false);
const adminError = ref("");
const adminSummary = ref(null);
const apiExample = ref({
  apiToken: "factory-dev-token",
  caller: "line-dashboard",
  taskType: "chat",
  line: "G77",
  station: "EWI",
  input: "Explain what this alarm means: EWI station cannot reach MOM.",
});
const copiedTarget = ref("");

const isAdminLoggedIn = computed(() => Boolean(adminToken.value));
const canClear = computed(
  () => messages.value.length > 1 || input.value.trim() || error.value,
);

const curlExample = computed(() => {
  const payload = buildExamplePayload();
  return `curl -X POST http://localhost:8080/api/v1/chat \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer ${apiExample.value.apiToken}" \\
  -d '${JSON.stringify(payload, null, 2)}'`;
});

const powershellExample = computed(() => {
  const metadata = buildExamplePayload().metadata;
  return `$body = @{
  input = "${escapePowerShellString(apiExample.value.input)}"
  caller = "${escapePowerShellString(apiExample.value.caller)}"
  task_type = "${escapePowerShellString(apiExample.value.taskType)}"
  metadata = @{
    line = "${escapePowerShellString(metadata.line)}"
    station = "${escapePowerShellString(metadata.station)}"
  }
} | ConvertTo-Json

Invoke-RestMethod \`
  -Uri "http://localhost:8080/api/v1/chat" \`
  -Method Post \`
  -Headers @{ Authorization = "Bearer ${escapePowerShellString(apiExample.value.apiToken)}" } \`
  -ContentType "application/json" \`
  -Body $body`;
});

onMounted(() => {
  if (adminToken.value) {
    loadAdminSummary();
  }
});

function renderMarkdown(content) {
  return DOMPurify.sanitize(marked.parse(content || ""));
}

function clearConversation() {
  messages.value = [{ ...welcomeMessage }];
  input.value = "";
  error.value = "";
}

function buildRequestMessages(content) {
  return [{ role: "user", content }];
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
    const result = await sendChat(buildRequestMessages(content));
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

async function submitAdminLogin() {
  const password = adminPassword.value.trim();
  if (!password || adminLoading.value) {
    return;
  }

  adminLoading.value = true;
  adminError.value = "";

  try {
    const token = await adminLogin(password);
    adminToken.value = token;
    storeAdminToken(token);
    adminPassword.value = "";
    await loadAdminSummary();
  } catch (err) {
    adminError.value = err.message || "管理员登录失败";
  } finally {
    adminLoading.value = false;
  }
}

async function loadAdminSummary() {
  if (!adminToken.value || adminLoading.value) {
    return;
  }

  adminLoading.value = true;
  adminError.value = "";

  try {
    adminSummary.value = await fetchAdminApiSummary(adminToken.value);
  } catch (err) {
    adminError.value = err.message || "读取 API 统计失败";
    adminSummary.value = null;
    if (String(adminError.value).toLowerCase().includes("token")) {
      logoutAdmin();
    }
  } finally {
    adminLoading.value = false;
  }
}

function logoutAdmin() {
  adminToken.value = "";
  adminSummary.value = null;
  clearAdminToken();
}

function buildExamplePayload() {
  return {
    input: apiExample.value.input,
    caller: apiExample.value.caller,
    task_type: apiExample.value.taskType,
    metadata: {
      line: apiExample.value.line,
      station: apiExample.value.station,
    },
  };
}

async function copyText(target, text) {
  await navigator.clipboard.writeText(text);
  copiedTarget.value = target;
  window.setTimeout(() => {
    if (copiedTarget.value === target) {
      copiedTarget.value = "";
    }
  }, 1600);
}

function escapePowerShellString(value) {
  return String(value).replaceAll("`", "``").replaceAll('"', '`"');
}
</script>

<template>
  <main class="app-shell" :class="{ 'admin-shell': activeView === 'admin' }">
    <header class="topbar">
      <div>
        <h1>Factory AI Platform</h1>
        <p>本地 Qwen 工厂 AI 服务</p>
      </div>
      <div class="topbar-actions">
        <nav class="view-tabs" aria-label="页面">
          <button
            type="button"
            :class="{ active: activeView === 'chat' }"
            @click="activeView = 'chat'"
          >
            聊天
          </button>
          <button
            type="button"
            :class="{ active: activeView === 'admin' }"
            @click="activeView = 'admin'"
          >
            API 管理
          </button>
        </nav>
        <span class="service-pill">vLLM: localhost:8000</span>
        <button
          v-if="activeView === 'chat'"
          class="clear-button"
          type="button"
          :disabled="loading || !canClear"
          @click="clearConversation"
        >
          清空会话
        </button>
      </div>
    </header>

    <template v-if="activeView === 'chat'">
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
    </template>

    <section v-else class="admin-page">
      <form v-if="!isAdminLoggedIn" class="login-panel" @submit.prevent="submitAdminLogin">
        <div>
          <h2>管理员登录</h2>
          <p>输入管理员密码后查看 API 状态、调用统计和接入示例。</p>
        </div>
        <label>
          管理员密码
          <input
            v-model="adminPassword"
            type="password"
            autocomplete="current-password"
            placeholder="ADMIN_PASSWORD"
            :disabled="adminLoading"
          />
        </label>
        <p v-if="adminError" class="error">{{ adminError }}</p>
        <button type="submit" :disabled="adminLoading || !adminPassword.trim()">
          {{ adminLoading ? "登录中" : "登录" }}
        </button>
      </form>

      <div v-else class="admin-dashboard">
        <section class="admin-toolbar">
          <div>
            <h2>API 管理</h2>
            <p>当前会话已登录，管理 token 保存在浏览器 sessionStorage。</p>
          </div>
          <div class="toolbar-buttons">
            <button type="button" @click="loadAdminSummary" :disabled="adminLoading">
              {{ adminLoading ? "刷新中" : "刷新" }}
            </button>
            <button type="button" class="secondary-button" @click="logoutAdmin">
              退出
            </button>
          </div>
        </section>

        <p v-if="adminError" class="error">{{ adminError }}</p>

        <section v-if="adminSummary" class="stats-grid">
          <article class="stat-panel">
            <span>API 状态</span>
            <strong>{{ adminSummary.health.status }}</strong>
            <small>{{ adminSummary.health.model }}</small>
          </article>
          <article class="stat-panel">
            <span>总调用</span>
            <strong>{{ adminSummary.summary.total_calls }}</strong>
            <small>平均 {{ adminSummary.summary.avg_duration_ms }} ms</small>
          </article>
          <article class="stat-panel">
            <span>成功 / 失败</span>
            <strong>{{ adminSummary.summary.ok_calls }} / {{ adminSummary.summary.error_calls }}</strong>
            <small>来自 JSONL 日志</small>
          </article>
          <article class="stat-panel">
            <span>限流</span>
            <strong>{{ adminSummary.rate_limit.requests }}</strong>
            <small>每 {{ adminSummary.rate_limit.window_seconds }} 秒 / token</small>
          </article>
        </section>

        <section v-if="adminSummary" class="admin-columns">
          <article class="admin-section">
            <h3>调用方统计</h3>
            <table>
              <thead>
                <tr>
                  <th>caller</th>
                  <th>total</th>
                  <th>ok</th>
                  <th>error</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(stats, caller) in adminSummary.summary.by_caller" :key="caller">
                  <td>{{ caller }}</td>
                  <td>{{ stats.total }}</td>
                  <td>{{ stats.ok }}</td>
                  <td>{{ stats.error }}</td>
                </tr>
              </tbody>
            </table>
          </article>

          <article class="admin-section">
            <h3>错误码统计</h3>
            <table>
              <thead>
                <tr>
                  <th>error_code</th>
                  <th>count</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(count, code) in adminSummary.summary.by_error_code" :key="code">
                  <td>{{ code }}</td>
                  <td>{{ count }}</td>
                </tr>
                <tr v-if="Object.keys(adminSummary.summary.by_error_code).length === 0">
                  <td colspan="2">暂无错误</td>
                </tr>
              </tbody>
            </table>
          </article>
        </section>

        <section class="admin-section integration-section">
          <h3>接入示例生成</h3>
          <div class="form-grid">
            <label>
              API token
              <input v-model="apiExample.apiToken" />
            </label>
            <label>
              caller
              <input v-model="apiExample.caller" />
            </label>
            <label>
              task_type
              <input v-model="apiExample.taskType" />
            </label>
            <label>
              line
              <input v-model="apiExample.line" />
            </label>
            <label>
              station
              <input v-model="apiExample.station" />
            </label>
            <label>
              input
              <textarea v-model="apiExample.input"></textarea>
            </label>
          </div>

          <div class="code-grid">
            <article>
              <div class="code-header">
                <h4>curl</h4>
                <button type="button" @click="copyText('curl', curlExample)">
                  {{ copiedTarget === "curl" ? "已复制" : "复制" }}
                </button>
              </div>
              <pre><code>{{ curlExample }}</code></pre>
            </article>
            <article>
              <div class="code-header">
                <h4>PowerShell</h4>
                <button type="button" @click="copyText('powershell', powershellExample)">
                  {{ copiedTarget === "powershell" ? "已复制" : "复制" }}
                </button>
              </div>
              <pre><code>{{ powershellExample }}</code></pre>
            </article>
          </div>
        </section>
      </div>
    </section>
  </main>
</template>
