<template>
  <div>
    <h2 class="text-2xl font-bold mb-4">策略编辑器</h2>
    <a-card>
      <a-tabs>
        <a-tab-pane key="builtin" tab="示例策略">
          <a-list :dataSource="examples" size="small">
            <template #renderItem="{item}">
              <a-list-item>
                <a-list-item-meta :title="item.name" :description="item.desc" />
                <a-button type="primary" ghost @click="selectExample(item)">使用</a-button>
              </a-list-item>
            </template>
          </a-list>
        </a-tab-pane>
        <a-tab-pane key="custom" tab="自定义策略">
          <a-textarea v-model:value="code" :rows="15" placeholder="输入 Python 策略代码..." />
          <a-button type="primary" class="mt-2" @click="saveStrategy">保存策略</a-button>
        </a-tab-pane>
      </a-tabs>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import api from '@/api/client'
import { message } from 'ant-design-vue'

const code = ref('')
const examples = ref([
  { name: '双均线交叉', desc: '5/20 SMA 金叉买入、死叉卖出', code: '...' },
  { name: '均值回归', desc: '布林带下轨 + RSI<35 超卖反弹', code: '...' },
  { name: '动量突破', desc: '20日新高 + 2x放量确认', code: '...' },
  { name: '多因子趋势', desc: '60MA趋势 + 量价配合', code: '...' },
])

function selectExample(item: any) { code.value = item.code }
async function saveStrategy() {
  await api.post('/indicator/save', { code: code.value })
  message.success('策略已保存')
}
</script>
