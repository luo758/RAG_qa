<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { BookOpen, LogOut, Menu, MessageSquare, Sparkles, Users, X } from '@lucide/vue'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const menuOpen = ref(false)

const displayName = computed(() => auth.user?.username || '用户')
const initial = computed(() => displayName.value.slice(0, 1).toUpperCase())
const isManager = computed(() => auth.user?.role === 'admin' || auth.user?.role === 'super_admin')
const roleLabel = computed(() => ({
  super_admin: '超级管理员',
  admin: '管理员',
  employee: '员工',
}[auth.user?.role || 'employee']))

onMounted(async () => {
  try {
    await auth.fetchMe()
  } catch {
    auth.logout()
    router.push('/login')
  }
})

function logout() {
  auth.logout()
  router.push('/login')
}

function isActive(prefix: string) {
  return route.path.startsWith(prefix)
}
</script>

<template>
  <div class="app-shell">
    <aside class="app-sidebar" :class="{ 'is-open': menuOpen }">
      <div class="brand-block">
        <div class="brand-mark"><Sparkles :size="20" /></div>
        <div>
          <strong>DocFlow</strong>
          <span>智文通</span>
        </div>
      </div>

      <nav class="nav-list">
        <RouterLink class="nav-item" :class="{ active: isActive('/chat') }" to="/chat" @click="menuOpen = false">
          <MessageSquare :size="18" />
          <span>智能问答</span>
        </RouterLink>
        <RouterLink class="nav-item" :class="{ active: isActive('/knowledge') }" to="/knowledge" @click="menuOpen = false">
          <BookOpen :size="18" />
          <span>知识库</span>
        </RouterLink>
        <RouterLink v-if="isManager" class="nav-item" :class="{ active: isActive('/admin/users') }" to="/admin/users" @click="menuOpen = false">
          <Users :size="18" />
          <span>用户与权限</span>
        </RouterLink>
      </nav>

      <div class="sidebar-note">
        <span class="status-dot"></span>
        <div>
          <strong>生产环境</strong>
          <p>MySQL · Milvus · Redis · BGE-M3</p>
        </div>
      </div>

      <div class="sidebar-user">
        <div class="avatar">{{ initial }}</div>
        <div class="user-meta">
          <strong>{{ displayName }}</strong>
          <span>{{ roleLabel }}</span>
        </div>
        <button class="icon-button" title="退出登录" @click="logout">
          <LogOut :size="17" />
        </button>
      </div>
    </aside>

    <button class="mobile-menu-button" @click="menuOpen = !menuOpen">
      <X v-if="menuOpen" :size="20" />
      <Menu v-else :size="20" />
    </button>

    <main class="app-main" :class="{ 'app-main-chat': route.path.startsWith('/chat') }">
      <RouterView />
    </main>
  </div>
</template>
