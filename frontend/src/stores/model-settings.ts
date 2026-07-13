import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { api } from '../services/api'
import type {
  ModelConnectionResult,
  ModelSettingsPayload,
  ModelSettingsStatus,
} from '../types/api'

const emptyStatus = (): ModelSettingsStatus => ({
  configured: false,
  protocol: 'openai',
  base_url: '',
  model_id: '',
  api_key_masked: '',
  configured_at: null,
  storage: 'server_memory',
})

export const useModelSettingsStore = defineStore('model-settings', () => {
  const status = ref<ModelSettingsStatus>(emptyStatus())
  const loading = ref(false)
  const loaded = ref(false)
  const configured = computed(() => status.value.configured)

  async function load(force = false): Promise<ModelSettingsStatus> {
    if (loaded.value && !force) return status.value
    loading.value = true
    try {
      status.value = await api.getModelSettings()
      loaded.value = true
      return status.value
    } finally {
      loading.value = false
    }
  }

  async function save(payload: ModelSettingsPayload): Promise<ModelSettingsStatus> {
    loading.value = true
    try {
      status.value = await api.saveModelSettings(payload)
      loaded.value = true
      return status.value
    } finally {
      loading.value = false
    }
  }

  function test(payload: ModelSettingsPayload): Promise<ModelConnectionResult> {
    return api.testModelSettings(payload)
  }

  async function clear(): Promise<void> {
    loading.value = true
    try {
      await api.clearModelSettings()
      status.value = emptyStatus()
      loaded.value = true
    } finally {
      loading.value = false
    }
  }

  return { status, loading, loaded, configured, load, save, test, clear }
})
