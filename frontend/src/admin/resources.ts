export type AdminColumnKind = 'text' | 'code' | 'boolean' | 'status' | 'datetime' | 'json'
export type AdminFieldControl = 'text' | 'textarea' | 'number' | 'switch' | 'select' | 'json'

export interface AdminColumnDefinition {
  key: string
  title: string
  width?: number
  kind?: AdminColumnKind
}

export interface AdminFieldDefinition {
  key: string
  label: string
  control: AdminFieldControl
  required?: boolean
  placeholder?: string
  defaultValue?: unknown
  options?: Array<{ label: string; value: string | number }>
}

export interface AdminResourceDefinition {
  resource: string
  title: string
  singular: string
  columns: AdminColumnDefinition[]
  fields: AdminFieldDefinition[]
  readOnly?: boolean
  testable?: boolean
}

export const modelDefinition: AdminResourceDefinition = {
  resource: 'model-configs',
  title: '模型服务',
  singular: '模型配置',
  testable: true,
  columns: [
    { key: 'config_code', title: '配置编码', kind: 'code', width: 150 },
    { key: 'provider', title: '服务协议', width: 150 },
    { key: 'model_name', title: '模型', kind: 'code', width: 180 },
    { key: 'model_type', title: '用途', width: 110 },
    { key: 'base_url', title: 'API 地址', kind: 'code', width: 260 },
    { key: 'is_active', title: '状态', kind: 'boolean', width: 90 },
    { key: 'updated_at', title: '更新时间', kind: 'datetime', width: 170 },
  ],
  fields: [
    { key: 'config_code', label: '配置编码', control: 'text', required: true },
    {
      key: 'provider',
      label: '服务协议',
      control: 'select',
      required: true,
      defaultValue: 'openai_compatible',
      options: [
        { label: 'OpenAI 兼容', value: 'openai_compatible' },
        { label: 'Anthropic 兼容', value: 'anthropic_compatible' },
      ],
    },
    { key: 'model_name', label: '模型 ID', control: 'text', required: true },
    {
      key: 'model_type',
      label: '模型用途',
      control: 'select',
      required: true,
      defaultValue: 'text',
      options: [
        { label: '文本通用', value: 'text' },
        { label: '资源生成', value: 'generation' },
        { label: '内容审核', value: 'review' },
        { label: '视觉识别', value: 'vision' },
      ],
    },
    { key: 'base_url', label: 'API 地址', control: 'text', required: true },
    {
      key: 'credential_reference',
      label: '环境变量引用',
      control: 'text',
      required: true,
      placeholder: 'env:MODEL_API_KEY',
      defaultValue: 'env:MODEL_API_KEY',
    },
    { key: 'timeout_seconds', label: '超时秒数', control: 'number', defaultValue: 60 },
    { key: 'max_retries', label: '重试次数', control: 'number', defaultValue: 1 },
    { key: 'temperature', label: '温度', control: 'number', defaultValue: 0.2 },
    { key: 'extra_json', label: '扩展参数', control: 'json', defaultValue: {} },
    { key: 'is_active', label: '启用', control: 'switch', defaultValue: true },
  ],
}

export const agentDefinition: AdminResourceDefinition = {
  resource: 'agent-configs',
  title: '智能体编排',
  singular: '智能体配置',
  columns: [
    { key: 'agent_code', title: '智能体编码', kind: 'code', width: 170 },
    { key: 'name', title: '名称', width: 160 },
    { key: 'workflow_node', title: '工作流节点', kind: 'code', width: 170 },
    { key: 'model_config_id', title: '模型配置', width: 100 },
    { key: 'prompt_template_id', title: '提示词', width: 90 },
    { key: 'enabled', title: '状态', kind: 'boolean', width: 90 },
    { key: 'updated_at', title: '更新时间', kind: 'datetime', width: 170 },
  ],
  fields: [
    { key: 'agent_code', label: '智能体编码', control: 'text', required: true },
    { key: 'name', label: '名称', control: 'text', required: true },
    { key: 'description', label: '说明', control: 'textarea' },
    { key: 'workflow_node', label: '工作流节点', control: 'text', required: true },
    { key: 'model_config_id', label: '模型配置 ID', control: 'number' },
    { key: 'prompt_template_id', label: '提示词模板 ID', control: 'number' },
    { key: 'timeout_seconds', label: '超时秒数', control: 'number', defaultValue: 30 },
    { key: 'max_retries', label: '重试次数', control: 'number', defaultValue: 1 },
    { key: 'config_json', label: '节点参数', control: 'json', defaultValue: {} },
    { key: 'enabled', label: '启用', control: 'switch', defaultValue: true },
  ],
}

