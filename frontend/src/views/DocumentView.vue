<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Edit3, FileText, RefreshCw, Trash2 } from '@lucide/vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api, errorMessage } from '../api/client'
import type { Chunk, DocumentDetail } from '../types'

const route = useRoute()
const router = useRouter()
const documentId = computed(() => Number(route.params.id))
const detail = ref<DocumentDetail | null>(null)
const loading = ref(true)
const editVisible = ref(false)
const editing = ref<Chunk | null>(null)
const editContent = ref('')
const saving = ref(false)

async function load() {
  loading.value = true
  try {
    const { data } = await api.get<DocumentDetail>(`/documents/${documentId.value}`)
    detail.value = data
  } catch (err) {
    ElMessage.error(errorMessage(err))
  } finally {
    loading.value = false
  }
}

function openEdit(chunk: Chunk) {
  editing.value = chunk
  editContent.value = chunk.content
  editVisible.value = true
}

async function saveChunk() {
  if (!editing.value || !editContent.value.trim()) return
  saving.value = true
  try {
    const { data } = await api.patch<Chunk>(`/chunks/${editing.value.id}`, { content: editContent.value })
    const index = detail.value?.chunks.findIndex((item) => item.id === data.id) ?? -1
    if (detail.value && index >= 0) detail.value.chunks[index] = data
    editVisible.value = false
    ElMessage.success('文档块已更新并重新向量化')
  } catch (err) {
    ElMessage.error(errorMessage(err))
  } finally {
    saving.value = false
  }
}

async function removeChunk(chunk: Chunk) {
  try {
    await ElMessageBox.confirm('删除后该文档块将不再参与检索，确认继续？', '删除文档块', { type: 'warning' })
    await api.delete(`/chunks/${chunk.id}`)
    if (detail.value) detail.value.chunks = detail.value.chunks.filter((item) => item.id !== chunk.id)
  } catch {
    /* cancelled */
  }
}

onMounted(load)
</script>

<template>
  <div class="page-shell content-page">
    <button class="back-button" @click="router.back()"><ArrowLeft :size="16" /> 返回</button>
    <header class="page-header compact-header">
      <div>
        <span class="page-kicker">文档预览</span>
        <h1>{{ detail?.filename || '文档详情' }}</h1>
        <p v-if="detail">{{ detail.file_type.toUpperCase() }} · {{ detail.chunks.length }} 个文档块 · {{ detail.char_count.toLocaleString() }} 字符</p>
      </div>
      <button class="icon-button" title="刷新" @click="load"><RefreshCw :size="18" /></button>
    </header>

    <div v-if="loading" class="skeleton-list"><i></i><i></i><i></i></div>
    <div v-else-if="detail?.chunks.length" class="chunk-list">
      <article v-for="chunk in detail.chunks" :key="chunk.id" class="chunk-card">
        <header>
          <span>文档块 {{ String(chunk.chunk_index + 1).padStart(2, '0') }}</span>
          <div v-if="detail?.can_manage">
            <button class="icon-button" title="编辑文档块" @click="openEdit(chunk)"><Edit3 :size="15" /></button>
            <button class="icon-button danger" title="删除文档块" @click="removeChunk(chunk)"><Trash2 :size="15" /></button>
          </div>
        </header>
        <pre>{{ chunk.content }}</pre>
        <footer>文档块 ID {{ chunk.id }} · 更新于 {{ new Date(chunk.updated_at).toLocaleString('zh-CN') }}</footer>
      </article>
    </div>
    <div v-else class="empty-state"><FileText :size="26" /><h3>没有文档块</h3><p>该文档可能还在处理中或解析失败。</p></div>

    <el-dialog v-model="editVisible" title="编辑文档块" width="720px">
      <el-input v-model="editContent" type="textarea" :rows="16" />
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveChunk">保存并重新向量化</el-button>
      </template>
    </el-dialog>
  </div>
</template>
