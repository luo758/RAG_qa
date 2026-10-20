<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ShieldCheck, UserCog, Users } from '@lucide/vue'
import { ElMessage } from 'element-plus'
import { api, errorMessage } from '../api/client'
import { useAuthStore } from '../stores/auth'
import type { AdminUser } from '../types'

const auth = useAuthStore()
const users = ref<AdminUser[]>([])
const loading = ref(true)
const savingId = ref<number | null>(null)
const isSuperAdmin = computed(() => auth.user?.role === 'super_admin')

const roleLabels: Record<string, string> = {
  super_admin: '超级管理员',
  admin: '管理员',
  employee: '员工',
}

async function load() {
  loading.value = true
  try {
    const { data } = await api.get<AdminUser[]>('/admin/users')
    users.value = data
  } catch (err) {
    ElMessage.error(errorMessage(err))
  } finally {
    loading.value = false
  }
}

async function changeRole(user: AdminUser, role: string) {
  savingId.value = user.id
  try {
    const { data } = await api.patch<AdminUser>(`/admin/users/${user.id}/role`, { role })
    Object.assign(user, data)
    ElMessage.success(`${user.username} 已设为${roleLabels[data.role]}`)
  } catch (err) {
    ElMessage.error(errorMessage(err))
    await load()
  } finally {
    savingId.value = null
  }
}

onMounted(load)
</script>

<template>
  <div class="page-shell content-page">
    <header class="page-header">
      <div>
        <span class="page-kicker">组织治理</span>
        <h1>用户与权限</h1>
        <p>超级管理员设置管理员；管理员进入具体知识库配置员工的查看和上传权限。</p>
      </div>
    </header>

    <section class="governance-banner">
      <ShieldCheck :size="24" />
      <div>
        <strong>最小权限模型</strong>
        <span>员工默认看不到知识库。查看与上传是两个独立权限，管理员始终不能通过上传权限获得修改既有内容的能力。</span>
      </div>
    </section>

    <section class="user-panel">
      <div class="section-title"><h2>账号列表</h2><span>{{ users.length }} 个账号</span></div>
      <div v-if="loading" class="skeleton-list"><i></i><i></i><i></i></div>
      <div v-else class="user-list">
        <article v-for="user in users" :key="user.id" class="user-row">
          <div class="user-symbol"><Users :size="18" /></div>
          <div class="user-identity">
            <strong>{{ user.username }}</strong>
            <span>ID {{ user.id }} · {{ user.is_active ? '正常' : '停用' }}</span>
          </div>
          <span class="role-pill" :class="user.role">{{ roleLabels[user.role] || user.role }}</span>
          <div v-if="isSuperAdmin && user.role !== 'super_admin'" class="role-control">
            <UserCog :size="15" />
            <el-select
              :model-value="user.role"
              :loading="savingId === user.id"
              @change="(value: string) => changeRole(user, value)"
            >
              <el-option label="管理员" value="admin" />
              <el-option label="员工" value="employee" />
            </el-select>
          </div>
          <span v-else class="role-lock">{{ isSuperAdmin ? '固定角色' : '由超级管理员维护' }}</span>
        </article>
      </div>
    </section>
  </div>
</template>
