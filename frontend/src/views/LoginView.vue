<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NAlert, NButton, NForm, NFormItem, NInput, NRadioButton, NRadioGroup, useMessage } from 'naive-ui'
import { ArrowRight, LockKeyhole, UserRound } from 'lucide-vue-next'
import AppLogo from '../components/AppLogo.vue'
import TcmIcon from '../components/TcmIcon.vue'
import { handoffToAdmin } from '../services/auth-storage'
import { useAuthStore } from '../stores/auth'
import { getErrorMessage } from '../utils/format'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const message = useMessage()
const loading = ref(false)
const errorText = ref('')
const captchaCode = ref('B7C9')
const requestedRole = route.query.role === 'admin' ? 'admin' : 'student'
const accountType = ref<'student' | 'admin'>(requestedRole)
const form = reactive({
  username: requestedRole,
  password: 'HerbWise@2026',
})

const capabilities = [
  {
    icon: 'identify',
    title: '本草多模态智鉴',
    desc: '图像、性状、气味与规则证据融合，输出置信度和鉴别依据。',
  },
  {
    icon: 'risk',
    title: '临床质量控制',
    desc: '围绕调剂、复核、预警和放行建立中药临床质控闭环。',
  },
  {
    icon: 'formula',
    title: '方剂配伍智析',
    desc: '支持药性、归经、功效、配伍机制与数字问答展示。',
  },
  {
    icon: 'trace',
    title: '批次溯源监管',
    desc: '沉淀产地、供应方、风险标签和溯源码，便于追溯复核。',
  },
]

function applyAccount(value: 'student' | 'admin'): void {
  accountType.value = value
  form.username = value
  form.password = 'HerbWise@2026'
  errorText.value = ''
}

function refreshCaptcha(): void {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
  captchaCode.value = Array.from(
    { length: 4 },
    () => chars[Math.floor(Math.random() * chars.length)],
  ).join('')
}

