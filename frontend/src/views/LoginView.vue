<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NAlert, NButton, NForm, NFormItem, NInput, NRadioButton, NRadioGroup, useMessage } from 'naive-ui'
import { ArrowRight, LockKeyhole, UserRound } from 'lucide-vue-next'
import AppLogo from '../components/AppLogo.vue'
import { handoffToAdmin } from '../services/auth-storage'
import { useAuthStore } from '../stores/auth'
import { getErrorMessage } from '../utils/format'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const message = useMessage()
const loading = ref(false)
const errorText = ref('')
const requestedRole = route.query.role === 'admin' ? 'admin' : 'student'
const accountType = ref<'student' | 'admin'>(requestedRole)
const form = reactive({
  username: requestedRole,
  password: 'HerbWise@2026',
})

function applyAccount(value: 'student' | 'admin'): void {
  accountType.value = value
  form.username = value
  form.password = 'HerbWise@2026'
  errorText.value = ''
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
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/onboarding'
    await router.replace(redirect.startsWith('/admin') ? '/onboarding' : redirect)
  } catch (error) {
    errorText.value = getErrorMessage(error, '登录失败，请检查账号或后端服务')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="login-page">
    <section class="login-visual" aria-label="中草药学习场景">
      <div class="visual-brand"><AppLogo :linked="false" /></div>
      <span class="project-mark">挑战杯创新项目<br />CHALLENGE CUP 2026</span>
    </section>

    <section class="login-panel">
      <div class="login-form-wrap">
        <div class="login-heading">
          <span class="eyebrow">安全访问</span>
          <h1>登录本草智策</h1>
        </div>

        <n-radio-group
          v-model:value="accountType"
          class="account-switch"
          name="account-type"
          @update:value="applyAccount"
        >
          <n-radio-button value="student">学习者</n-radio-button>
          <n-radio-button value="admin">管理员端</n-radio-button>
        </n-radio-group>

        <n-alert v-if="errorText" type="error" :bordered="false" closable @close="errorText = ''">
          {{ errorText }}
        </n-alert>

        <n-form :model="form" label-placement="top" size="large" @submit.prevent="submit">
          <n-form-item label="账号" path="username">
            <n-input v-model:value="form.username" placeholder="请输入账号" autocomplete="username">
              <template #prefix><UserRound :size="18" /></template>
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
              <template #prefix><LockKeyhole :size="18" /></template>
            </n-input>
          </n-form-item>
          <n-button type="primary" size="large" block :loading="loading" attr-type="submit">
            进入系统
            <template #icon><ArrowRight :size="18" /></template>
          </n-button>
        </n-form>

        <div class="login-footnote">
          <span class="status-dot success" />
          <span>统一身份认证</span>
          <code>{{ accountType === 'admin' ? 'ADMIN' : 'LEARNER' }}</code>
        </div>
      </div>
    </section>
  </main>
</template>

<style scoped>
.login-page {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(420px, 0.65fr);
  min-height: 100vh;
  background: #fff;
}

.login-visual {
  position: relative;
  min-height: 100vh;
  overflow: hidden;
  background-color: #edf2ed;
  background-image: url('/images/herbal-workbench.png');
  background-position: center;
  background-size: cover;
}

.visual-brand {
  position: absolute;
  top: 36px;
  left: 40px;
}

.project-mark {
  position: absolute;
  right: 36px;
  bottom: 30px;
  color: #435048;
  font-size: 11px;
  line-height: 1.55;
  font-weight: 700;
  text-align: right;
}

.login-panel {
  display: grid;
  min-height: 100vh;
  padding: 48px;
  border-left: 1px solid var(--line);
  place-items: center;
}

.login-form-wrap {
  display: grid;
  gap: 22px;
  width: min(100%, 390px);
}

.login-heading {
  display: grid;
  gap: 6px;
}

.login-heading h1 {
  color: var(--ink);
  font-size: 28px;
  line-height: 1.3;
  font-weight: 720;
  letter-spacing: 0;
}

.account-switch {
  display: flex;
  width: 100%;
  flex-wrap: nowrap;
}

.account-switch :deep(.n-radio-button) {
  width: auto;
  flex: 1 1 0;
  text-align: center;
}

.login-footnote {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-top: 4px;
  color: var(--muted);
  font-size: 12px;
}

.login-footnote code {
  margin-left: auto;
  color: var(--primary-strong);
  font-size: 11px;
}

@media (max-width: 900px) {
  .login-page {
    grid-template-columns: 1fr;
  }

  .login-visual {
    min-height: 220px;
    max-height: 30vh;
    background-position: center 38%;
  }

  .visual-brand {
    top: 22px;
    left: 22px;
  }

  .project-mark {
    right: 20px;
    bottom: 16px;
  }

  .login-panel {
    min-height: calc(100vh - 220px);
    padding: 36px 22px;
    border-top: 1px solid var(--line);
    border-left: 0;
  }
}

@media (max-width: 480px) {
  .login-visual {
    min-height: 170px;
  }

  .project-mark {
    display: none;
  }

  .login-panel {
    min-height: calc(100vh - 170px);
    place-items: start center;
  }
}
</style>
