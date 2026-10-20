<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { RefreshCw, Sparkles } from '@lucide/vue'
import { ElMessage } from 'element-plus'
import { api, errorMessage } from '../api/client'
import { useAuthStore } from '../stores/auth'
import type { CaptchaResponse } from '../types'

const router = useRouter()
const auth = useAuthStore()
const captcha = ref<CaptchaResponse | null>(null)
const submitting = ref(false)
const error = ref('')
const form = reactive({ username: '', password: '', confirm_password: '', captcha_code: '' })

async function loadCaptcha() {
  const { data } = await api.get<CaptchaResponse>('/auth/captcha')
  captcha.value = data
  form.captcha_code = ''
  if (import.meta.env.DEV && data.debug_code) form.captcha_code = data.debug_code
}

async function submit() {
  error.value = ''
  if (form.password !== form.confirm_password) {
    error.value = '两次输入的密码不一致'
    return
  }
  if (!captcha.value) return
  submitting.value = true
  try {
    await auth.register({
      username: form.username,
      password: form.password,
      confirm_password: form.confirm_password,
      captcha_id: captcha.value.captcha_id,
      captcha_code: form.captcha_code,
    })
    ElMessage.success('账号创建成功')
    router.push('/chat')
  } catch (err) {
    error.value = errorMessage(err)
    await loadCaptcha()
  } finally {
    submitting.value = false
  }
}

onMounted(loadCaptcha)
</script>

<template>
  <div class="auth-shell">
    <section class="auth-story register-story">
      <div class="auth-brand"><Sparkles :size="22" /> DocFlow 智文通</div>
      <div class="auth-copy">
        <span class="eyebrow">团队访问</span>
        <h1>建立你的<br />技术知识空间</h1>
        <p>每个账号拥有独立知识库和会话历史。文档、向量与用户数据均由平台隔离管理。</p>
      </div>
      <div class="signal-card">
        <strong>知识接入标准流程</strong>
        <span>上传 → 解析 → 切块 → 向量化 → 检索</span>
      </div>
    </section>

    <section class="auth-panel">
      <div class="auth-form-wrap">
        <span class="page-kicker">创建账号</span>
        <h2>注册账号</h2>
        <p class="muted">用户名仅支持字母、数字和下划线</p>
        <form class="auth-form" @submit.prevent="submit">
          <label>账号</label>
          <el-input v-model="form.username" size="large" placeholder="3–32 位账号" autocomplete="username" />
          <label>密码</label>
          <el-input v-model="form.password" size="large" type="password" show-password placeholder="至少 8 位" autocomplete="new-password" />
          <label>确认密码</label>
          <el-input v-model="form.confirm_password" size="large" type="password" show-password placeholder="再次输入密码" autocomplete="new-password" />
          <label>图形验证码</label>
          <div class="captcha-row">
            <el-input v-model="form.captcha_code" size="large" maxlength="4" placeholder="输入图中字符" />
            <button class="captcha-image" type="button" title="刷新验证码" @click="loadCaptcha">
              <img v-if="captcha" :src="captcha.image_data" alt="图形验证码" />
              <RefreshCw :size="18" />
            </button>
          </div>
          <p v-if="error" class="form-error">{{ error }}</p>
          <el-button class="primary-action" type="primary" size="large" native-type="submit" :loading="submitting">注册并登录</el-button>
        </form>
        <p class="auth-switch">已有账号？<RouterLink to="/login">返回登录</RouterLink></p>
      </div>
    </section>
  </div>
</template>
