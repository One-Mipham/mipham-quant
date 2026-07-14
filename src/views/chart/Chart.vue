<template>
  <div>
    <a-space class="mb-4">
      <a-select v-model:value="market" style="width:120px" @change="loadChart">
        <a-select-option value="CNStock">A股</a-select-option>
        <a-select-option value="HKStock">港股</a-select-option>
        <a-select-option value="Crypto">加密</a-select-option>
        <a-select-option value="USStock">美股</a-select-option>
      </a-select>
      <a-input v-model:value="symbol" placeholder="股票代码" style="width:160px" />
      <a-select v-model:value="timeframe" style="width:100px">
        <a-select-option value="1D">日线</a-select-option>
        <a-select-option value="1W">周线</a-select-option>
        <a-select-option value="4H">4小时</a-select-option>
        <a-select-option value="1H">1小时</a-select-option>
      </a-select>
      <a-button type="primary" @click="loadChart">查询</a-button>
      <a-button @click="addWatchlist">加自选</a-button>
    </a-space>

    <div ref="chartRef" class="w-full" style="height:500px" />

    <a-card title="实时行情" class="mt-4" v-if="ticker">
      <a-descriptions :column="4" size="small">
        <a-descriptions-item label="最新价">{{ ticker.last }}</a-descriptions-item>
        <a-descriptions-item label="涨跌">{{ ticker.change }}</a-descriptions-item>
        <a-descriptions-item label="涨跌幅">{{ ticker.changePercent }}%</a-descriptions-item>
        <a-descriptions-item label="成交量">{{ ticker.volume || '--' }}</a-descriptions-item>
        <a-descriptions-item label="最高">{{ ticker.high }}</a-descriptions-item>
        <a-descriptions-item label="最低">{{ ticker.low }}</a-descriptions-item>
        <a-descriptions-item label="开盘">{{ ticker.open }}</a-descriptions-item>
        <a-descriptions-item label="昨收">{{ ticker.previousClose }}</a-descriptions-item>
      </a-descriptions>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import * as echarts from 'echarts'
import api from '@/api/client'

const route = useRoute()
const market = ref((route.params.market as string) || 'CNStock')
const symbol = ref((route.params.symbol as string) || '600519')
const timeframe = ref('1D')
const chartRef = ref<HTMLElement>()
const ticker = ref<any>(null)
let chart: echarts.ECharts | null = null

async function loadChart() {
  const { data } = await api.get('/kline', { params: { market: market.value, symbol: symbol.value, timeframe: timeframe.value, limit: 200 } })
  const klines = data.klines || data.data || []
  // Update ticker
  try {
    const { data: t } = await api.get('/market/ticker', { params: { market: market.value, symbol: symbol.value } })
    ticker.value = t.ticker || t
  } catch { /* ignore */ }

  if (!chart && chartRef.value) chart = echarts.init(chartRef.value)
  if (!chart) return

  const dates = klines.map((k: any) => new Date(k.time * 1000).toLocaleDateString('zh-CN'))
  const ohlc = klines.map((k: any) => [k.open, k.close, k.low, k.high])
  const volumes = klines.map((k: any) => k.volume)

  chart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
    grid: [{ left: '10%', right: '8%', top: '5%', height: '60%' }],
    xAxis: [{ type: 'category', data: dates, boundaryGap: true }],
    yAxis: [{ type: 'value', scale: true }, { type: 'value', scale: true }],
    series: [
      { name: 'K线', type: 'candlestick', data: ohlc },
    ],
  })
}

function addWatchlist() {
  api.post('/market/watchlist', { market: market.value, symbol: symbol.value })
}

onMounted(loadChart)
</script>
