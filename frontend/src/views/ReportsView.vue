<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { NAlert, NButton, NEmpty, NSpin, NTag, useMessage } from 'naive-ui'
import { Download, FileChartColumn, FileText, RefreshCw, ScanSearch } from 'lucide-vue-next'
import PageHeader from '../components/PageHeader.vue'
import SourceBadge from '../components/SourceBadge.vue'
import { api } from '../services/api'
import { useAuthStore } from '../stores/auth'
import type { LearnerProfile, LearningPath, ReportRecord, WeakPoint } from '../types/api'
import { downloadBlob, formatDate, getErrorMessage, levelLabels, taskTypeLabels } from '../utils/format'

const auth = useAuthStore()
const message = useMessage()
const loading = ref(false)
const generating = ref(false)
const exportingLearning = ref(false)
const exportingTask = ref(false)
const report = ref<ReportRecord | null>(null)
const taskReport = ref<ReportRecord | null>(null)
const errorText = ref('')

const reportProfile = computed(() => (report.value?.content.profile || null) as LearnerProfile | null)
const reportWeakPoints = computed(() => (report.value?.content.weak_points || []) as unknown as WeakPoint[])
const reportPath = computed(() => (report.value?.content.path || null) as LearningPath | null)
const lastTaskId = computed(() => localStorage.getItem('herbwise.last_task_id') || '')

async function loadReport(): Promise<void> {
  loading.value = true
  errorText.value = ''
  try {
    report.value = await api.getLearningReport(auth.learnerId)
  } catch (error) {
    report.value = null
    const status = (error as { response?: { status?: number } }).response?.status
    if (status !== 404) errorText.value = getErrorMessage(error, '学习报告加载失败')
  } finally {
    loading.value = false
  }
}

async function generateReport(): Promise<void> {
  generating.value = true
  try {
    report.value = await api.generateLearningReport(auth.learnerId)
    message.success('学习报告已生成')
  } catch (error) {
    message.error(getErrorMessage(error, '学习报告生成失败'))
  } finally {
    generating.value = false
  }
}

async function downloadRecord(item: ReportRecord, filename: string): Promise<void> {
  const blob = await api.downloadReport(item.report_id)
  downloadBlob(blob, filename)
}

async function exportLearningReport(): Promise<void> {
  exportingLearning.value = true
  try {
    report.value = await api.exportLearningReport(auth.learnerId)
    await downloadRecord(report.value, `本草智策-学习报告-${auth.learnerId}.docx`)
    message.success('Word 学习报告已导出')
  } catch (error) {
    message.error(getErrorMessage(error, 'Word 报告导出失败'))
  } finally {
    exportingLearning.value = false
  }
}

async function exportRecognitionReport(): Promise<void> {
  if (!lastTaskId.value) {
    message.warning('暂无可导出的辨识任务')
    return
  }
  exportingTask.value = true
  try {
    taskReport.value = await api.exportTaskReport(lastTaskId.value)
    await downloadRecord(taskReport.value, `本草智策-辨识复核-${lastTaskId.value}.docx`)
    message.success('Word 辨识复核报告已导出')
  } catch (error) {
    message.error(getErrorMessage(error, '辨识报告导出失败'))
  } finally {
    exportingTask.value = false
  }
}

onMounted(loadReport)
</script>