export const promptDefinition: AdminResourceDefinition = {
  resource: 'prompt-templates',
  title: '提示词模板',
  singular: '提示词模板',
  columns: [
    { key: 'template_code', title: '模板编码', kind: 'code', width: 180 },
    { key: 'name', title: '名称', width: 180 },
    { key: 'task_type', title: '任务类型', width: 140 },
    { key: 'version', title: '版本', kind: 'code', width: 90 },
    { key: 'is_active', title: '状态', kind: 'boolean', width: 90 },
    { key: 'updated_at', title: '更新时间', kind: 'datetime', width: 170 },
  ],
  fields: [
    { key: 'template_code', label: '模板编码', control: 'text', required: true },
    { key: 'name', label: '名称', control: 'text', required: true },
    { key: 'task_type', label: '任务类型', control: 'text', required: true },
    { key: 'system_prompt', label: '系统提示词', control: 'textarea', required: true },
    { key: 'user_prompt_template', label: '用户提示词模板', control: 'textarea', required: true },
    { key: 'output_schema_json', label: '输出结构', control: 'json', defaultValue: {} },
    { key: 'version', label: '版本', control: 'text', required: true, defaultValue: 'v1' },
    { key: 'is_active', label: '启用', control: 'switch', defaultValue: true },
  ],
}

export const testCaseDefinition: AdminResourceDefinition = {
  resource: 'test-cases',
  title: '测试用例',
  singular: '测试用例',
  columns: [
    { key: 'case_code', title: '用例编码', kind: 'code', width: 170 },
    { key: 'name', title: '名称', width: 200 },
    { key: 'case_type', title: '类型', width: 130 },
    { key: 'status', title: '状态', kind: 'status', width: 100 },
    { key: 'tags_json', title: '标签', kind: 'json', width: 180 },
    { key: 'updated_at', title: '更新时间', kind: 'datetime', width: 170 },
  ],
  fields: [
    { key: 'case_code', label: '用例编码', control: 'text', required: true },
    { key: 'name', label: '名称', control: 'text', required: true },
    { key: 'case_type', label: '类型', control: 'text', required: true },
    { key: 'input_json', label: '输入数据', control: 'json', required: true, defaultValue: {} },
    { key: 'expected_json', label: '预期结果', control: 'json', required: true, defaultValue: {} },
    { key: 'tags_json', label: '标签', control: 'json', defaultValue: [] },
    {
      key: 'status',
      label: '状态',
      control: 'select',
      defaultValue: 'active',
      options: [
        { label: '启用', value: 'active' },
        { label: '停用', value: 'inactive' },
      ],
    },
  ],
}

export const systemDefinition: AdminResourceDefinition = {
  resource: 'system-configs',
  title: '系统配置',
  singular: '系统配置',
  columns: [
    { key: 'config_key', title: '配置键', kind: 'code', width: 220 },
    { key: 'config_value_json', title: '配置值', kind: 'json', width: 320 },
    { key: 'description', title: '说明', width: 240 },
    { key: 'is_public', title: '公开', kind: 'boolean', width: 90 },
    { key: 'updated_at', title: '更新时间', kind: 'datetime', width: 170 },
  ],
  fields: [
    { key: 'config_key', label: '配置键', control: 'text', required: true },
    { key: 'config_value_json', label: '配置值', control: 'json', required: true, defaultValue: {} },
    { key: 'description', label: '说明', control: 'textarea' },
    { key: 'is_public', label: '公开', control: 'switch', defaultValue: false },
  ],
}

export const roleDefinition: AdminResourceDefinition = {
  resource: 'roles',
  title: '角色',
  singular: '角色',
  columns: [
    { key: 'code', title: '角色编码', kind: 'code', width: 160 },
    { key: 'name', title: '名称', width: 160 },
    { key: 'description', title: '说明', width: 280 },
    { key: 'is_active', title: '状态', kind: 'boolean', width: 90 },
    { key: 'updated_at', title: '更新时间', kind: 'datetime', width: 170 },
  ],
  fields: [
    { key: 'code', label: '角色编码', control: 'text', required: true },
    { key: 'name', label: '名称', control: 'text', required: true },
    { key: 'description', label: '说明', control: 'textarea' },
    { key: 'is_active', label: '启用', control: 'switch', defaultValue: true },
  ],
}

export const menuDefinition: AdminResourceDefinition = {
  resource: 'menus',
  title: '菜单',
  singular: '菜单',
  columns: [
    { key: 'code', title: '菜单编码', kind: 'code', width: 160 },
    { key: 'name', title: '名称', width: 140 },
    { key: 'path', title: '路径', kind: 'code', width: 200 },
    { key: 'permission_code', title: '权限编码', kind: 'code', width: 180 },
    { key: 'sort_order', title: '排序', width: 80 },
    { key: 'is_enabled', title: '状态', kind: 'boolean', width: 90 },
  ],
  fields: [
    { key: 'parent_id', label: '父菜单 ID', control: 'number' },
    { key: 'code', label: '菜单编码', control: 'text', required: true },
    { key: 'name', label: '名称', control: 'text', required: true },
    { key: 'path', label: '路由路径', control: 'text' },
    { key: 'component', label: '组件标识', control: 'text' },
    { key: 'icon', label: '图标', control: 'text' },
    { key: 'sort_order', label: '排序', control: 'number', defaultValue: 0 },
    { key: 'menu_type', label: '菜单类型', control: 'text', defaultValue: 'menu' },
    { key: 'permission_code', label: '权限编码', control: 'text' },
    { key: 'is_visible', label: '可见', control: 'switch', defaultValue: true },
    { key: 'is_enabled', label: '启用', control: 'switch', defaultValue: true },
  ],
}
