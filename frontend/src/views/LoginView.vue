<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { RefreshCw, ShieldCheck, Sparkles } from '@lucide/vue'
import { ElMessage } from 'element-plus'
import { api, errorMessage } from '../api/client'
import { useAuthStore } from '../stores/auth'
import type { CaptchaResponse } from '../types'

const router = useRouter()
const auth = useAuthStore()
const captcha = ref<CaptchaResponse | null>(null)
const submitting = ref(false)
const error = ref('')
const form = reactive({ username: '', password: '', captcha_code: '' })

async function loadCaptcha() {
  const { data } = await api.get<CaptchaResponse>('/auth/captcha')
  captcha.value = data
  form.captcha_code = ''
  if (import.meta.env.DEV && data.debug_code) {
    form.captcha_code = data.debug_code
  }
}

async function submit() {
  error.value = ''
  if (!form.username || !form.password || !form.captcha_code || !captcha.value) {
    error.value = '请填写账号、密码和验证码'
    return
  }
  submitting.value = true
  try {
    await auth.login({
      username: form.username,
      password: form.password,
      captcha_id: captcha.value.captcha_id,
      captcha_code: form.captcha_code,
    })
    ElMessage.success('登录成功')
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
    <section class="auth-story">
      <div class="auth-brand"><Sparkles :size="22" /> DocFlow 智文通</div>
      <div class="auth-copy">
        <span class="eyebrow"><ShieldCheck :size="15" /> 企业技术知识引擎</span>
        <h1>让技术文档<br />真正回答问题</h1>
        <p>统一接入 API 文档、故障案例与版本说明，通过多知识库检索和可引用的流式回答缩短技术排障路径。</p>
      </div>
      <div class="flow-card">
        <div class="flow-line"><span>01</span> 文档解析与切块</div>
        <div class="flow-line"><span>02</span> 稠密 + BM25 混合检索</div>
        <div class="flow-line"><span>03</span> 通义千问流式回答</div>
        <div class="flow-line"><span>04</span> 文档引用与历史会话</div>
      </div>
    </section>

    <section class="auth-panel">
      <div class="auth-form-wrap">
        <span class="page-kicker">账号登录</span>
        <h2>登录工作台</h2>
        <p class="muted">使用你的企业账号继续</p>

        <form class="auth-form" @submit.prevent="submit">
          <label>账号</label>
          <el-input v-model="form.username" size="large" placeholder="请输入账号" autocomplete="username" />
          <label>密码</label>
          <el-input v-model="form.password" size="large" type="password" show-password placeholder="请输入密码" autocomplete="current-password" />
          <label>图形验证码</label>
          <div class="captcha-row">
            <el-input v-model="form.captcha_code" size="large" maxlength="4" placeholder="输入图中字符" @keyup.enter="submit" />
            <button class="captcha-image" type="button" title="刷新验证码" @click="loadCaptcha">
              <img v-if="captcha" :src="captcha.image_data" alt="图形验证码" />
              <RefreshCw :size="18" />
            </button>
          </div>
          <p v-if="error" class="form-error">{{ error }}</p>
          <el-button class="primary-action" type="primary" size="large" native-type="submit" :loading="submitting">登录</el-button>
        </form>

        <p class="auth-switch">还没有账号？<RouterLink to="/register">创建企业账号</RouterLink></p>
      </div>
    </section>
  </div>
</template>
