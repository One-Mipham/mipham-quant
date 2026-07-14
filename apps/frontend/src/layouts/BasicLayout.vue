<template>
  <a-layout class="min-h-screen">
    <a-layout-sider v-model:collapsed="collapsed" breakpoint="lg" collapsible
      style="background:#001529;">
      <div class="text-white text-center py-4 text-lg font-bold cursor-pointer"
        @click="$router.push('/')">
        <span v-if="!collapsed">Mipham Quant</span>
        <span v-else class="text-sm">MQ</span>
      </div>
      <a-menu v-model:selectedKeys="selectedKeys" theme="dark" mode="inline"
        @click="({key}: any) => $router.push(key)">
        <a-menu-item key="/">
          <dashboard-outlined /> <span>仪表盘</span>
        </a-menu-item>
        <a-menu-item key="/chart">
          <line-chart-outlined /> <span>K线图</span>
        </a-menu-item>
        <a-menu-item key="/strategy">
          <code-outlined /> <span>策略</span>
        </a-menu-item>
        <a-menu-item key="/backtest">
          <fund-outlined /> <span>回测</span>
        </a-menu-item>
        <a-menu-item key="/news">
          <bulb-outlined /> <span>快讯</span>
        </a-menu-item>
      </a-menu>
    </a-layout-sider>

    <a-layout>
      <a-layout-header style="background:#fff; padding:0 24px; display:flex;
        justify-content:flex-end; align-items:center; border-bottom:1px solid #f0f0f0;">
        <a-space>
          <a-avatar :src="auth.user?.avatar || '/avatar2.jpg'" size="small" />
          <span>{{ auth.user?.nickname || auth.user?.username || '未登录' }}</span>
          <a-button type="link" @click="auth.logout()">退出</a-button>
        </a-space>
      </a-layout-header>

      <a-layout-content style="margin:16px; padding:24px; background:#fff; min-height:360px;">
        <router-view />
      </a-layout-content>

      <a-layout-footer style="text-align:center;">
        Mipham Quant Desktop v1.0.0 ©2026 One Mipham Corporation
      </a-layout-footer>
    </a-layout>
  </a-layout>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import {
  DashboardOutlined, LineChartOutlined, CodeOutlined,
  FundOutlined, BulbOutlined,
} from '@ant-design/icons-vue'

const auth = useAuthStore()
const route = useRoute()
const collapsed = ref(false)
const selectedKeys = computed(() => [route.path])
</script>
