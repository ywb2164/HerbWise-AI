<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import {
  NAlert,
  NButton,
  NDrawer,
  NDrawerContent,
  NForm,
  NFormItem,
  NInput,
  NPopconfirm,
  NRadioButton,
  NRadioGroup,
  NSpin,
  NTag,
  useMessage,
} from 'naive-ui'
import { CheckCircle2, KeyRound, PlugZap, Save, Trash2 } from 'lucide-vue-next'
import { useModelSettingsStore } from '../stores/model-settings'
import type { ModelProtocol, ModelSettingsPayload } from '../types/api'
import { formatDate, getErrorMessage } from '../utils/format'

const show = defineModel<boolean>('show', { default: false })
const modelSettings = useModelSettingsStore()
const message = useMessage()
const testing = ref(false)
const errorText = ref('')
const testResult = ref<{ elapsed: number; reply: string } | null>(null)

const endpoints: Record<ModelProtocol, string> = {
  openai: 'https://maas-coding-api.cn-huabei-1.xf-yun.com/v2',
  anthropic: 'https://maas-coding-api.cn-huabei-1.xf-yun.com/anthropic',
}

const form = reactive({
  protocol: 'openai' as ModelProtocol,
  base_url: endpoints.openai,
  model_id: 'astron-code-latest',
  api_key: '',
})

function payload(): ModelSettingsPayload {
  return {
    protocol: form.protocol,
    base_url: form.base_url.trim(),
    model_id: form.model_id.trim(),
    ...(form.api_key ? { api_key: form.api_key } : {}),
  }
}

function validate(): boolean {
  errorText.value = ''
  if (!form.base_url.trim() || !form.model_id.trim()) {
    errorText.value = '请填写 API 地址和模型 ID'
    return false
  }
  if (!form.api_key && !modelSettings.status.configured) {
    errorText.value = '请填写 API Key'
    return false
  }
  return true
}

async function hydrate(): Promise<void> {
  errorText.value = ''
  testResult.value = null
  try {
    const status = await modelSettings.load(true)
    form.protocol = status.configured ? status.protocol : 'openai'
    form.base_url = status.base_url || endpoints[form.protocol]
    form.model_id = status.model_id || 'astron-code-latest'
    form.api_key = ''
  } catch (error) {
    errorText.value = getErrorMessage(error, '模型设置读取失败')
  }
}

async function testConnection(): Promise<void> {
  if (!validate()) return
  testing.value = true
  testResult.value = null
  try {
    const result = await modelSettings.test(payload())
    testResult.value = { elapsed: result.elapsed_ms, reply: result.reply }
    message.success('模型连接成功')
  } catch (error) {
    errorText.value = getErrorMessage(error, '模型连接失败')
  } finally {
    testing.value = false
  }
}

async function saveSettings(): Promise<void> {
  if (!validate()) return
  try {
    await modelSettings.save(payload())
    form.api_key = ''
    message.success('模型设置已保存')
  } catch (error) {
    errorText.value = getErrorMessage(error, '模型设置保存失败')
  }
}

async function clearSettings(): Promise<void> {
  try {
    await modelSettings.clear()
    form.api_key = ''
    testResult.value = null
    message.success('模型设置已清除')
  } catch (error) {
    errorText.value = getErrorMessage(error, '模型设置清除失败')
  }
}

watch(show, (value) => {
  if (value) void hydrate()
})

watch(
  () => form.protocol,
  (value, previous) => {
    if (!modelSettings.status.configured || form.base_url === endpoints[previous]) {
      form.base_url = endpoints[value]
    }
    testResult.value = null
  },
)
</script>

