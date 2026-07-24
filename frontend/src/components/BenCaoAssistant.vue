<template>
  <teleport to="body">
    <transition name="assistant-slide">
      <section v-if="isOpen" class="bencao-panel" :class="{ 'login-route': route.name === 'login' }">
        <header class="assistant-header">
          <div class="assistant-title">
            <span class="assistant-seal">本草</span>
            <div>
              <h3>本草智问</h3>
              <p>中药鉴别 · 方剂配伍 · 质控溯源</p>
            </div>
          </div>
          <button class="close-btn" type="button" aria-label="关闭本草智问" @click="isOpen = false">×</button>
        </header>

        <div class="online-row">
          <i></i>
          <span>智能助手在线</span>
        </div>

        <main ref="messageBoxRef" class="message-box">
          <article v-for="message in messages" :key="message.id" class="message-item" :class="message.role">
            <div class="message-bubble">{{ message.content }}</div>
          </article>
          <article v-if="isThinking" class="message-item assistant">
            <div class="message-bubble thinking">正在分析...</div>
          </article>
        </main>

        <div class="quick-area">
          <button v-for="question in quickQuestions" :key="question" type="button" @click="sendQuestion(question)">
            {{ question }}
          </button>
        </div>

        <footer class="input-area">
          <textarea
            v-model="inputText"
            rows="1"
            placeholder="请输入中药鉴别、方剂配伍或平台使用问题"
            @keydown.enter.exact.prevent="sendQuestion()"
          ></textarea>
          <button type="button" @click="sendQuestion()">发送</button>
        </footer>
      </section>
    </transition>

    <button
      class="bencao-float"
      :class="{ 'login-route': route.name === 'login' }"
      type="button"
      aria-label="打开本草智问"
      @click="isOpen = !isOpen"
    >
      <span class="float-halo"></span>
      <span class="float-icon">
        <TcmIcon name="assistant" size="sm" theme="dark" />
      </span>
      <span class="float-copy">
        <b>本草智问</b>
        <small><i></i> 在线</small>
      </span>
    </button>
  </teleport>
</template>

<script setup lang="ts">
import { nextTick, ref } from 'vue';
import { useRoute } from 'vue-router';
import TcmIcon from './TcmIcon.vue';

type MessageRole = 'assistant' | 'user';

interface ChatMessage {
  id: number;
  role: MessageRole;
  content: string;
}

const isOpen = ref(false);
const isThinking = ref(false);
const inputText = ref('');
const messageBoxRef = ref<HTMLElement>();
const route = useRoute();
let messageId = 1;

const quickQuestions = [
  '如何上传中药图片进行识别？',
  '如何查看批次质控溯源？',
  '黄芪和党参如何区分？',
  '方剂配伍分析怎么使用？',
];

const messages = ref<ChatMessage[]>([
  {
    id: messageId++,
    role: 'assistant',
    content: '您好，我是本草智问助手，可为您提供中药鉴别、方剂配伍、质控溯源和平台操作指引。您可以直接输入问题，也可以点击下方快捷问题开始。',
  },
]);

const scrollToBottom = () => {
  nextTick(() => {
    if (!messageBoxRef.value) return;
    messageBoxRef.value.scrollTop = messageBoxRef.value.scrollHeight;
  });
};

const getMockAnswer = (question: string) => {
  if (/[上传图片识别]/.test(question) || question.includes('上传') || question.includes('图片') || question.includes('识别')) {
    return '您可以进入“多模态本草智鉴终端”，上传中药图片后选择识别模型，系统会输出药材名称、置信度、性状特征和风险提示。';
  }
  if (question.includes('视频') || question.includes('巡检') || question.includes('动态')) {
    return '您可以进入“动态本草智鉴”，在“视频流识别”中上传检测视频，或在“实时巡检识别”中调用摄像头进行连续识别。';
  }
  if (question.includes('溯源') || question.includes('质控') || question.includes('批次')) {
    return '您可以进入“质控溯源中心”，查看批次编号、药材产地、供应商、识别置信度、风险等级和复核建议，形成完整证据链。';
  }
  if (question.includes('方剂') || question.includes('配伍')) {
    return '您可以进入“方剂配伍智能体”，输入药材组成、剂量和适应症，系统会辅助分析君臣佐使结构、功效方向和风险禁忌。';
  }
  if (question.includes('黄芪') || question.includes('党参')) {
    return '黄芪多呈类圆形或椭圆形厚片，外皮黄白色，断面纤维性较强；党参断面常有放射状纹理，质地较柔韧。实际鉴别需结合性状、气味、断面纹理与批次信息综合判断。';
  }
  return '我可以辅助解答中药识别、方剂配伍、质控溯源和平台使用相关问题。您可以尝试询问某味药材的鉴别方法，或询问某个功能如何使用。';
};

