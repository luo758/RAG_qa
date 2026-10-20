<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Bot, Check, Edit3, Plus, Send, Settings2, Sparkles, Trash2, User } from '@lucide/vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api, errorMessage } from '../api/client'
import { useAuthStore } from '../stores/auth'
import type { ChatMessage, ChatSession, KnowledgeBase } from '../types'

const router = useRouter()
const auth = useAuthStore()
const kbs = ref<KnowledgeBase[]>([])
const sessions = ref<ChatSession[]>([])
const messages = ref<ChatMessage[]>([])
const selectedKbs = ref<number[]>([])
const currentSession = ref<ChatSession | null>(null)
const question = ref('')
const sending = ref(false)
const loading = ref(true)
const messageList = ref<HTMLElement | null>(null)
const settings = reactive({
  model: 'qwen-max',
  temperature: 0.2,
  top_p: 0.8,
  max_tokens: 2048,
  history_turns: 5,
})

const currentTitle = computed(() => currentSession.value?.title || '新对话')
const canManageKnowledge = computed(() => auth.user?.role === 'admin' || auth.user?.role === 'super_admin')

async function loadKnowledgeBases() {
  const { data } = await api.get<KnowledgeBase[]>('/knowledge-bases')
  kbs.value = data
  if (!selectedKbs.value.length) selectedKbs.value = data.slice(0, 1).map((item) => item.id)
}

async function loadSessions(selectFirst = false) {
  const { data } = await api.get<ChatSession[]>('/sessions')
  sessions.value = data
  if ((selectFirst || !currentSession.value) && data.length) {
    await selectSession(data[0])
  }
}

async function selectSession(session: ChatSession) {
  currentSession.value = session
  settings.model = session.model
  settings.temperature = session.temperature
  settings.top_p = session.top_p
  settings.max_tokens = session.max_tokens
  settings.history_turns = session.history_turns
  const { data } = await api.get<ChatMessage[]>(`/sessions/${session.id}/messages`)
  messages.value = data
  await scrollToBottom()
}

async function createSession() {
  let title = '新对话'
  try {
    const result = await ElMessageBox.prompt('输入会话名称', '新建对话', {
      inputValue: '新对话',
      confirmButtonText: '创建',
      cancelButtonText: '取消',
      inputValidator: (value) => Boolean(value?.trim()) || '名称不能为空',
    })
    title = result.value.trim()
  } catch {
    return
  }
  const { data } = await api.post<ChatSession>('/sessions', {
    title,
    model: settings.model,
    temperature: settings.temperature,
    top_p: settings.top_p,
    max_tokens: settings.max_tokens,
    history_turns: settings.history_turns,
  })
  sessions.value.unshift(data)
  currentSession.value = data
  messages.value = []
}

async function renameSession(session: ChatSession) {
  try {
    const result = await ElMessageBox.prompt('输入新的会话名称', '重命名会话', {
      inputValue: session.title,
      confirmButtonText: '保存',
      cancelButtonText: '取消',
      inputValidator: (value) => Boolean(value?.trim()) || '名称不能为空',
    })
    const { data } = await api.patch<ChatSession>(`/sessions/${session.id}`, { title: result.value.trim() })
    Object.assign(session, data)
    if (currentSession.value?.id === session.id) currentSession.value = data
  } catch {
    /* cancelled */
  }
}

async function deleteSession(session: ChatSession) {
  try {
    await ElMessageBox.confirm(`确认删除会话「${session.title}」？`, '删除会话', { type: 'warning' })
    await api.delete(`/sessions/${session.id}`)
    sessions.value = sessions.value.filter((item) => item.id !== session.id)
    if (currentSession.value?.id === session.id) {
      currentSession.value = null
      messages.value = []
      if (sessions.value.length) await selectSession(sessions.value[0])
    }
  } catch {
    /* cancelled */
  }
}

async function applySettings() {
  if (!currentSession.value) return
  const { data } = await api.patch<ChatSession>(`/sessions/${currentSession.value.id}`, settings)
  currentSession.value = data
  ElMessage.success('推理参数已应用')
}

