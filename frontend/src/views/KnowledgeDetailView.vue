<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Edit3, FileText, RefreshCw, Trash2, UploadCloud, Users } from '@lucide/vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api, errorMessage } from '../api/client'
import type { DocumentItem, KnowledgeBase, KnowledgePermission } from '../types'

const route = useRoute()
const router = useRouter()
const kbId = computed(() => Number(route.params.id))
const kb = ref<KnowledgeBase | null>(null)
const documents = ref<DocumentItem[]>([])
const permissions = ref<KnowledgePermission[]>([])
const loading = ref(true)
const uploading = ref(false)
const savingPermission = ref<number | null>(null)
const editVisible = ref(false)
const editSaving = ref(false)
const file = ref<File | null>(null)
const form = reactive({ chunk_size: 800, overlap: 100, retrieval_mode: 'hybrid' })
const editForm = reactive({ name: '', description: '' })

async function loadPermissions() {
  if (!kb.value?.can_manage) return
  const { data } = await api.get<KnowledgePermission[]>(`/knowledge-bases/${kbId.value}/permissions`)
  permissions.value = data
}

async function load() {
  loading.value = true
  try {
    const [kbResponse, docResponse] = await Promise.all([
      api.get<KnowledgeBase>(`/knowledge-bases/${kbId.value}`),
      api.get<DocumentItem[]>(`/knowledge-bases/${kbId.value}/documents`),
    ])
    kb.value = kbResponse.data
    documents.value = docResponse.data
    await loadPermissions()
  } catch (err) {
    ElMessage.error(errorMessage(err))
  } finally {
    loading.value = false
  }
}

function chooseFile(event: Event) {
  const input = event.target as HTMLInputElement
  file.value = input.files?.[0] || null
}

async function upload() {
  if (!file.value) {
    ElMessage.warning('请先选择文件')
    return
  }
  uploading.value = true
  try {
    const body = new FormData()
    body.append('file', file.value)
    body.append('chunk_size', String(form.chunk_size))
    body.append('overlap', String(form.overlap))
    body.append('retrieval_mode', form.retrieval_mode)
    await api.post(`/knowledge-bases/${kbId.value}/documents`, body, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 180000,
    })
    ElMessage.success('文档解析完成')
    file.value = null
    await load()
  } catch (err) {
    ElMessage.error(errorMessage(err))
  } finally {
    uploading.value = false
  }
}

async function removeDocument(document: DocumentItem) {
  try {
    await ElMessageBox.confirm(`删除文档「${document.filename}」？`, '删除文档', { type: 'warning' })
    await api.delete(`/documents/${document.id}`)
    documents.value = documents.value.filter((item) => item.id !== document.id)
  } catch {
    /* cancelled */
  }
}

function openEdit() {
  if (!kb.value) return
  editForm.name = kb.value.name
  editForm.description = kb.value.description
  editVisible.value = true
}

async function saveKnowledgeBase() {
  if (!editForm.name.trim()) return
  editSaving.value = true
  try {
    const { data } = await api.patch<KnowledgeBase>(`/knowledge-bases/${kbId.value}`, {
      name: editForm.name.trim(),
      description: editForm.description.trim(),
    })
    kb.value = data
    editVisible.value = false
    ElMessage.success('知识库信息已更新')
  } catch (err) {
    ElMessage.error(errorMessage(err))
  } finally {
    editSaving.value = false
  }
}

async function savePermission(row: KnowledgePermission) {
  if (!row.can_view) row.can_upload = false
  if (row.can_upload) row.can_view = true
  savingPermission.value = row.user_id
  try {
    const { data } = await api.put<KnowledgePermission>(
      `/knowledge-bases/${kbId.value}/permissions/${row.user_id}`,
      { can_view: row.can_view, can_upload: row.can_upload },
    )
    Object.assign(row, data)
    ElMessage.success(`已更新 ${row.username} 的权限`)
  } catch (err) {
    ElMessage.error(errorMessage(err))
    await loadPermissions()
  } finally {
    savingPermission.value = null
  }
}

function statusLabel(status: string) {
  return { ready: '已解析', processing: '处理中', failed: '失败' }[status] || status
}

onMounted(load)
</script>

