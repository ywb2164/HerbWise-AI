<script setup lang="ts">
import { computed, h, onMounted, reactive, ref } from 'vue'
import {
  NAvatar,
  NButton,
  NDataTable,
  NDrawer,
  NDrawerContent,
  NForm,
  NFormItem,
  NInput,
  NPagination,
  NSelect,
  NSpace,
  NSpin,
  NSwitch,
  NTag,
  useDialog,
  useMessage,
  type DataTableColumns,
} from 'naive-ui'
import { Pencil, Plus, RefreshCw, Trash2 } from 'lucide-vue-next'
import PageHeader from '../../components/PageHeader.vue'
import { api } from '../../services/api'
import { useAuthStore } from '../../stores/auth'
import type { AdminRecord, AdminUser, JsonRecord } from '../../types/api'
import { formatDate, getErrorMessage } from '../../utils/format'

const auth = useAuthStore()
const message = useMessage()
const dialog = useDialog()
const loading = ref(false)
const saving = ref(false)
const users = ref<AdminUser[]>([])
const roleOptions = ref<Array<{ label: string; value: string }>>([])
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const drawerOpen = ref(false)
const editing = ref<AdminUser | null>(null)
const errorText = ref('')
const form = reactive({
  username: '',
  password: '',
  display_name: '',
  email: '',
  learner_id: '',
  role_codes: [] as string[],
  is_active: true,
  is_superuser: false,
})

function iconButton(icon: typeof Pencil, label: string, action: () => void, disabled = false) {
  return h(
    NButton,
    {
      quaternary: true,
      circle: true,
      size: 'small',
      disabled,
      title: label,
      'aria-label': label,
      onClick: action,
    },
    { icon: () => h(icon, { size: 16 }) },
  )
}

const columns = computed<DataTableColumns<AdminUser>>(() => [
  {
    key: 'display_name',
    title: '用户',
    width: 210,
    render: (row) =>
      h(NSpace, { align: 'center', wrap: false }, {
        default: () => [
          h(NAvatar, { round: true, size: 'small', color: '#dcebe3', textColor: '#195b43' }, {
            default: () => row.display_name.slice(0, 1),
          }),
          h('div', { class: 'user-cell' }, [h('strong', row.display_name), h('small', row.username)]),
        ],
      }),
  },
  { key: 'learner_id', title: '学习者 ID', width: 140, render: (row) => row.learner_id || '--' },
  { key: 'email', title: '邮箱', width: 220, render: (row) => row.email || '--' },
  {
    key: 'roles',
    title: '角色',
    width: 190,
    render: (row) =>
      h(NSpace, { size: 4 }, {
        default: () => (row.roles || []).map((role) => h(NTag, { size: 'small', bordered: false }, { default: () => role })),
      }),
  },
  {
    key: 'is_active',
    title: '状态',
    width: 90,
    render: (row) => h(NTag, { size: 'small', bordered: false, type: row.is_active ? 'success' : 'default' }, {
      default: () => (row.is_active ? '启用' : '停用'),
    }),
  },
  { key: 'last_login_at', title: '最近登录', width: 170, render: (row) => formatDate(row.last_login_at) },
  {
    key: 'actions',
    title: '操作',
    width: 96,
    fixed: 'right',
    render: (row) => h(NSpace, { size: 2, wrap: false }, {
      default: () => [
        iconButton(Pencil, '编辑', () => openEdit(row)),
        iconButton(Trash2, row.id === auth.user?.id ? '不能删除当前账号' : '删除', () => confirmDelete(row), row.id === auth.user?.id),
      ],
    }),
  },
])

async function load(): Promise<void> {
  loading.value = true
  try {
    const [userPage, rolePage] = await Promise.all([
      api.listAdminRecords<AdminUser>('users', page.value, pageSize.value),
      api.listAdminRecords<AdminRecord>('roles', 1, 100),
    ])
    users.value = userPage.items
    total.value = userPage.total
    roleOptions.value = rolePage.items.map((role) => ({
      label: String(role.name || role.code),
      value: String(role.code),
    }))
  } catch (error) {
    message.error(getErrorMessage(error, '用户列表加载失败'))
  } finally {
    loading.value = false
  }
}

function resetForm(user: AdminUser | null): void {
  form.username = user?.username || ''
  form.password = ''
  form.display_name = user?.display_name || ''
  form.email = user?.email || ''
  form.learner_id = user?.learner_id || ''
  form.role_codes = [...(user?.roles || [])]
  form.is_active = user?.is_active ?? true
  form.is_superuser = user?.is_superuser ?? false
  errorText.value = ''
}

function openCreate(): void {
  editing.value = null
  resetForm(null)
  drawerOpen.value = true
}

function openEdit(user: AdminUser): void {
  editing.value = user
  resetForm(user)
  drawerOpen.value = true
}

