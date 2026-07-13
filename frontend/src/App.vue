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

const themeOverrides: GlobalThemeOverrides = {
  common: {
    primaryColor: '#1f6b4f',
    primaryColorHover: '#2b7c5e',
    primaryColorPressed: '#195b43',
    primaryColorSuppl: '#2b7c5e',
    infoColor: '#2f6f8f',
    warningColor: '#bd7a20',
    errorColor: '#b64b42',
    successColor: '#2c7a55',
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
    itemColorActive: '#eaf4ef',
    itemTextColorActive: '#195b43',
    itemIconColorActive: '#195b43',
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
        </n-message-provider>
      </n-notification-provider>
    </n-dialog-provider>
  </n-config-provider>
</template>