async function submit(): Promise<void> {
  if (!form.username.trim() || !form.password) {
    errorText.value = '请填写账号和密码'
    return
  }
  loading.value = true
  errorText.value = ''
  try {
    await auth.login(form.username.trim(), form.password)
    if (accountType.value === 'admin' && !auth.isAdmin) {
      await auth.logout()
      errorText.value = '该账号没有管理员权限'
      return
    }
    if (accountType.value === 'student' && auth.isAdmin) {
      await auth.logout()
      errorText.value = '管理员账号请从管理员端登录'
      return
    }
    message.success('登录成功')
    if (auth.isAdmin) {
      handoffToAdmin()
      return
    }
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/dashboard'
    await router.replace(redirect.startsWith('/admin') ? '/dashboard' : redirect)
  } catch (error) {
    errorText.value = getErrorMessage(error, '登录失败，请检查账号或后端服务')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="login-page">
    <header class="login-topbar">
      <AppLogo :linked="false" />
      <p>AI 赋能中医药教育与实训的智能学习平台</p>
    </header>

    <section class="hero-panel">
      <div class="hero-kicker">
        <i />
        <span>以学习者画像驱动中药实训，以知识生成连接识别与成长</span>
        <i />
      </div>
      <h1>本草智策</h1>
      <p class="hero-subtitle">
        中药智能鉴别与临床药事质控<br />
        个性化知识生成与多智能体协同决策系统
      </p>

      <div class="feature-grid" aria-label="平台核心能力">
        <article v-for="item in capabilities" :key="item.title" class="feature-item">
          <span><TcmIcon :name="item.icon" size="sm" /></span>
          <div>
            <strong>{{ item.title }}</strong>
            <p>{{ item.desc }}</p>
          </div>
        </article>
      </div>
    </section>

    <aside class="login-console">
      <div class="console-brand">
        <AppLogo :linked="false" />
        <p>本草智策——中药智能鉴别与临床药事质控</p>
      </div>

      <div class="section-title">
        <span />
        <h2>用户登录</h2>
        <span />
      </div>

      <n-radio-group
        v-model:value="accountType"
        class="role-tabs"
        name="account-type"
        @update:value="applyAccount"
      >
        <n-radio-button value="student">学习者</n-radio-button>
        <n-radio-button value="admin">管理端</n-radio-button>
      </n-radio-group>

      <n-alert
        v-if="errorText"
        type="error"
        :bordered="false"
        closable
        class="login-alert"
        @close="errorText = ''"
      >
        {{ errorText }}
      </n-alert>

      <n-form :model="form" label-placement="top" size="large" class="signin-form" @submit.prevent="submit">
        <n-form-item label="账号" path="username">
          <n-input v-model:value="form.username" placeholder="请输入账号" autocomplete="username">
            <template #prefix><UserRound :size="17" /></template>
          </n-input>
        </n-form-item>
        <n-form-item label="密码" path="password">
          <n-input
            v-model:value="form.password"
            type="password"
            show-password-on="mousedown"
            placeholder="请输入密码"
            autocomplete="current-password"
            @keyup.enter="submit"
          >
            <template #prefix><LockKeyhole :size="17" /></template>
          </n-input>
        </n-form-item>

        <div class="captcha-preview">
          <div>
            <strong>统一身份认证</strong>
            <span>演示环境验证码</span>
          </div>
          <button type="button" title="刷新验证码" @click="refreshCaptcha">{{ captchaCode }}</button>
        </div>

        <n-button type="primary" size="large" block :loading="loading" attr-type="submit" class="submit-btn">
          进入系统
          <template #icon><ArrowRight :size="18" /></template>
        </n-button>
      </n-form>

      <div class="console-meta">
        <span>统一身份认证</span>
        <span>{{ accountType === 'admin' ? '进入管理工作台' : '进入学习工作台' }}</span>
      </div>

      <button type="button" class="project-entry" @click="submit">
        <span>
          <strong>项目展示入口</strong>
          <small>CHALLENGE CUP 2026</small>
        </span>
        <i><ArrowRight :size="17" /></i>
      </button>
    </aside>
  </main>
</template>

<style scoped>
.login-page {
  position: relative;
  isolation: isolate;
  min-height: 100vh;
  overflow: hidden;
  color: #153f34;
  background: #faf8ef url('/images/herbwise-login-scene.jpg') center / cover no-repeat;
}

.login-page::before {
  position: absolute;
  z-index: -1;
  inset: 0;
  content: "";
  background:
    linear-gradient(90deg, rgba(255, 253, 244, 0.04) 0%, rgba(255, 253, 244, 0.08) 52%, rgba(255, 253, 244, 0.75) 100%),
    rgba(255, 253, 244, 0.08);
}

.login-topbar {
  position: absolute;
  z-index: 2;
  top: 30px;
  right: 4%;
  left: 4%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
}

.login-topbar :deep(.logo-mark) {
  width: 52px;
  height: 52px;
  flex-basis: 52px;
  border-radius: 10px;
  box-shadow: 0 10px 24px rgba(26, 75, 58, 0.18);
}

.login-topbar :deep(.logo-copy strong) {
  font-family: "Noto Serif SC", "Songti SC", SimSun, serif;
  font-size: 24px;
  letter-spacing: 0;
}

.login-topbar p {
  color: #315548;
  font-family: "Noto Serif SC", "Songti SC", SimSun, serif;
  font-size: 14px;
}

.hero-panel {
  position: absolute;
  z-index: 1;
  right: 43%;
  bottom: clamp(80px, 8vh, 112px);
  left: 4%;
  max-width: 900px;
}

.hero-kicker {
  display: grid;
  grid-template-columns: 30px minmax(0, auto) 30px;
  align-items: center;
  justify-content: start;
  gap: 14px;
  color: #164e3f;
  font-size: 13px;
  font-weight: 700;
}

.hero-kicker i {
  width: 30px;
  height: 1px;
  background: #b89047;
}

.hero-kicker span {
  min-width: 0;
  line-height: 1.6;
  text-align: center;
  text-wrap: balance;
}

.hero-panel h1 {
  margin: 20px 0 6px;
  color: #11513f;
  font-family: "Noto Serif SC", "Songti SC", STKaiti, serif;
  font-size: clamp(60px, 5vw, 82px);
  line-height: 1;
  font-weight: 700;
  letter-spacing: 0;
}

.hero-subtitle {
  color: #16604b;
  font-family: "Noto Serif SC", "Songti SC", SimSun, serif;
  font-size: clamp(19px, 1.55vw, 25px);
  line-height: 1.6;
  font-weight: 650;
}

.feature-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  margin-top: 44px;
  border-top: 1px solid rgba(138, 108, 50, 0.28);
  border-bottom: 1px solid rgba(138, 108, 50, 0.28);
}

.feature-item {
  display: grid;
  grid-template-columns: 48px minmax(0, 1fr);
  gap: 11px;
  min-height: 156px;
  padding: 20px 14px;
  border-right: 1px solid rgba(138, 108, 50, 0.2);
}

.feature-item:last-child {
  border-right: 0;
}

.feature-item > span {
  display: grid;
  width: 48px;
  height: 48px;
  padding: 4px;
  background: rgba(255, 252, 232, 0.72);
  border: 1px solid rgba(190, 149, 65, 0.32);
  border-radius: 50%;
  place-items: center;
}

.feature-item strong {
  display: block;
  margin: 2px 0 5px;
  color: #154b3c;
  font-size: 14px;
  line-height: 1.4;
}

.feature-item p {
  color: #53685f;
  font-size: 12px;
  line-height: 1.65;
}

.login-console {
  position: absolute;
  z-index: 3;
  top: 50%;
  right: 4%;
  display: grid;
  gap: 16px;
  width: min(36.5vw, 526px);
  padding: 34px 32px 30px;
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid rgba(194, 166, 111, 0.5);
  border-radius: 8px;
  box-shadow: 0 24px 60px rgba(67, 72, 54, 0.16);
  transform: translateY(-45%);
  backdrop-filter: blur(14px);
}

.console-brand {
  display: grid;
  grid-template-columns: max-content minmax(0, 1fr);
  align-items: center;
  gap: 16px;
  min-width: 0;
  padding-bottom: 2px;
}

.console-brand p {
  min-width: 0;
  padding-left: 16px;
  color: #687b72;
  border-left: 1px solid #e1ded2;
  font-size: 11px;
  line-height: 1.6;
  overflow-wrap: anywhere;
}

.console-brand :deep(.app-logo) {
  flex: none;
}

.console-brand :deep(.logo-copy strong) {
  font-family: "Noto Serif SC", "Songti SC", SimSun, serif;
  font-size: 22px;
}

.section-title {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 15px;
  margin-top: 4px;
}

.section-title span {
  height: 1px;
  background: linear-gradient(90deg, transparent, #c9a75f);
}

.section-title span:last-child {
  background: linear-gradient(90deg, #c9a75f, transparent);
}

.section-title h2 {
  color: #244f41;
  font-family: "Noto Serif SC", "Songti SC", SimSun, serif;
  font-size: 18px;
}

.role-tabs {
  display: flex;
  width: 100%;
}

.role-tabs :deep(.n-radio-button) {
  flex: 1 1 0;
  text-align: center;
}

.login-alert {
  margin-bottom: -5px;
}

.signin-form :deep(.n-form-item) {
  margin-bottom: 8px;
}

.signin-form :deep(.n-form-item-label) {
  color: #345548;
  font-size: 12px;
  font-weight: 650;
}

.signin-form :deep(.n-input) {
  --n-height: 52px !important;
  background: rgba(248, 251, 249, 0.9);
}

.captcha-preview {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  min-height: 72px;
  margin: 3px 0 14px;
  padding: 13px 14px;
  background: #fbfaf6;
  border: 1px solid #e4dfd0;
  border-radius: 7px;
}

.captcha-preview div {
  display: grid;
  gap: 3px;
}

.captcha-preview strong {
  color: #315548;
  font-size: 13px;
}

.captcha-preview span {
  color: #8a958f;
  font-size: 10px;
}

.captcha-preview button {
  min-width: 76px;
  height: 44px;
  color: #3e4e46;
  background: #fff1c8;
  border: 1px solid #dfc478;
  border-radius: 6px;
  cursor: pointer;
  font-family: "SFMono-Regular", Consolas, monospace;
  font-size: 16px;
  font-weight: 800;
  letter-spacing: 0.12em;
}

.submit-btn {
  min-height: 52px;
  font-family: "Noto Serif SC", "Songti SC", SimSun, serif;
  font-size: 16px;
  font-weight: 700;
}

.console-meta {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  padding: 1px 0 15px;
  color: #6d7d75;
  border-bottom: 1px solid #e3dfd3;
  font-size: 11px;
}

.console-meta span:last-child {
  color: #215643;
}

.project-entry {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-height: 66px;
  padding: 11px 16px;
  color: #284f41;
  background: #fffef9;
  border: 1px solid #ddc887;
  border-radius: 7px;
  cursor: pointer;
  text-align: left;
}

.project-entry > span {
  display: grid;
  gap: 2px;
}

.project-entry strong {
  font-family: "Noto Serif SC", "Songti SC", SimSun, serif;
  font-size: 15px;
}

.project-entry small {
  color: #8b8c7d;
  font-size: 9px;
  letter-spacing: 0.08em;
}

.project-entry i {
  display: grid;
  width: 36px;
  height: 36px;
  border: 1px solid #ddc887;
  border-radius: 50%;
  place-items: center;
}

@media (max-width: 1180px) {
  .login-console {
    right: 3%;
    width: min(42vw, 500px);
  }

  .hero-panel {
    right: 47%;
    left: 3%;
  }

  .feature-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .feature-item {
    min-height: 112px;
  }

  .feature-item:nth-child(2) {
    border-right: 0;
  }

  .feature-item:nth-child(-n + 2) {
    border-bottom: 1px solid rgba(138, 108, 50, 0.2);
  }
}

@media (max-width: 860px) {
  .login-page {
    min-height: 100dvh;
    overflow: auto;
    padding: 96px 20px 28px;
    background-position: 32% center;
  }

  .login-page::before {
    background: rgba(255, 253, 244, 0.83);
  }

  .login-topbar {
    top: 20px;
    right: 20px;
    left: 20px;
  }

  .login-topbar p {
    display: none;
  }

  .hero-panel {
    position: relative;
    right: auto;
    bottom: auto;
    left: auto;
    max-width: none;
    margin: 0 auto 22px;
  }

  .hero-kicker,
  .feature-grid {
    display: none;
  }

  .hero-panel h1 {
    margin: 0 0 6px;
    font-size: 44px;
  }

  .hero-subtitle {
    font-size: 16px;
  }

  .login-console {
    position: relative;
    top: auto;
    right: auto;
    width: min(100%, 520px);
    margin: 0 auto;
    padding: 27px 22px 24px;
    transform: none;
  }

  .console-brand {
    grid-template-columns: 1fr;
    gap: 9px;
  }

  .console-brand p {
    padding-left: 0;
    border-left: 0;
    line-height: 1.55;
  }
}
</style>