<template>
  <div class="page-shell content-page">
    <button class="back-button" @click="router.push('/knowledge')"><ArrowLeft :size="16" /> 返回知识库</button>
    <header class="page-header compact-header">
      <div>
        <span class="page-kicker">{{ kb?.can_manage ? '知识库运营' : '文档访问' }}</span>
        <h1>{{ kb?.name || '知识库' }}</h1>
        <p>{{ kb?.description || '上传并解析技术文档' }}</p>
      </div>
      <div class="header-actions">
        <el-button v-if="kb?.can_manage" @click="openEdit"><Edit3 :size="16" /> 编辑信息</el-button>
        <button class="icon-button" title="刷新" @click="load"><RefreshCw :size="18" /></button>
      </div>
    </header>

    <section v-if="kb?.can_upload" class="upload-panel">
      <div class="upload-copy">
        <UploadCloud :size="26" />
        <div>
          <h2>上传文档</h2>
          <p>支持 PDF、PPTX、Markdown、TXT、PNG、JPG。单文件最大 30 MB。</p>
        </div>
      </div>
      <div class="upload-controls">
        <label class="file-picker">
          <input type="file" accept=".pdf,.pptx,.md,.markdown,.txt,.png,.jpg,.jpeg,.webp,.bmp" @change="chooseFile" />
          <FileText :size="17" />
          <span>{{ file?.name || '选择文件' }}</span>
        </label>
        <div class="parse-field"><span>切块大小</span><el-input-number v-model="form.chunk_size" :min="100" :max="5000" :step="100" controls-position="right" /></div>
        <div class="parse-field"><span>重叠大小</span><el-input-number v-model="form.overlap" :min="0" :max="1000" :step="20" controls-position="right" /></div>
        <div class="parse-field"><span>检索模式</span><el-select v-model="form.retrieval_mode"><el-option label="混合检索" value="hybrid" /><el-option label="稠密向量" value="dense" /></el-select></div>
        <el-button type="primary" :loading="uploading" @click="upload"><UploadCloud :size="16" /> 开始解析</el-button>
      </div>
    </section>
    <div v-else class="shared-notice">
      <strong>只读权限</strong>
      <span>你可以检索和查看该知识库。上传、编辑和删除由管理员操作。</span>
    </div>

    <section v-if="kb?.can_manage" class="permission-panel">
      <div class="section-title">
        <div>
          <h2>员工权限</h2>
          <p>员工默认不可见。开启查看后可检索；开启上传后仍不能修改或删除已有内容。</p>
        </div>
        <Users :size="20" />
      </div>
      <div v-if="permissions.length" class="permission-list">
        <article v-for="row in permissions" :key="row.user_id" class="permission-row">
          <div class="permission-user">
            <strong>{{ row.username }}</strong>
            <span>员工账号</span>
          </div>
          <label class="permission-switch">
            <span>查看</span>
            <el-switch v-model="row.can_view" :loading="savingPermission === row.user_id" @change="savePermission(row)" />
          </label>
          <label class="permission-switch">
            <span>上传</span>
            <el-switch v-model="row.can_upload" :loading="savingPermission === row.user_id" @change="savePermission(row)" />
          </label>
        </article>
      </div>
      <div v-else class="empty-inline">暂无员工账号，员工注册后会出现在这里。</div>
    </section>

    <section class="document-section">
      <div class="section-title"><h2>文档列表</h2><span>{{ documents.length }} 个文档</span></div>
      <div v-if="loading" class="skeleton-list"><i></i><i></i></div>
      <div v-else-if="documents.length" class="document-list">
        <article v-for="document in documents" :key="document.id" class="document-row">
          <div class="doc-icon"><FileText :size="20" /></div>
          <button class="doc-main" @click="router.push(`/documents/${document.id}`)">
            <strong>{{ document.filename }}</strong>
            <span>{{ document.file_type.toUpperCase() }} · {{ document.retrieval_mode }} · {{ document.chunk_size }} 字符切块</span>
          </button>
          <span class="status-pill" :class="document.status">{{ statusLabel(document.status) }}</span>
          <span class="doc-count">{{ document.char_count.toLocaleString() }} 字符</span>
          <button v-if="document.can_manage" class="icon-button danger" title="删除文档" @click="removeDocument(document)"><Trash2 :size="16" /></button>
        </article>
      </div>
      <div v-else class="empty-state"><FileText :size="25" /><h3>暂无文档</h3><p>选择一个技术文档开始解析。</p></div>
    </section>

    <el-dialog v-model="editVisible" title="编辑知识库" width="480px">
      <div class="dialog-form">
        <label>名称</label>
        <el-input v-model="editForm.name" maxlength="128" />
        <label>描述</label>
        <el-input v-model="editForm.description" type="textarea" :rows="3" maxlength="2000" />
      </div>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="editSaving" @click="saveKnowledgeBase">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>
