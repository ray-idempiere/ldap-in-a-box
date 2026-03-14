<template>
  <div>
    <h1 class="text-2xl font-bold mb-6">Dashboard</h1>
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
      <div class="bg-white p-6 rounded-lg shadow">
        <div class="text-3xl font-bold text-indigo-600">{{ stats.users }}</div>
        <div class="text-gray-500">Users</div>
      </div>
      <div class="bg-white p-6 rounded-lg shadow">
        <div class="text-3xl font-bold text-green-600">{{ stats.groups }}</div>
        <div class="text-gray-500">Groups</div>
      </div>
      <div class="bg-white p-6 rounded-lg shadow">
        <div class="text-3xl font-bold text-blue-600">{{ stats.vpnUsers }}</div>
        <div class="text-gray-500">VPN Users</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../api/client'

const stats = ref({ users: 0, groups: 0, vpnUsers: 0 })

onMounted(async () => {
  const [usersRes, groupsRes] = await Promise.all([
    api.get('/users'),
    api.get('/groups'),
  ])
  const users = usersRes.data
  stats.value = {
    users: users.length,
    groups: groupsRes.data.length,
    vpnUsers: users.filter(u => u.is_vpn === 'Y').length,
  }
})
</script>
