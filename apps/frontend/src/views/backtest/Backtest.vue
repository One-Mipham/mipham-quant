<template>
  <div>
    <h2 class="text-2xl font-bold mb-4">回测</h2>
    <a-card>
      <a-form layout="inline" class="mb-4">
        <a-form-item label="市场"><a-select v-model:value="form.market" style="width:100px">
          <a-select-option value="CNStock">A股</a-select-option>
          <a-select-option value="HKStock">港股</a-select-option>
        </a-select></a-form-item>
        <a-form-item label="代码"><a-input v-model:value="form.symbol" style="width:120px" /></a-form-item>
        <a-form-item label="周期"><a-select v-model:value="form.timeframe" style="width:80px">
          <a-select-option value="1D">日线</a-select-option>
          <a-select-option value="1W">周线</a-select-option>
        </a-select></a-form-item>
        <a-form-item label="起始资金"><a-input-number v-model:value="form.capital" style="width:120px" /></a-form-item>
        <a-form-item><a-button type="primary" @click="runBacktest" :loading="running">运行回测</a-button></a-form-item>
      </a-form>
    </a-card>

    <a-card title="回测结果" class="mt-4" v-if="result">
      <a-row :gutter="16">
        <a-col :span="4"><a-statistic title="年化收益" :value="result.annualReturn" suffix="%" /></a-col>
        <a-col :span="4"><a-statistic title="最大回撤" :value="result.maxDrawdown" suffix="%" /></a-col>
        <a-col :span="4"><a-statistic title="夏普比率" :value="result.sharpeRatio" /></a-col>
        <a-col :span="4"><a-statistic title="胜率" :value="result.winRate" suffix="%" /></a-col>
        <a-col :span="4"><a-statistic title="交易次数" :value="result.totalTrades" /></a-col>
        <a-col :span="4"><a-statistic title="盈亏比" :value="result.profitFactor" /></a-col>
      </a-row>
      <div ref="equityRef" style="height:300px;margin-top:16px" />
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import * as echarts from 'echarts'
import api from '@/api/client'

const running = ref(false)
const result = ref<any>(null)
const equityRef = ref<HTMLElement>()
const form = reactive({ market: 'CNStock', symbol: '600519', timeframe: '1D', capital: 100000 })

async function runBacktest() {
  running.value = true
  try {
    const { data } = await api.post('/backtest/run', {
      market: form.market, symbol: form.symbol, timeframe: form.timeframe,
      initial_capital: form.capital, strategy: 'sma_crossover',
    })
    result.value = data.result || data
    // Render equity curve
    setTimeout(() => {
      if (!equityRef.value) return
      const chart = echarts.init(equityRef.value)
      const equity = result.value?.equityCurve || []
      chart.setOption({
        tooltip: { trigger: 'axis' },
        xAxis: { type: 'category', data: equity.map((e: any) => e.time?.slice(0, 10)) },
        yAxis: { type: 'value' },
        series: [{ name: '净值', type: 'line', data: equity.map((e: any) => e.value), smooth: true, areaStyle: { opacity: 0.1 } }],
      })
    }, 100)
  } finally {
    running.value = false
  }
}
</script>
