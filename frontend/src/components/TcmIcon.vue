<template>
  <span class="tcm-illustration-icon" :class="[`theme-${theme}`, `size-${size}`]">
    <svg viewBox="0 0 96 96" role="img" aria-hidden="true">
      <defs>
        <linearGradient :id="gradId" x1="18" x2="82" y1="12" y2="88">
          <stop offset="0" stop-color="#fff6d8" />
          <stop offset="0.52" stop-color="#f4dfaa" />
          <stop offset="1" stop-color="#d7ae62" />
        </linearGradient>
        <linearGradient :id="jadeId" x1="14" x2="82" y1="16" y2="82">
          <stop offset="0" stop-color="#1f7a5a" />
          <stop offset="1" stop-color="#0b4f3d" />
        </linearGradient>
      </defs>

      <circle class="wash" cx="48" cy="48" r="41" />
      <path class="cloud cloud-a" d="M16 66c8-8 15-3 18 2 4-7 14-7 19 0" />
      <path class="leaf leaf-a" d="M72 26c-12 1-20 8-23 19 12-1 20-8 23-19Z" />
      <path class="leaf leaf-b" d="M79 46c-9 1-15 6-17 14 9-1 15-6 17-14Z" />

      <g v-if="is('intro', 'scroll', 'syndrome', 'classic')" class="motif">
        <path d="M25 27h42c5 0 8 3 8 8v31H28c-5 0-8-3-8-8V33c0-3 2-6 5-6Z" fill="#f8ecd0" />
        <path d="M28 31h38v31H29c-3 0-5-2-5-5V35c0-2 2-4 4-4Z" />
        <path d="M35 39h24M35 47h18M35 55h25" />
        <circle cx="61" cy="48" r="11" fill="none" />
        <path v-if="is('intro', 'reasoning')" d="M61 37c-5 2-6 6-2 10 5 4 4 9-2 12" />
        <path v-if="is('classic')" d="M68 30v30M64 35h8M64 44h8M64 53h8" />
      </g>

      <g v-else-if="is('basic', 'study')" class="motif">
        <path d="M20 31c12-6 22-4 30 3 9-7 18-8 29-3v39c-11-5-21-4-29 3-8-7-18-8-30-3V31Z" fill="#f8ecd0" />
        <path d="M50 34v38M28 41h14M28 49h13M58 41h14M58 49h13" />
        <path v-if="is('study')" d="M74 18 82 26 62 58l-10 4 4-10 18-34Z" fill="#f3dfaa" />
      </g>

      <g v-else-if="is('acupoint', 'constitution')" class="motif">
        <path d="M48 18c8 0 13 6 13 14 0 7-4 11-8 14v11l15 16H28l15-16V46c-4-3-8-7-8-14 0-8 5-14 13-14Z" fill="#f8ecd0" />
        <path d="M48 35v30M36 47c7 3 17 3 24 0" />
        <circle cx="48" cy="35" r="3" />
        <circle cx="42" cy="48" r="3" />
        <circle cx="54" cy="48" r="3" />
        <circle cx="48" cy="61" r="3" />
        <path v-if="is('constitution')" d="M22 49c8-16 43-22 56 0M26 63c12 13 31 13 44 0" />
      </g>

      <g v-else-if="is('diagnosis', 'massage')" class="motif">
        <path d="M30 58c7 3 15 4 24 3l16-19c4-5 10 0 6 6L58 72c-10 4-21 3-33-3-4-2-5-7-2-10 2-2 5-2 7-1Z" fill="#f8ecd0" />
        <path d="M31 57 46 33c3-5 10-1 7 5L43 58" />
        <path d="M43 58 61 30c3-5 10 0 7 5L55 61" />
        <path v-if="is('diagnosis')" d="M23 73c12 5 27 7 43 3" />
      </g>

      <g v-else-if="is('therapy', 'moxa')" class="motif">
        <rect x="39" y="39" width="18" height="28" rx="6" fill="#f8ecd0" />
        <path d="M37 68h22M44 39v-9M52 39v-9" />
        <path d="M43 27c-9-8 7-10 0-18M53 28c9-8-7-11 1-19" />
        <path v-if="is('moxa')" d="M28 72c10 7 30 7 40 0" />
      </g>

      <g v-else-if="is('herb', 'materiaMedica', 'root')" class="motif">
        <path d="M48 72c-5-16-3-31 7-46" />
        <path d="M51 43c-15 1-24-6-27-18 15-1 24 6 27 18Z" fill="#f8ecd0" />
        <path d="M54 50c14-1 23 5 27 17-14 1-23-5-27-17Z" fill="#f8ecd0" />
        <path d="M47 71c-7 1-13 6-17 13M49 72c6 1 11 5 15 12" />
      </g>

      <g v-else-if="is('risk')" class="motif">
        <path d="M48 19 75 29v18c0 17-10 29-27 36-17-7-27-19-27-36V29l27-10Z" fill="#f8ecd0" />
        <path d="M36 51 45 60 62 38" />
      </g>

      <g v-else-if="is('sleep')" class="motif">
        <path d="M59 20c-16 5-25 24-17 39 6 12 20 16 32 10-8 12-25 17-39 9-15-9-20-28-10-43 7-10 20-17 34-15Z" fill="#f8ecd0" />
        <path d="M62 34h10M67 29v10" />
      </g>

      <g v-else-if="is('food', 'formula')" class="motif">
        <path d="M25 52h46c-2 17-11 27-23 27S27 69 25 52Z" fill="#f8ecd0" />
        <path d="M22 52h52M60 26c-8 8-3 14-10 20M48 24c-8 8-2 13-9 20" />
        <circle cx="40" cy="58" r="4" fill="#d7ae62" />
        <circle cx="50" cy="59" r="4" fill="#d7ae62" />
        <path v-if="is('formula')" d="M30 42c6-12 25-15 35-5" />
      </g>

      <g v-else-if="is('exercise', 'taiji', 'reasoning')" class="motif">
        <circle cx="48" cy="48" r="25" fill="#f8ecd0" />
        <path d="M48 23c15 6 15 22 0 25-15 3-15 19 0 25" />
        <circle cx="48" cy="36" r="4" fill="#0b5a43" />
        <circle cx="48" cy="60" r="4" fill="#f8ecd0" />
        <path d="M21 48c8-22 42-31 58-5" />
      </g>

      <g v-else-if="is('emotion')" class="motif">
        <path d="M48 67c-12-7-21-16-23-30 11 1 18 7 23 19 5-12 12-18 23-19-2 14-11 23-23 30Z" fill="#f8ecd0" />
        <path d="M29 70c10 7 28 7 38 0M26 54c-10-9 5-12 0-22M70 54c10-9-5-12 0-22" />
      </g>

      <g v-else-if="is('acupuncture', 'needle')" class="motif">
        <path d="M52 17v52M48 17h8M45 69h14" />
        <path d="M37 77c7-8 15-8 22 0" />
        <circle cx="52" cy="32" r="4" />
        <circle cx="52" cy="48" r="4" />
      </g>

      <g v-else-if="is('research')" class="motif">
        <path d="M25 27h35v43H25V27Z" fill="#f8ecd0" />
        <path d="M33 39h18M33 48h15M33 57h22" />
        <circle cx="62" cy="58" r="13" fill="none" />
        <path d="M72 68 82 78M34 64l7-8 7 5 8-13" />
      </g>

      <g v-else-if="is('collect', 'identify', 'explain', 'warning', 'archive', 'screen', 'trace', 'lab', 'assistant')" class="motif">
        <path v-if="is('collect')" d="M24 31h48v36H24V31Z" fill="#f8ecd0" />
        <path v-if="is('collect')" d="M34 48h28M48 34v28" />
        <path v-if="is('identify')" d="M23 48c12-15 38-15 50 0-12 15-38 15-50 0Z" fill="#f8ecd0" />
        <circle v-if="is('identify')" cx="48" cy="48" r="10" />
        <path v-if="is('explain')" d="M28 25h40v40H46L35 76V65h-7V25Z" fill="#f8ecd0" />
        <path v-if="is('explain')" d="M36 38h24M36 48h18" />
        <path v-if="is('warning')" d="M48 20 77 72H19L48 20Z" fill="#f8ecd0" />
        <path v-if="is('warning')" d="M48 37v17M48 63v2" />
        <path v-if="is('archive')" d="M24 33h48v40H24V33Z" fill="#f8ecd0" />
        <path v-if="is('archive')" d="M24 33l8-10h32l8 10M37 51h22" />
        <path v-if="is('screen')" d="M22 28h52v34H22V28Z" fill="#f8ecd0" />
        <path v-if="is('screen')" d="M34 70h28M48 62v8M32 52l9-10 8 6 12-15" />
        <path v-if="is('trace')" d="M24 49h48M30 35c8 0 8 28 16 28s8-28 16-28" />
        <circle v-if="is('trace')" cx="24" cy="49" r="5" fill="#f8ecd0" />
        <circle v-if="is('trace')" cx="72" cy="49" r="5" fill="#f8ecd0" />
        <path v-if="is('lab')" d="M33 24h30v14l13 31c2 5-1 9-6 9H26c-5 0-8-4-6-9l13-31V24Z" fill="#f8ecd0" />
        <path v-if="is('lab')" d="M34 51h28M39 24h18" />
        <path v-if="is('assistant')" d="M48 72c-12-8-21-17-23-31 11 1 18 7 23 18 5-11 12-17 23-18-2 14-11 23-23 31Z" fill="#f8ecd0" />
      </g>

      <g v-else class="motif">
        <path d="M48 72c-7-15-6-31 2-48" />
        <path d="M51 44c-13 1-22-5-26-17 13-1 22 5 26 17Z" fill="#f8ecd0" />
        <path d="M53 51c12-1 20 5 24 16-12 1-20-5-24-16Z" fill="#f8ecd0" />
      </g>
    </svg>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue';

