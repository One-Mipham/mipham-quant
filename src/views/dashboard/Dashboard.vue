<template>
  <div>
    <h2 class="text-2xl font-bold mb-6">仪表盘</h2>

    <!-- Market Overview Cards -->
    <a-row :gutter="16" class="mb-6">
      <a-col :span="6" v-for="m in markets" :key="m.name">
        <a-card size="small" hoverable @click="$router.push(`/chart/${m.market}/${m.symbol}`)">
          <div class="flex justify-between items-center">
            <span class="font-medium">{{ m.name }}</span>
            <span :class="m.change >= 0 ? 'text-green-500' : 'text-red-500'">
              {{ m.change >= 0 ? '+' : '' }}{{ m.change }}%
            </span>
          </div>
          <div class="text-lg font-bold mt-1">{{ m.price }}</div>
        </a-card>
      </a-col>
    </a-row>

    <!-- Watchlist Table -->
    <a-card title="自选股" class="mb-6">
      <a-table :columns="columns" :dataSource="watchlist" :loading="loading"
        rowKey="symbol" size="small" :pagination="{pageSize:10}" />
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '@/api/client'

const loading = ref(true)
const watchlist = ref<any[]>([])
const markets = ref([
  { name: '上证指数', market: 'CNStock', symbol: '000001', price: '--', change: 0 },
  { name: '贵州茅台', market: 'CNStock', symbol: '600519', price: '--', change: 0 },
  { name: '腾讯控股', market: 'HKStock', symbol: '00700', price: '--', change: 0 },
  { name: '宁德时代', market: 'CNStock', symbol: '300750', price: '--', change: 0 },
])

const columns = [
  { title: '代码', dataIndex: 'symbol', key: 'symbol' },
  { title: '名称', dataIndex: 'name', key: 'name' },
  { title: '市场', dataIndex: 'market', key: 'market' },
]

onMounted(async () => {
  try {
    const { data } = await api.get('/market/watchlist')
    watchlist.value = data.watchlist || []
  } catch { /* empty watchlist */ }
  loading.value = false
})
</script>
