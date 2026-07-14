import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { api } from '../services/api'
import type {
  ModelConnectionResult,
  ModelPurpose,
  ModelSettingsPayload,
  ModelSettingsStatus,
} from '../types/api'

const emptyStatus = (purpose: ModelPurpose): ModelSettingsStatus => ({
  purpose,
  configured: false,
  protocol: 'openai',
  base_url: '',
  model_id: '',
  api_key_masked: '',
  configured_at: null,
  storage: 'server_memory',
})

export const useModelSettingsStore = defineStore('model-settings', () => {
  const statuses = ref<Record<ModelPurpose, ModelSettingsStatus>>({
    vision: emptyStatus('vision'),
    text: emptyStatus('text'),
  })
  const loading = ref<Record<ModelPurpose, boolean>>({ vision: false, text: false })
  const loaded = ref<Record<ModelPurpose, boolean>>({ vision: false, text: false })
  // The aliases keep existing visual-recognition consumers on the vision status.
  const status = computed(() => statuses.value.vision)
  const configured = computed(() => statuses.value.vision.configured)

  async function load(purpose: ModelPurpose, force = false): Promise<ModelSettingsStatus> {
    if (loaded.value[purpose] && !force) return statuses.value[purpose]
    loading.value[purpose] = true
    try {
      statuses.value[purpose] = await api.getModelSettings(purpose)
      loaded.value[purpose] = true
      return statuses.value[purpose]
    } finally {
      loading.value[purpose] = false
    }
  }

  async function save(purpose: ModelPurpose, payload: ModelSettingsPayload): Promise<ModelSettingsStatus> {
    loading.value[purpose] = true
    try {
      statuses.value[purpose] = await api.saveModelSettings(purpose, payload)
      loaded.value[purpose] = true
      return statuses.value[purpose]
    } finally {
      loading.value[purpose] = false
    }
  }

  function testText(payload: ModelSettingsPayload): Promise<ModelConnectionResult> {
    return api.testTextModelSettings(payload)
  }

  function testVision(payload: ModelSettingsPayload, file: File): Promise<ModelConnectionResult> {
    return api.testVisionModelSettings(payload, file)
  }

  async function clear(purpose: ModelPurpose): Promise<void> {
    loading.value[purpose] = true
    try {
      await api.clearModelSettings(purpose)
      statuses.value[purpose] = emptyStatus(purpose)
      loaded.value[purpose] = true
    } finally {
      loading.value[purpose] = false
    }
  }

  return { statuses, status, loading, loaded, configured, load, save, testText, testVision, clear }
})