const props = withDefaults(defineProps<{
  name?: string;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  theme?: 'light' | 'dark' | 'plain';
}>(), {
  name: 'herb',
  size: 'md',
  theme: 'light',
});

const gradId = computed(() => `tcmGold-${props.name}`);
const jadeId = computed(() => `tcmJade-${props.name}`);
const is = (...names: string[]) => names.includes(props.name);
</script>

<style scoped>
.tcm-illustration-icon {
  display: inline-grid;
  place-items: center;
  flex: none;
  border-radius: 22px;
  color: #123f32;
  background:
    radial-gradient(circle at 72% 20%, rgba(246, 216, 138, 0.36), transparent 34%),
    linear-gradient(145deg, rgba(255, 247, 224, 0.98), rgba(231, 244, 237, 0.94));
  border: 1px solid rgba(224, 184, 92, 0.34);
  box-shadow: 0 12px 26px rgba(7, 60, 46, 0.12), inset 0 1px 0 rgba(255, 255, 255, 0.72);
  transition: transform 220ms ease, box-shadow 220ms ease, border-color 220ms ease;
}

.tcm-illustration-icon:hover {
  transform: translateY(-3px);
  border-color: rgba(246, 216, 138, 0.6);
  box-shadow: 0 18px 36px rgba(7, 60, 46, 0.18), 0 0 24px rgba(246, 216, 138, 0.16);
}