async function submit(): Promise<void> {
  errorText.value = ''
  if (!form.username.trim() || !form.display_name.trim() || (!editing.value && form.password.length < 8)) {
    errorText.value = editing.value ? '请填写显示名称' : '请填写账号、显示名称和至少 8 位密码'
    return
  }
  const data: JsonRecord = {
    display_name: form.display_name.trim(),
    email: form.email.trim() || null,
    learner_id: form.learner_id.trim() || null,
    role_codes: form.role_codes,
    is_active: form.is_active,
    is_superuser: form.is_superuser,
    ...(form.password ? { password: form.password } : {}),
  }
  saving.value = true
  try {
    if (editing.value) {
      await api.updateAdminUser(editing.value.id, data)
    } else {
      await api.createAdminUser({ username: form.username.trim(), ...data })
    }
    drawerOpen.value = false
    message.success('用户已保存')
    await load()
  } catch (error) {
    errorText.value = getErrorMessage(error, '用户保存失败')
  } finally {
    saving.value = false
  }
}

function confirmDelete(user: AdminUser): void {
  if (user.id === auth.user?.id) return
  dialog.warning({
    title: '删除用户',
    content: `确认删除 ${user.display_name}（${user.username}）？`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await api.deleteAdminUser(user.id)
        message.success('用户已删除')
        await load()
      } catch (error) {
        message.error(getErrorMessage(error, '用户删除失败'))
      }
    },
  })
}

function changePage(value: number): void {
  page.value = value
  void load()
}

onMounted(load)
</script>

<template>
  <div class="admin-users admin-page-standalone">
    <PageHeader title="用户管理" eyebrow="组织权限" :meta="`共 ${total} 个账号`">
      <template #actions>
        <n-button secondary @click="load">
          <template #icon><RefreshCw :size="17" /></template>
          刷新
        </n-button>
        <n-button type="primary" @click="openCreate">
          <template #icon><Plus :size="17" /></template>
          新建用户
        </n-button>
      </template>
    </PageHeader>

    <section class="users-table">
      <n-spin :show="loading">
        <n-data-table
          remote
          :columns="columns"
          :data="users"
          :row-key="(row: AdminUser) => row.id"
          :scroll-x="1120"
          :bordered="false"
          size="small"
        />
      </n-spin>
      <div class="users-pagination">
        <n-pagination :page="page" :page-size="pageSize" :item-count="total" @update:page="changePage" />
      </div>
    </section>

    <n-drawer v-model:show="drawerOpen" placement="right" width="min(520px, 100vw)">
      <n-drawer-content :title="editing ? '编辑用户' : '新建用户'" closable>
        <n-form :model="form" label-placement="top">
          <n-form-item label="账号" required>
            <n-input v-model:value="form.username" :disabled="Boolean(editing)" />
          </n-form-item>
          <n-form-item :label="editing ? '重置密码' : '密码'" :required="!editing">
            <n-input
              v-model:value="form.password"
              type="password"
              show-password-on="mousedown"
              :placeholder="editing ? '留空则不修改' : '至少 8 位'"
              autocomplete="new-password"
            />
          </n-form-item>
          <n-form-item label="显示名称" required><n-input v-model:value="form.display_name" /></n-form-item>
          <n-form-item label="邮箱"><n-input v-model:value="form.email" /></n-form-item>
          <n-form-item label="学习者 ID"><n-input v-model:value="form.learner_id" /></n-form-item>
          <n-form-item label="角色">
            <n-select v-model:value="form.role_codes" multiple :options="roleOptions" />
          </n-form-item>
          <n-form-item label="账号状态"><n-switch v-model:value="form.is_active" /></n-form-item>
          <n-form-item label="超级管理员"><n-switch v-model:value="form.is_superuser" /></n-form-item>
        </n-form>
        <p v-if="errorText" class="form-error">{{ errorText }}</p>
        <template #footer>
          <div class="drawer-footer">
            <n-button @click="drawerOpen = false">取消</n-button>
            <n-button type="primary" :loading="saving" @click="submit">保存</n-button>
          </div>
        </template>
      </n-drawer-content>
    </n-drawer>
  </div>
</template>

<style scoped>
.admin-page-standalone {
  width: 100%;
  max-width: 1680px;
  margin: 0 auto;
  padding: 24px 26px 40px;
}

.users-table {
  overflow: hidden;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 6px;
}

.users-pagination {
  display: flex;
  justify-content: flex-end;
  padding: 14px;
  border-top: 1px solid var(--line);
}

.drawer-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  width: 100%;
}

.form-error {
  color: var(--danger);
  font-size: 12px;
}

:deep(.user-cell) {
  display: grid;
  min-width: 0;
}

:deep(.user-cell strong) {
  color: var(--ink);
  font-size: 13px;
}

:deep(.user-cell small) {
  color: var(--muted);
  font-size: 11px;
}

@media (max-width: 760px) {
  .admin-page-standalone {
    padding: 18px 12px 30px;
  }

  .users-pagination {
    justify-content: flex-start;
    overflow-x: auto;
  }
}
</style>
