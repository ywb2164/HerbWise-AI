<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
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
  NTabPane,
  NTabs,
  NTag,
  useMessage,
} from 'naive-ui'
import { CheckCircle2, KeyRound, PlugZap, Save, Trash2, Upload } from 'lucide-vue-next'
import { useModelSettingsStore } from '../stores/model-settings'
import type { ModelProtocol, ModelPurpose, ModelSettingsPayload } from '../types/api'
import { formatDate, getErrorMessage } from '../utils/format'

const show = defineModel<boolean>('show', { default: false })
const modelSettings = useModelSettingsStore()
const message = useMessage()
const activePurpose = ref<ModelPurpose>('vision')
const testing = reactive<Record<ModelPurpose, boolean>>({ vision: false, text: false })
const errors = reactive<Record<ModelPurpose, string>>({ vision: '', text: '' })
const results = reactive<Record<ModelPurpose, { elapsed: number; reply: string } | null>>({ vision: null, text: null })
const visionFile = ref<File | null>(null)

const endpoints: Record<ModelProtocol, string> = {
  openai: 'https://maas-coding-api.cn-huabei-1.xf-yun.com/v2',
  anthropic: 'https://maas-coding-api.cn-huabei-1.xf-yun.com/anthropic',
}

type SettingsForm = { protocol: ModelProtocol; base_url: string; model_id: string; api_key: string }
const draftKey = (purpose: ModelPurpose) => `herbwise.model-settings.${purpose}`

function readDraft(purpose: ModelPurpose): Pick<SettingsForm, 'protocol' | 'base_url' | 'model_id'> {
  try {
    const parsed = JSON.parse(localStorage.getItem(draftKey(purpose)) || '{}') as Partial<SettingsForm>
    const protocol = parsed.protocol === 'anthropic' ? 'anthropic' : 'openai'
    return { protocol, base_url: parsed.base_url || endpoints[protocol], model_id: parsed.model_id || '' }
  } catch {
    return { protocol: 'openai', base_url: endpoints.openai, model_id: '' }
  }
}

const forms = reactive<Record<ModelPurpose, SettingsForm>>({
  vision: { ...readDraft('vision'), model_id: readDraft('vision').model_id || 'qwen3-vl-plus', api_key: '' },
  text: { ...readDraft('text'), model_id: readDraft('text').model_id || 'astron-code-latest', api_key: '' },
})
const activeForm = computed(() => forms[activePurpose.value])
const activeStatus = computed(() => modelSettings.statuses[activePurpose.value])

function persistDraft(purpose: ModelPurpose): void {
  const { protocol, base_url, model_id } = forms[purpose]
  localStorage.setItem(draftKey(purpose), JSON.stringify({ protocol, base_url, model_id }))
}

function payload(purpose: ModelPurpose): ModelSettingsPayload {
  const form = forms[purpose]
  return {
    protocol: form.protocol,
    base_url: form.base_url.trim(),
    model_id: form.model_id.trim(),
    ...(form.api_key ? { api_key: form.api_key } : {}),
  }
}

function validate(purpose: ModelPurpose): boolean {
  errors[purpose] = ''
  const form = forms[purpose]
  if (!form.base_url.trim() || !form.model_id.trim()) {
    errors[purpose] = '请填写 API 地址和模型 ID'
    return false
  }
  if (!form.api_key && !modelSettings.statuses[purpose].configured) {
    errors[purpose] = '请填写 API Key'
    return false
  }
  if (purpose === 'vision' && !visionFile.value) {
    errors[purpose] = '请先选择一张 JPG、PNG 或 WebP 图片进行识图测试'
    return false
  }
  return true
}

async function hydrate(purpose: ModelPurpose): Promise<void> {
  errors[purpose] = ''
  results[purpose] = null
  try {
    const status = await modelSettings.load(purpose, true)
    const draft = readDraft(purpose)
    forms[purpose].protocol = status.configured ? status.protocol : draft.protocol
    forms[purpose].base_url = status.base_url || draft.base_url || endpoints[forms[purpose].protocol]
    forms[purpose].model_id = status.model_id || draft.model_id || (purpose === 'vision' ? 'qwen3-vl-plus' : 'astron-code-latest')
    forms[purpose].api_key = ''
  } catch (error) {
    errors[purpose] = getErrorMessage(error, '模型设置读取失败')
  }
}