<template>
  <n-drawer v-model:show="show" placement="right" width="min(460px, 100vw)">
    <n-drawer-content title="模型服务设置" closable :native-scrollbar="false">
      <n-spin :show="modelSettings.loading">
        <div class="settings-content">
          <div class="connection-summary">
            <div>
              <span>连接状态</span>
              <strong>{{ modelSettings.status.configured ? modelSettings.status.model_id : '尚未配置' }}</strong>
              <small v-if="modelSettings.status.configured">
                {{ modelSettings.status.api_key_masked }} · {{ formatDate(modelSettings.status.configured_at) }}
              </small>
            </div>
            <n-tag :type="modelSettings.status.configured ? 'success' : 'default'" :bordered="false">
              {{ modelSettings.status.configured ? '已连接' : '未连接' }}
            </n-tag>
          </div>

          <n-alert v-if="errorText" type="error" :bordered="false" closable @close="errorText = ''">
            {{ errorText }}
          </n-alert>
          <n-alert v-if="testResult" type="success" :bordered="false">
            连接耗时 {{ testResult.elapsed }} ms · {{ testResult.reply }}
          </n-alert>

          <n-form :model="form" label-placement="top" size="large">
            <n-form-item label="接口协议" path="protocol">
              <n-radio-group v-model:value="form.protocol" class="protocol-switch">
                <n-radio-button value="openai">OpenAI 兼容</n-radio-button>
                <n-radio-button value="anthropic">Anthropic</n-radio-button>
              </n-radio-group>
            </n-form-item>
            <n-form-item label="API 地址" path="base_url">
              <n-input v-model:value="form.base_url" placeholder="https://..." clearable />
            </n-form-item>
            <n-form-item label="模型 ID" path="model_id">
              <n-input v-model:value="form.model_id" placeholder="模型标识" clearable />
            </n-form-item>
            <n-form-item label="API Key" path="api_key">
              <n-input
                v-model:value="form.api_key"
                type="password"
                show-password-on="mousedown"
                :placeholder="modelSettings.status.configured ? '留空则沿用当前密钥' : '请输入 API Key'"
                autocomplete="off"
              >
                <template #prefix><KeyRound :size="17" /></template>
              </n-input>
            </n-form-item>
          </n-form>

          <div class="security-note">
            <CheckCircle2 :size="18" />
            <span>密钥仅保存在当前后端进程内存中，服务重启后需重新配置。</span>
          </div>
        </div>
      </n-spin>

      <template #footer>
        <div class="drawer-actions">
          <n-popconfirm v-if="modelSettings.status.configured" @positive-click="clearSettings">
            <template #trigger>
              <n-button quaternary type="error" aria-label="清除模型设置">
                <template #icon><Trash2 :size="17" /></template>
              </n-button>
            </template>
            清除当前模型连接？
          </n-popconfirm>
          <n-button :loading="testing" @click="testConnection">
            测试连接
            <template #icon><PlugZap :size="17" /></template>
          </n-button>
          <n-button type="primary" :loading="modelSettings.loading" @click="saveSettings">
            保存
            <template #icon><Save :size="17" /></template>
          </n-button>
        </div>
      </template>
    </n-drawer-content>
  </n-drawer>
</template>

<style scoped>
.settings-content {
  display: grid;
  gap: 20px;
}

.connection-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 16px 0 18px;
  border-bottom: 1px solid var(--line);
}

.connection-summary > div {
  display: grid;
  gap: 3px;
  min-width: 0;
}

.connection-summary span,
.connection-summary small {
  color: var(--muted);
  font-size: 11px;
}

.connection-summary strong {
  overflow: hidden;
  color: var(--ink);
  font-size: 16px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.protocol-switch {
  display: flex;
  width: 100%;
}

.protocol-switch :deep(.n-radio-button) {
  flex: 1 1 0;
  text-align: center;
}

.security-note {
  display: grid;
  grid-template-columns: 22px minmax(0, 1fr);
  gap: 9px;
  padding: 13px 0;
  color: var(--muted);
  border-top: 1px solid var(--line);
  font-size: 12px;
  line-height: 1.6;
}

.security-note svg {
  color: var(--primary);
}

.drawer-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  width: 100%;
}

.drawer-actions > :first-child {
  margin-right: auto;
}
</style>
