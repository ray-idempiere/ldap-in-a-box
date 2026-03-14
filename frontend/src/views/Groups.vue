<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold">Groups</h1>
      <button @click="showCreate = true" class="bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700">+ New Group</button>
    </div>

    <div class="space-y-4">
      <div v-for="g in groups" :key="g.cn" class="bg-white p-4 rounded-lg shadow">
        <div class="flex items-center justify-between">
          <div>
            <span class="font-bold text-lg">{{ g.cn }}</span>
            <span class="text-gray-500 ml-3">{{ g.description }}</span>
          </div>
          <span class="text-gray-400">{{ g.members.length }} members</span>
        </div>
        <div class="mt-2">
          <span v-for="m in g.members" :key="m" class="inline-block bg-indigo-100 text-indigo-800 rounded px-2 py-0.5 text-sm mr-2">{{ m }}</span>
        </div>
        <div class="mt-3 flex gap-2">
          <input v-model="memberInputs[g.cn]" placeholder="Add member (uid)" class="border rounded px-2 py-1 text-sm" />
          <button @click="addMember(g.cn)" class="bg-green-500 text-white px-3 py-1 rounded text-sm">Add</button>
        </div>
      </div>
    </div>

    <div v-if="showCreate" class="fixed inset-0 bg-black/50 flex items-center justify-center">
      <form @submit.prevent="createGroup" class="bg-white p-6 rounded-lg w-96">
        <h2 class="text-xl font-bold mb-4">New Group</h2>
        <input v-model="newGroup.cn" placeholder="Group name" class="w-full border rounded px-3 py-2 mb-3" required />
        <input v-model="newGroup.description" placeholder="Description" class="w-full border rounded px-3 py-2 mb-3" />
        <div class="flex gap-3">
          <button type="submit" class="bg-indigo-600 text-white px-4 py-2 rounded">Create</button>
          <button type="button" @click="showCreate = false" class="border px-4 py-2 rounded">Cancel</button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue'
import api from '../api/client'

const groups = ref([])
const showCreate = ref(false)
const newGroup = ref({ cn: '', description: '' })
const memberInputs = reactive({})

async function fetchGroups() {
  const { data } = await api.get('/groups')
  groups.value = data
}

async function createGroup() {
  await api.post('/groups', newGroup.value)
  showCreate.value = false
  newGroup.value = { cn: '', description: '' }
  fetchGroups()
}

async function addMember(cn) {
  const uid = memberInputs[cn]
  if (!uid) return
  await api.post(`/groups/${cn}/members`, { uid })
  memberInputs[cn] = ''
  fetchGroups()
}

onMounted(fetchGroups)
</script>
