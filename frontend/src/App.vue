<script setup lang="ts">
import {
  NConfigProvider,
  NDialogProvider,
  NGlobalStyle,
  NMessageProvider,
  NNotificationProvider,
  dateZhCN,
  zhCN,
  type GlobalThemeOverrides,
} from 'naive-ui'
import BenCaoAssistant from './components/BenCaoAssistant.vue'

const themeOverrides: GlobalThemeOverrides = {
  common: {
    primaryColor: '#0b654b',
    primaryColorHover: '#14795a',
    primaryColorPressed: '#074b39',
    primaryColorSuppl: '#14795a',
    infoColor: '#2a6f86',
    warningColor: '#b8812f',
    errorColor: '#b44c43',
    successColor: '#19704f',
    borderRadius: '6px',
    borderRadiusSmall: '4px',
    fontFamily:
      'Inter, "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif',
  },
  Button: {
    borderRadiusMedium: '6px',
    borderRadiusLarge: '6px',
  },
  Card: {
    borderRadius: '8px',
  },
  Drawer: {
    borderRadius: '0px',
  },
  Menu: {
    itemBorderRadius: '6px',
    itemColorActive: '#e6f2ec',
    itemTextColorActive: '#074b39',
    itemIconColorActive: '#074b39',
  },
}
</script>

<template>
  <n-config-provider
    :locale="zhCN"
    :date-locale="dateZhCN"
    :theme-overrides="themeOverrides"
  >
    <n-global-style />
    <n-dialog-provider>
      <n-notification-provider placement="top-right">
        <n-message-provider>
          <router-view />
          <BenCaoAssistant />
        </n-message-provider>
      </n-notification-provider>
    </n-dialog-provider>
  </n-config-provider>
</template>
