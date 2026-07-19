<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import DemoAccessGate from './components/DemoAccessGate.vue'
import AppLayout from './layouts/AppLayout.vue'
import {
  DEMO_ACCESS_REVOKED_EVENT,
  isDemoAccessRequired,
} from './utils/demoAccess'

const accessRequired = isDemoAccessRequired()
const accessGranted = ref(!accessRequired)

function grantAccess() {
  accessGranted.value = true
}

function revokeAccess() {
  if (accessRequired) accessGranted.value = false
}

onMounted(() => {
  window.addEventListener(DEMO_ACCESS_REVOKED_EVENT, revokeAccess)
})

onBeforeUnmount(() => {
  window.removeEventListener(DEMO_ACCESS_REVOKED_EVENT, revokeAccess)
})
</script>

<template>
  <DemoAccessGate v-if="accessRequired && !accessGranted" @granted="grantAccess" />
  <div v-else class="app-root">
    <aside class="demo-environment-notice" role="note">
      受控演示环境：数据使用临时共享存储，可能被其他获授权访客看到，也可能在服务重启后丢失。请仅输入脱敏或虚构内容。授权生成面试准备后，相关内容会发送给外部大模型服务。
    </aside>
    <AppLayout />
  </div>
</template>