function parseEvent(block: string): { event: string; data: any } | null {
  const lines = block.split('\n')
  let event = 'message'
  const dataLines: string[] = []
  for (const line of lines) {
    if (line.startsWith('event:')) event = line.slice(6).trim()
    if (line.startsWith('data:')) dataLines.push(line.slice(5).trim())
  }
  if (!dataLines.length) return null
  try {
    return { event, data: JSON.parse(dataLines.join('\n')) }
  } catch {
    return null
  }
}

async function ask() {
  const text = question.value.trim()
  if (!text || sending.value) return
  if (!currentSession.value) {
    await createSession()
    if (!currentSession.value) return
  }
  if (!selectedKbs.value.length) {
    ElMessage.warning('请至少选择一个知识库')
    return
  }

  sending.value = true
  question.value = ''
  messages.value.push({
    id: Date.now(),
    role: 'user',
    content: text,
    citations: [],
    created_at: new Date().toISOString(),
  })
  const assistant: ChatMessage = {
    id: Date.now() + 1,
    role: 'assistant',
    content: '',
    citations: [],
    created_at: new Date().toISOString(),
  }
  messages.value.push(assistant)
  await scrollToBottom()

  try {
    const response = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${localStorage.getItem('docflow_token') || ''}`,
      },
      body: JSON.stringify({
        session_id: currentSession.value.id,
        question: text,
        knowledge_base_ids: selectedKbs.value,
        model: settings.model,
        temperature: settings.temperature,
        top_p: settings.top_p,
        max_tokens: settings.max_tokens,
        history_turns: settings.history_turns,
      }),
    })
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}))
      throw new Error(payload.detail || '问答请求失败')
    }
    const reader = response.body?.getReader()
    if (!reader) throw new Error('浏览器不支持流式响应')
    const decoder = new TextDecoder()
    let buffer = ''
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const blocks = buffer.split('\n\n')
      buffer = blocks.pop() || ''
      for (const block of blocks) {
        const parsed = parseEvent(block)
        if (!parsed) continue
        if (parsed.event === 'meta') {
          assistant.citations = parsed.data.citations || []
        } else if (parsed.event === 'token') {
          assistant.content += parsed.data.text || ''
          await scrollToBottom()
        } else if (parsed.event === 'error') {
          assistant.content += `\n\n[错误] ${parsed.data.message}`
        }
      }
    }
    if (!assistant.content) assistant.content = '当前知识库中没有足够信息。'
    await loadSessions()
  } catch (err) {
    assistant.content = `回答失败：${errorMessage(err)}`
  } finally {
    sending.value = false
    await scrollToBottom()
  }
}

async function scrollToBottom() {
  await nextTick()
  if (messageList.value) messageList.value.scrollTop = messageList.value.scrollHeight
}

onMounted(async () => {
  try {
    await Promise.all([loadKnowledgeBases(), loadSessions(true)])
  } catch (err) {
    ElMessage.error(errorMessage(err))
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="page-shell chat-page">
    <aside class="session-pane">
      <div class="pane-heading">
        <div>
          <span class="page-kicker">会话记录</span>
          <h2>对话</h2>
        </div>
        <button class="icon-button accent" title="新建对话" @click="createSession"><Plus :size="18" /></button>
      </div>

      <div v-if="loading" class="skeleton-list"><i></i><i></i><i></i></div>
      <div v-else-if="sessions.length" class="session-list">
        <button
          v-for="session in sessions"
          :key="session.id"
          class="session-item"
          :class="{ active: currentSession?.id === session.id }"
          @click="selectSession(session)"
        >
          <span class="session-title">{{ session.title }}</span>
          <span class="session-actions">
            <i title="重命名" @click.stop="renameSession(session)"><Edit3 :size="14" /></i>
            <i title="删除" @click.stop="deleteSession(session)"><Trash2 :size="14" /></i>
          </span>
        </button>
      </div>
      <div v-else class="empty-mini">还没有对话</div>
    </aside>

    <section class="conversation-pane">
      <header class="conversation-head">
        <div>
          <span class="page-kicker">知识问答</span>
          <h1>{{ currentTitle }}</h1>
        </div>
        <el-select v-model="selectedKbs" multiple collapse-tags :max-collapse-tags="2" placeholder="选择知识库" class="kb-select">
          <el-option v-for="kb in kbs" :key="kb.id" :label="kb.name" :value="kb.id" />
        </el-select>
      </header>

      <div v-if="!kbs.length" class="empty-state large">
        <Sparkles :size="28" />
        <h3>{{ canManageKnowledge ? '先创建一个知识库' : '等待管理员授权' }}</h3>
        <p>{{ canManageKnowledge ? '上传技术文档后，才能开始基于内容的问答。' : '当前账号还没有可访问的知识库。' }}</p>
        <el-button type="primary" @click="router.push('/knowledge')">前往知识库</el-button>
      </div>

      <div ref="messageList" v-else class="message-list">
        <div v-if="!messages.length" class="welcome-block">
          <div class="welcome-icon"><Sparkles :size="26" /></div>
          <h2>向技术文档提问</h2>
          <p>选择知识库后，可以询问 API 用法、错误码、版本兼容性和故障排查步骤。</p>
          <div class="prompt-grid">
            <button @click="question = '企业版最多可以同时执行几个渲染任务？'">企业版最多可以同时执行几个渲染任务？</button>
            <button @click="question = 'access_token 过期后应该怎么处理？'">access_token 过期后应该怎么处理？</button>
            <button @click="question = '渲染任务一直 queued 有哪些原因？'">渲染任务一直 queued 有哪些原因？</button>
          </div>
        </div>

        <article v-for="message in messages" :key="message.id" class="message-row" :class="message.role">
          <div class="message-avatar">
            <User v-if="message.role === 'user'" :size="17" />
            <Bot v-else :size="17" />
          </div>
          <div class="message-content">
            <div class="message-meta">{{ message.role === 'user' ? '你' : 'DocFlow' }}</div>
            <div class="message-bubble">{{ message.content || (sending ? '正在检索文档…' : '') }}</div>
            <details v-if="message.citations?.length" class="citation-box">
              <summary>{{ message.citations.length }} 条文档引用</summary>
              <a
                v-for="citation in message.citations"
                :key="citation.chunk_id"
                class="citation-item"
                href="#"
                @click.prevent="router.push(`/documents/${citation.document_id}`)"
              >
                <span>[{{ citation.index }}] {{ citation.document_name }}</span>
                <small>{{ citation.snippet }}</small>
              </a>
            </details>
          </div>
        </article>
      </div>

      <footer class="composer">
        <textarea
          v-model="question"
          rows="2"
          placeholder="输入技术问题，Enter 发送，Shift + Enter 换行"
          @keydown.enter.exact.prevent="ask"
        ></textarea>
        <button class="send-button" :disabled="sending || !question.trim()" @click="ask">
          <Send :size="19" />
        </button>
      </footer>
    </section>

    <aside class="settings-pane">
      <div class="pane-heading compact">
        <div>
          <span class="page-kicker">推理设置</span>
          <h2>推理参数</h2>
        </div>
        <Settings2 :size="18" />
      </div>
      <label>模型</label>
      <el-select v-model="settings.model" class="full-width">
        <el-option label="Qwen Max · 高质量" value="qwen-max" />
        <el-option label="Qwen Plus · 均衡" value="qwen-plus" />
        <el-option label="Qwen Turbo · 低延迟" value="qwen-turbo" />
      </el-select>
      <div class="setting-line"><span>温度 <b>{{ settings.temperature }}</b></span><el-slider v-model="settings.temperature" :min="0" :max="2" :step="0.1" /></div>
      <div class="setting-line"><span>Top P <b>{{ settings.top_p }}</b></span><el-slider v-model="settings.top_p" :min="0" :max="1" :step="0.05" /></div>
      <label>最大输出 Token</label>
      <el-input-number v-model="settings.max_tokens" :min="64" :max="8192" :step="128" controls-position="right" class="full-width" />
      <label>历史对话轮数</label>
      <el-input-number v-model="settings.history_turns" :min="0" :max="20" controls-position="right" class="full-width" />
      <el-button class="settings-apply" @click="applySettings"><Check :size="15" /> 应用参数</el-button>
      <div class="settings-note">
        <strong>检索模式</strong>
        <span>知识库含混合检索文档时自动启用 Dense + BM25。</span>
      </div>
    </aside>
  </div>
</template>