const sendQuestion = (preset?: string) => {
  const question = (preset ?? inputText.value).trim();
  if (!question || isThinking.value) return;
  if (!isOpen.value) isOpen.value = true;
  messages.value.push({ id: messageId++, role: 'user', content: question });
  inputText.value = '';
  isThinking.value = true;
  scrollToBottom();

  window.setTimeout(() => {
    messages.value.push({ id: messageId++, role: 'assistant', content: getMockAnswer(question) });
    isThinking.value = false;
    scrollToBottom();
  }, 460);
};
</script>

<style scoped>
.bencao-float {
  position: fixed;
  right: 28px;
  bottom: 28px;
  z-index: 3000;
  display: inline-flex;
  align-items: center;
  gap: 12px;
  min-height: 58px;
  padding: 10px 18px 10px 12px;
  border: 1px solid rgba(239, 211, 147, 0.34);
  border-radius: 999px;
  color: #f7fbf8;
  cursor: pointer;
  background:
    radial-gradient(circle at 12% 18%, rgba(239, 211, 147, 0.24), transparent 34%),
    linear-gradient(135deg, rgba(13, 88, 64, 0.96), rgba(3, 38, 31, 0.96));
  box-shadow: 0 20px 48px rgba(3, 38, 31, 0.28);
  backdrop-filter: blur(18px);
  transition: transform 220ms cubic-bezier(0.22, 1, 0.36, 1), box-shadow 220ms cubic-bezier(0.22, 1, 0.36, 1);
}

.bencao-float:hover {
  transform: translateY(-3px);
  box-shadow: 0 26px 66px rgba(3, 38, 31, 0.36);
}

.float-halo {
  position: absolute;
  inset: -7px;
  border-radius: inherit;
  border: 1px solid rgba(239, 211, 147, 0.28);
  animation: assistantPulse 2.8s ease-in-out infinite;
  pointer-events: none;
}

.float-icon {
  position: relative;
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.08);
  box-shadow: inset 0 0 0 1px rgba(246, 216, 138, 0.18), 0 0 22px rgba(143, 214, 192, 0.14);
}

.float-copy {
  display: grid;
  gap: 2px;
  text-align: left;
}

.float-copy b {
  font-size: 14px;
  letter-spacing: 0.04em;
}

.float-copy small {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: rgba(247, 251, 248, 0.76);
  font-size: 11px;
}

.float-copy small i,
.online-row i {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #8fd67f;
  box-shadow: 0 0 0 5px rgba(143, 214, 127, 0.14);
}

.bencao-panel {
  position: fixed;
  right: 28px;
  bottom: 96px;
  z-index: 2999;
  display: flex;
  flex-direction: column;
  width: min(420px, calc(100vw - 32px));
  height: calc(100vh - 120px);
  max-height: 760px;
  overflow: hidden;
  border: 1px solid rgba(19, 94, 70, 0.14);
  border-radius: 24px;
  background:
    radial-gradient(circle at 100% 0, rgba(239, 211, 147, 0.18), transparent 32%),
    rgba(245, 250, 247, 0.92);
  box-shadow: 0 28px 80px rgba(6, 42, 34, 0.22);
  backdrop-filter: blur(18px);
}

.assistant-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 18px 18px 12px;
  border-bottom: 1px solid rgba(19, 94, 70, 0.1);
}

.assistant-title {
  display: flex;
  align-items: center;
  gap: 12px;
}