<template>
  <div class="page reports-page">
    <PageHeader title="学习报告" :meta="`学习者 ${auth.learnerId}`">
      <template #actions>
        <n-button secondary :loading="loading" @click="loadReport">
          刷新报告
          <template #icon><RefreshCw :size="17" /></template>
        </n-button>
        <n-button type="primary" :loading="generating" @click="generateReport">
          生成报告
          <template #icon><FileChartColumn :size="17" /></template>
        </n-button>
      </template>
    </PageHeader>

    <n-alert v-if="errorText" type="warning" :bordered="false" class="report-alert">{{ errorText }}</n-alert>

    <section class="report-actions-band">
      <div>
        <FileText :size="24" />
        <div>
          <strong>学习报告</strong>
          <span>{{ report ? `更新于 ${formatDate(report.updated_at || report.created_at)}` : '尚未生成' }}</span>
        </div>
        <n-button type="primary" secondary :loading="exportingLearning" @click="exportLearningReport">
          导出 Word
          <template #icon><Download :size="17" /></template>
        </n-button>
      </div>
      <div>
        <ScanSearch :size="24" />
        <div>
          <strong>辨识复核报告</strong>
          <span class="mono">{{ lastTaskId || '暂无任务' }}</span>
        </div>
        <n-button secondary :disabled="!lastTaskId" :loading="exportingTask" @click="exportRecognitionReport">
          导出 Word
          <template #icon><Download :size="17" /></template>
        </n-button>
      </div>
    </section>

    <n-spin :show="loading">
      <template v-if="report">
        <section class="report-title-band">
          <div>
            <span class="eyebrow">{{ report.report_type }}</span>
            <h2>{{ report.title }}</h2>
            <span class="mono">{{ report.report_id }}</span>
          </div>
          <div class="report-title-tags">
            <SourceBadge :source="String(report.content.data_source || 'mock')" :official="report.content.is_official === true" />
            <n-tag type="success" :bordered="false">{{ report.status }}</n-tag>
            <n-tag v-if="report.download_available" type="info" :bordered="false">Word 可下载</n-tag>
          </div>
        </section>

        <section class="page-grid two-column report-grid">
          <div class="surface">
            <div class="surface-header">
              <h2 class="surface-title">学情摘要</h2>
              <span class="report-version">{{ reportProfile?.learner_id || auth.learnerId }}</span>
            </div>
            <div class="surface-body report-profile">
              <div class="profile-report-name">
                <span>{{ reportProfile?.identity_type || '学生' }}</span>
                <strong>{{ reportProfile?.name || auth.user?.display_name || '--' }}</strong>
                <n-tag type="success" :bordered="false">
                  {{ levelLabels[reportProfile?.overall_level || 'basic'] || reportProfile?.overall_level || '--' }}
                </n-tag>
              </div>
              <dl>
                <div><dt>学习目标</dt><dd>{{ reportProfile?.learning_goal || '--' }}</dd></div>
                <div><dt>专业背景</dt><dd>{{ reportProfile?.professional_background || '--' }}</dd></div>
                <div><dt>画像诊断</dt><dd>{{ reportProfile?.diagnosis_summary || '--' }}</dd></div>
              </dl>
            </div>
          </div>

          <div class="surface">
            <div class="surface-header">
              <h2 class="surface-title">学习路径</h2>
              <span class="report-version">V{{ reportPath?.version || '--' }}</span>
            </div>
            <div v-if="reportPath" class="surface-body path-report">
              <div class="path-report-stage">
                <span>当前阶段</span>
                <strong>{{ levelLabels[reportPath.current_stage] || reportPath.current_stage }}</strong>
              </div>
              <div class="path-report-tasks">
                <span>推荐任务</span>
                <div>
                  <n-tag v-for="task in reportPath.path.recommended_task_types || []" :key="task" :bordered="false">
                    {{ taskTypeLabels[task] || task }}
                  </n-tag>
                </div>
              </div>
              <dl>
                <div><dt>路径规则</dt><dd>{{ reportPath.path.rule_version || '--' }}</dd></div>
                <div><dt>生成原因</dt><dd>{{ reportPath.reason || '--' }}</dd></div>
              </dl>
            </div>
            <div v-else class="empty-state"><n-empty description="报告中暂无路径数据" /></div>
          </div>
        </section>

        <section class="surface weak-report-section">
          <div class="surface-header">
            <h2 class="surface-title">薄弱点清单</h2>
            <span class="report-version">{{ reportWeakPoints.length }} 项</span>
          </div>
          <div v-if="reportWeakPoints.length" class="weak-report-list">
            <div v-for="item in reportWeakPoints" :key="`${item.dimension_code}-${item.knowledge_point}`">
              <span class="weak-severity" />
              <div>
                <strong>{{ item.knowledge_point }}</strong>
                <span>{{ item.dimension_code }}</span>
              </div>
              <n-tag type="warning" size="small" :bordered="false">{{ item.severity }}</n-tag>
            </div>
          </div>
          <div v-else class="empty-state"><n-empty description="报告中暂无薄弱点" /></div>
        </section>
      </template>

      <section v-else class="surface empty-report">
        <n-empty description="暂无学习报告">
          <template #extra>
            <n-button type="primary" :loading="generating" @click="generateReport">生成学习报告</n-button>
          </template>
        </n-empty>
      </section>
    </n-spin>
  </div>
