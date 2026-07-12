<script setup lang="ts">
import { promptDefinition } from '../../admin/resources'
import AdminResourceView from '../../components/admin/AdminResourceView.vue'
</script>

<template><AdminResourceView :definition="promptDefinition" /></template>
