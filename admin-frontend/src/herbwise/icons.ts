import { Icon } from '@iconify/vue';
import { defineComponent, h } from 'vue';

function createIcon(name: string) {
  return defineComponent({
    name: `HerbwiseIcon${name}`,
    inheritAttrs: false,
    props: {
      size: {
        type: [Number, String],
        default: 18
      }
    },
    setup(props, { attrs }) {
      return () => h(Icon, { ...attrs, icon: name, width: props.size, height: props.size });
    }
  });
}

export const Pencil = createIcon('ph:pencil-simple');
export const Plus = createIcon('ph:plus');
export const RefreshCw = createIcon('ph:arrows-clockwise');
export const TestTube2 = createIcon('ph:test-tube');
export const Trash2 = createIcon('ph:trash');
export const Bot = createIcon('ph:robot');
export const BrainCircuit = createIcon('ph:brain');
export const CheckCircle2 = createIcon('ph:check-circle');
export const Database = createIcon('ph:database');
export const FileStack = createIcon('ph:files');
export const ListChecks = createIcon('ph:list-checks');