async function testConnection(): Promise<void> {
  const purpose = activePurpose.value
  if (!validate(purpose)) return
  testing[purpose] = true
  results[purpose] = null
  try {
    const result = purpose === 'vision'
      ? await modelSettings.testVision(payload(purpose), visionFile.value as File)
      : await modelSettings.testText(payload(purpose))
    results[purpose] = { elapsed: result.elapsed_ms, reply: result.reply }
    message.success(purpose === 'vision' ? '识图模型测试成功' : '文字模型连接成功')
  } catch (error) {
    errors[purpose] = getErrorMessage(error, '模型连接失败')
  } finally {
    testing[purpose] = false
  }
}

async function saveSettings(): Promise<void> {
  const purpose = activePurpose.value
  errors[purpose] = ''
  // Saving a vision configuration does not require a test image.
  if (!forms[purpose].base_url.trim() || !forms[purpose].model_id.trim()) {
    errors[purpose] = '请填写 API 地址和模型 ID'
    return
  }
  if (!forms[purpose].api_key && !modelSettings.statuses[purpose].configured) {
    errors[purpose] = '请填写 API Key'
    return
  }
  try {
    await modelSettings.save(purpose, payload(purpose))
    forms[purpose].api_key = ''
    persistDraft(purpose)
    message.success(purpose === 'vision' ? '识图模型已保存' : '文字模型已保存')
  } catch (error) {
    errors[purpose] = getErrorMessage(error, '模型设置保存失败')
  }
}

async function clearSettings(): Promise<void> {
  const purpose = activePurpose.value
  try {
    await modelSettings.clear(purpose)
    forms[purpose].api_key = ''
    results[purpose] = null
    message.success(purpose === 'vision' ? '识图模型设置已清除' : '文字模型设置已清除')
  } catch (error) {
    errors[purpose] = getErrorMessage(error, '模型设置清除失败')
  }
}

function selectVisionFile(event: Event): void {
  const input = event.target as HTMLInputElement
  visionFile.value = input.files?.[0] || null
  results.vision = null
}

watch(show, (value) => {
  if (value) void Promise.all([hydrate('vision'), hydrate('text')])
})
watch(forms, () => { persistDraft('vision'); persistDraft('text') }, { deep: true })
watch(() => activeForm.value.protocol, (value, previous) => {
  if (!activeStatus.value.configured || activeForm.value.base_url === endpoints[previous]) activeForm.value.base_url = endpoints[value]
  results[activePurpose.value] = null
})
</script>