.assistant-seal {
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  border-radius: 15px;
  color: #f6e7be;
  background: linear-gradient(135deg, #0e5e45, #062b23);
  box-shadow: inset 0 0 0 1px rgba(246, 231, 190, 0.25);
  font-size: 12px;
  font-weight: 900;
}

.assistant-title h3 {
  margin: 0;
  color: #064e3b;
  font-size: 18px;
  font-weight: 900;
}

.assistant-title p {
  margin: 4px 0 0;
  color: #6b8178;
  font-size: 12px;
  font-weight: 700;
}

.close-btn {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border: 0;
  border-radius: 50%;
  color: #0f4a38;
  cursor: pointer;
  background: rgba(19, 121, 85, 0.08);
  font-size: 22px;
  line-height: 1;
}

.online-row {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin: 12px 18px 0;
  padding: 7px 11px;
  border-radius: 999px;
  color: #2f7762;
  background: rgba(19, 121, 85, 0.08);
  font-size: 12px;
  font-weight: 800;
}

.message-box {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 0;
  padding: 16px 18px;
  overflow-y: auto;
}

.message-item {
  display: flex;
}

.message-item.user {
  justify-content: flex-end;
}

.message-bubble {
  max-width: 82%;
  padding: 12px 14px;
  border-radius: 18px;
  color: #395047;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(19, 94, 70, 0.09);
  line-height: 1.72;
  font-size: 13px;
  box-shadow: 0 10px 28px rgba(6, 78, 59, 0.06);
  white-space: pre-wrap;
}

.message-item.user .message-bubble {
  color: #f5fbf7;
  background: linear-gradient(135deg, #167255, #064e3b);
  border-color: rgba(255, 255, 255, 0.12);
}

.thinking {
  color: #6b8178;
}

.quick-area {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 0 18px 14px;
}

.quick-area button {
  border: 1px solid rgba(19, 94, 70, 0.12);
  border-radius: 999px;
  padding: 7px 10px;
  color: #0f4a38;
  cursor: pointer;
  background: rgba(255, 255, 255, 0.72);
  font-size: 12px;
  font-weight: 800;
  transition: transform 180ms ease, background 180ms ease;
}

.quick-area button:hover {
  transform: translateY(-1px);
  background: rgba(19, 121, 85, 0.08);
}

.input-area {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 74px;
  gap: 10px;
  padding: 14px 18px 18px;
  border-top: 1px solid rgba(19, 94, 70, 0.1);
}

.input-area textarea {
  width: 100%;
  min-height: 42px;
  max-height: 94px;
  padding: 11px 13px;
  border: 1px solid rgba(19, 94, 70, 0.12);
  border-radius: 18px;
  outline: none;
  resize: none;
  color: #0f342b;
  background: rgba(255, 255, 255, 0.84);
  box-sizing: border-box;
  font-family: inherit;
  line-height: 1.5;
}

.input-area textarea:focus {
  border-color: rgba(47, 143, 104, 0.58);
  box-shadow: 0 0 0 4px rgba(47, 143, 104, 0.12);
}

.input-area button {
  border: 0;
  border-radius: 999px;
  color: #fff;
  cursor: pointer;
  background: linear-gradient(135deg, #2f8f68, #064e3b);
  font-weight: 900;
  box-shadow: 0 12px 24px rgba(6, 78, 59, 0.18);
}

.assistant-slide-enter-active,
.assistant-slide-leave-active {
  transition: opacity 220ms ease, transform 220ms cubic-bezier(0.22, 1, 0.36, 1);
}

.assistant-slide-enter-from,
.assistant-slide-leave-to {
  opacity: 0;
  transform: translateX(18px) translateY(8px);
}

@keyframes assistantPulse {
  0%, 100% {
    opacity: 0.55;
    transform: scale(1);
  }
  50% {
    opacity: 0.95;
    transform: scale(1.06);
  }
}

@media (max-width: 640px) {
  .bencao-panel.login-route,
  .bencao-float.login-route {
    display: none;
  }

  .bencao-panel {
    right: 16px;
    bottom: 88px;
    height: min(680px, calc(100vh - 110px));
  }

  .bencao-float {
    right: 16px;
    bottom: 12px;
    width: 52px;
    min-height: 52px;
    padding: 5px;
    border-radius: 50%;
  }

  .float-copy {
    display: none;
  }

  .float-icon {
    width: 40px;
    height: 40px;
  }
}
</style>