.size-sm {
  width: 34px;
  height: 34px;
  border-radius: 12px;
}

.size-md {
  width: 48px;
  height: 48px;
  border-radius: 16px;
}

.size-lg {
  width: 62px;
  height: 62px;
}

.size-xl {
  width: 86px;
  height: 86px;
  border-radius: 28px;
}

svg {
  width: 82%;
  height: 82%;
  overflow: visible;
}

.wash {
  fill: rgba(15, 107, 79, 0.08);
  stroke: rgba(18, 63, 50, 0.18);
  stroke-width: 1.2;
}

.motif {
  fill: none;
  stroke: currentColor;
  stroke-width: 3.2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.motif [fill="#f8ecd0"] {
  stroke: rgba(18, 63, 50, 0.9);
}

.leaf {
  fill: rgba(31, 122, 90, 0.68);
  stroke: rgba(18, 63, 50, 0.65);
  stroke-width: 1.5;
}

.leaf-b {
  fill: rgba(111, 174, 114, 0.5);
}

.cloud {
  fill: none;
  stroke: rgba(181, 139, 74, 0.42);
  stroke-width: 2.2;
  stroke-linecap: round;
}

.theme-dark {
  color: #fff2bd;
  background:
    radial-gradient(circle at 72% 16%, rgba(246, 216, 138, 0.2), transparent 34%),
    linear-gradient(145deg, rgba(255, 255, 255, 0.12), rgba(255, 255, 255, 0.04));
  border-color: rgba(246, 216, 138, 0.26);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.14), 0 16px 32px rgba(0, 0, 0, 0.18);

}

.theme-dark .wash {
  fill: rgba(157, 234, 203, 0.08);
  stroke: rgba(246, 216, 138, 0.22);
}

.theme-dark .motif [fill="#f8ecd0"] {
  stroke: rgba(255, 242, 189, 0.92);
}

.theme-plain {
  background: transparent;
  border-color: transparent;
  box-shadow: none;
}
</style>