<template>
  <n-drawer v-model:show="show" placement="right" width="min(520px, 100vw)">
    <n-drawer-content title="模型服务设置" closable :native-scrollbar="false">
      <n-tabs v-model:value="activePurpose" type="line" animated>
        <n-tab-pane name="vision" tab="识图模型">
          <p class="purpose-note">用于药材图片名称识别；测试会真实发送选中的图片，不调用 YOLO、知识包或学习任务。</p>
          <section class="settings-content">
            <div class="connection-summary">
              <div><span>连接状态</span><strong>{{ activeStatus.configured ? activeStatus.model_id : '尚未配置' }}</strong><small v-if="activeStatus.configured">{{ activeStatus.api_key_masked }} · {{ formatDate(activeStatus.configured_at) }}</small></div>
              <n-tag :type="activeStatus.configured ? 'success' : 'default'" :bordered="false">{{ activeStatus.configured ? '已连接' : '需重新配置' }}</n-tag>
            </div>
            <n-alert v-if="errors.vision" type="error" :bordered="false" closable @close="errors.vision = ''">{{ errors.vision }}</n-alert>
            <n-alert v-if="results.vision" type="success" :bordered="false">识图耗时 {{ results.vision.elapsed }} ms · {{ results.vision.reply }}</n-alert>
            <n-form :model="forms.vision" label-placement="top" size="large">
              <n-form-item label="接口协议"><n-radio-group v-model:value="forms.vision.protocol" class="protocol-switch"><n-radio-button value="openai">OpenAI 兼容</n-radio-button><n-radio-button value="anthropic">Anthropic</n-radio-button></n-radio-group></n-form-item>
              <n-form-item label="API 地址"><n-input v-model:value="forms.vision.base_url" placeholder="https://..." clearable /></n-form-item>
              <n-form-item label="模型 ID"><n-input v-model:value="forms.vision.model_id" placeholder="例如 qwen3-vl-plus" clearable /></n-form-item>
              <n-form-item label="API Key"><n-input v-model:value="forms.vision.api_key" type="password" show-password-on="mousedown" :placeholder="activeStatus.configured ? '留空则沿用当前密钥' : '请输入 API Key'" autocomplete="off"><template #prefix><KeyRound :size="17" /></template></n-input></n-form-item>
              <n-form-item label="图片测试"><label class="image-test"><Upload :size="18" /><input accept="image/jpeg,image/png,image/webp" type="file" @change="selectVisionFile" /><span>{{ visionFile?.name || '选择 JPG、PNG 或 WebP 图片' }}</span></label></n-form-item>
            </n-form>
          </section>
        </n-tab-pane>
        <n-tab-pane name="text" tab="文字模型">
          <p class="purpose-note">用于学习规划、学习建议、资源生成和审核，不参与药材识图命名。</p>
          <section class="settings-content">
            <div class="connection-summary">
              <div><span>连接状态</span><strong>{{ activeStatus.configured ? activeStatus.model_id : '尚未配置' }}</strong><small v-if="activeStatus.configured">{{ activeStatus.api_key_masked }} · {{ formatDate(activeStatus.configured_at) }}</small></div>
              <n-tag :type="activeStatus.configured ? 'success' : 'default'" :bordered="false">{{ activeStatus.configured ? '已连接' : '需重新配置' }}</n-tag>
            </div>
            <n-alert v-if="errors.text" type="error" :bordered="false" closable @close="errors.text = ''">{{ errors.text }}</n-alert>
            <n-alert v-if="results.text" type="success" :bordered="false">连接耗时 {{ results.text.elapsed }} ms · {{ results.text.reply }}</n-alert>
            <n-form :model="forms.text" label-placement="top" size="large">
              <n-form-item label="接口协议"><n-radio-group v-model:value="forms.text.protocol" class="protocol-switch"><n-radio-button value="openai">OpenAI 兼容</n-radio-button><n-radio-button value="anthropic">Anthropic</n-radio-button></n-radio-group></n-form-item>
              <n-form-item label="API 地址"><n-input v-model:value="forms.text.base_url" placeholder="https://..." clearable /></n-form-item>
              <n-form-item label="模型 ID"><n-input v-model:value="forms.text.model_id" placeholder="模型标识" clearable /></n-form-item>
              <n-form-item label="API Key"><n-input v-model:value="forms.text.api_key" type="password" show-password-on="mousedown" :placeholder="activeStatus.configured ? '留空则沿用当前密钥' : '请输入 API Key'" autocomplete="off"><template #prefix><KeyRound :size="17" /></template></n-input></n-form-item>
            </n-form>
          </section>
        </n-tab-pane>
      </n-tabs>
      <div class="security-note"><CheckCircle2 :size="18" /><span>密钥仅保存在当前后端进程内存中；浏览器仅保存协议、地址和模型 ID，服务重启后请重新配置密钥。</span></div>
      <template #footer><div class="drawer-actions"><n-popconfirm v-if="activeStatus.configured" @positive-click="clearSettings"><template #trigger><n-button quaternary type="error" aria-label="清除模型设置"><template #icon><Trash2 :size="17" /></template></n-button></template>清除当前模型连接？</n-popconfirm><n-button :loading="testing[activePurpose]" @click="testConnection">{{ activePurpose === 'vision' ? '测试识图' : '测试连接' }}<template #icon><PlugZap :size="17" /></template></n-button><n-button type="primary" :loading="modelSettings.loading[activePurpose]" @click="saveSettings">保存<template #icon><Save :size="17" /></template></n-button></div></template>
    </n-drawer-content>
  </n-drawer>
</template>

<style scoped>
.purpose-note { margin: 0 0 16px; color: var(--muted); font-size: 12px; line-height: 1.65; }
.settings-content { display: grid; gap: 20px; }
.connection-summary { display: flex; align-items: center; justify-content: space-between; gap: 18px; padding: 4px 0 18px; border-bottom: 1px solid var(--line); }
.connection-summary > div { display: grid; gap: 3px; min-width: 0; }
.connection-summary span, .connection-summary small { color: var(--muted); font-size: 11px; }
.connection-summary strong { overflow: hidden; color: var(--ink); font-size: 16px; text-overflow: ellipsis; white-space: nowrap; }
.protocol-switch { display: flex; width: 100%; }.protocol-switch :deep(.n-radio-button) { flex: 1 1 0; text-align: center; }
.image-test { display: flex; align-items: center; gap: 9px; width: 100%; padding: 11px; color: var(--muted); border: 1px dashed var(--line-strong); border-radius: 6px; cursor: pointer; }.image-test input { display: none; }.image-test span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.security-note { display: grid; grid-template-columns: 22px minmax(0, 1fr); gap: 9px; margin-top: 18px; padding: 13px 0; color: var(--muted); border-top: 1px solid var(--line); font-size: 12px; line-height: 1.6; }.security-note svg { color: var(--primary); }
.drawer-actions { display: flex; justify-content: flex-end; gap: 10px; width: 100%; }.drawer-actions > :first-child { margin-right: auto; }
</style>
