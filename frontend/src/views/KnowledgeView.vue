<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { BookOpen, ChevronRight, Plus, Trash2 } from '@lucide/vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api, errorMessage } from '../api/client'
import { useAuthStore } from '../stores/auth'
import type { KnowledgeBase } from '../types'

const router = useRouter()
const auth = useAuthStore()
const items = ref<KnowledgeBase[]>([])
const loading = ref(true)
const dialogVisible = ref(false)
const creating = ref(false)
const form = reactive({ name: '', description: '' })
const canCreate = computed(() => auth.user?.role === 'admin' || auth.user?.role === 'super_admin')

async function load() {
  loading.value = true
  try {
    const { data } = await api.get<KnowledgeBase[]>('/knowledge-bases')
    items.value = data
  } catch (err) {
    ElMessage.error(errorMessage(err))
  } finally {
    loading.value = false
  }
}

async function create() {
  if (!form.name.trim()) return
  creating.value = true
  try {
    await api.post('/knowledge-bases', { name: form.name.trim(), description: form.description.trim() })
    dialogVisible.value = false
    form.name = ''
    form.description = ''
    await load()
  } catch (err) {
    ElMessage.error(errorMessage(err))
  } finally {
    creating.value = false
  }
}

async function remove(item: KnowledgeBase) {
  try {
    await ElMessageBox.confirm(`删除知识库「${item.name}」及其全部文档？`, '删除知识库', { type: 'warning' })
    await api.delete(`/knowledge-bases/${item.id}`)
    items.value = items.value.filter((kb) => kb.id !== item.id)
  } catch {
    /* cancelled */
  }
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }).format(new Date(value))
}

onMounted(load)
</script>

<template>
  <div class="page-shell content-page">
    <header class="page-header">
      <div>
        <span class="page-kicker">知识库</span>
        <h1>知识库管理</h1>
        <p>将不同技术主题拆分成独立知识库，控制每次问答的检索范围。</p>
      </div>
      <el-button v-if="canCreate" type="primary" size="large" @click="dialogVisible = true"><Plus :size="17" /> 新建知识库</el-button>
    </header>

    <div v-if="loading" class="knowledge-grid"><i v-for="n in 3" :key="n" class="knowledge-skeleton"></i></div>
    <div v-else-if="items.length" class="knowledge-grid">
      <article v-for="item in items" :key="item.id" class="knowledge-card" @click="router.push(`/knowledge/${item.id}`)">
        <div class="knowledge-icon"><BookOpen :size="22" /></div>
        <div class="knowledge-card-head">
          <span class="page-kicker">{{ item.can_manage ? '可管理' : item.can_upload ? '可上传' : '只读' }}</span>
          <button v-if="item.can_manage" class="icon-button danger" title="删除知识库" @click.stop="remove(item)"><Trash2 :size="16" /></button>
        </div>
        <h2>{{ item.name }}</h2>
        <p>{{ item.description || '暂无描述' }}</p>
        <footer><span>更新于 {{ formatDate(item.updated_at) }}</span><ChevronRight :size="17" /></footer>
      </article>
    </div>
    <div v-else class="empty-state large">
      <BookOpen :size="30" />
      <h2>还没有知识库</h2>
      <p v-if="canCreate">先创建一个知识库，再上传 PDF、PPTX、Markdown 或图片文档。</p>
      <p v-else>暂无可访问的知识库，请联系管理员授权。</p>
      <el-button v-if="canCreate" type="primary" @click="dialogVisible = true">创建第一个知识库</el-button>
    </div>

    <el-dialog v-model="dialogVisible" title="新建知识库" width="460px">
      <div class="dialog-form">
        <label>名称</label>
        <el-input v-model="form.name" maxlength="128" placeholder="例如：API 文档库" />
        <label>描述</label>
        <el-input v-model="form.description" type="textarea" :rows="3" maxlength="2000" placeholder="说明知识库包含哪些技术内容" />
      </div>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="create">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>