</template>

<style scoped>
.report-alert {
  margin-bottom: 18px;
}

.report-actions-band {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 20px;
}

.report-actions-band > div {
  display: grid;
  grid-template-columns: 40px minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
  min-height: 82px;
  padding: 16px 18px;
  background: #fff;
  border: 1px solid var(--line);
}

.report-actions-band svg {
  color: var(--primary);
}

.report-actions-band > div:nth-child(2) svg {
  color: var(--blue);
}

.report-actions-band > div > div {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.report-actions-band strong {
  color: var(--ink);
  font-size: 14px;
}

.report-actions-band span {
  overflow: hidden;
  color: var(--muted);
  font-size: 10px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.report-title-band {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  min-height: 112px;
  padding: 22px 26px;
  background: #eff6f2;
  border-left: 4px solid var(--primary);
}

.report-title-band h2 {
  margin: 4px 0 3px;
  color: var(--ink);
  font-size: 23px;
  font-weight: 700;
}

.report-title-band .mono {
  color: var(--muted);
  font-size: 10px;
}

.report-title-tags {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 7px;
}

.report-grid {
  margin-top: 20px;
}

.report-version {
  color: var(--muted);
  font-size: 11px;
}

.report-profile,
.path-report {
  min-height: 238px;
}

.profile-report-name {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px 12px;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--line);
}

.profile-report-name > span {
  color: var(--muted);
  font-size: 11px;
}

.profile-report-name strong {
  color: var(--ink);
  font-size: 18px;
}

.report-profile dl,
.path-report dl {
  display: grid;
  gap: 9px;
  margin: 16px 0 0;
}

.report-profile dl > div,
.path-report dl > div {
  display: grid;
  grid-template-columns: 90px minmax(0, 1fr);
  gap: 12px;
}

.report-profile dt,
.report-profile dd,
.path-report dt,
.path-report dd {
  margin: 0;
  font-size: 11px;
}

.report-profile dt,
.path-report dt {
  color: var(--muted);
}

.report-profile dd,
.path-report dd {
  color: var(--ink);
  line-height: 1.55;
}

.path-report-stage {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--line);
}

.path-report-stage span,
.path-report-tasks > span {
  color: var(--muted);
  font-size: 11px;
}

.path-report-stage strong {
  color: var(--primary);
  font-size: 19px;
}

.path-report-tasks {
  display: grid;
  gap: 8px;
  margin-top: 14px;
}

.path-report-tasks > div {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}

.weak-report-section {
  margin-top: 20px;
}

.weak-report-list {
  display: grid;
}

.weak-report-list > div {
  display: grid;
  grid-template-columns: 8px minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
  min-height: 60px;
  padding: 10px 18px;
  border-bottom: 1px solid var(--line);
}

.weak-report-list > div:last-child {
  border-bottom: 0;
}

.weak-severity {
  width: 7px;
  height: 27px;
  background: var(--amber);
  border-radius: 3px;
}

.weak-report-list > div > div {
  display: grid;
  gap: 2px;
}

.weak-report-list strong {
  color: var(--ink);
  font-size: 13px;
}

.weak-report-list span {
  color: var(--muted);
  font-size: 10px;
}

.empty-report {
  display: grid;
  min-height: 360px;
  place-items: center;
}

@media (max-width: 820px) {
  .report-actions-band {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 600px) {
  .report-actions-band > div {
    grid-template-columns: 34px minmax(0, 1fr);
  }

  .report-actions-band .n-button {
    grid-column: 1 / -1;
  }

  .report-title-band {
    align-items: flex-start;
    flex-direction: column;
  }

  .report-title-tags {
    justify-content: flex-start;
  }
}
</style>
