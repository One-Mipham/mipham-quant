<template>
  <div>
    <h2 class="text-2xl font-bold mb-4">快讯</h2>
    <a-list :dataSource="news" :loading="loading" size="small">
      <template #renderItem="{item}">
        <a-list-item>
          <a-list-item-meta :title="item.title" :description="item.time" />
        </a-list-item>
      </template>
    </a-list>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '@/api/client'

const loading = ref(true)
const news = ref<any[]>([])

onMounted(async () => {
  try {
    const { data } = await api.get('/market/news', { params: { market: 'CNStock', limit: 20 } })
    news.value = (data.news || data.items || []).map((n: any) => ({
      title: n.title || n.headline || n.name,
      time: n.time || n.published || n.date,
    }))
  } catch { /* empty */ }
  loading.value = false
})
</script>
