<template>
  <div v-if="loading" class="p-8 text-gray-500">Loading attributes...</div>
  <div v-else-if="entry" class="p-6 h-full overflow-y-auto bg-white">
    <div class="flex justify-between items-start mb-6 border-b pb-4">
      <div>
        <h2 class="text-2xl font-bold mb-1 break-all">{{ entry.dn }}</h2>
        <div class="flex flex-wrap gap-2 text-sm text-gray-500 mt-2">
          <span v-for="oc in entry.attributes.objectClass" :key="oc" class="bg-gray-100 px-2 py-0.5 rounded border">{{ oc }}</span>
        </div>
      </div>
      <div class="flex gap-3 flex-shrink-0">
        <button @click="saveChanges" :disabled="!hasChanges || saving"
          class="px-4 py-2 rounded shadow transition-colors"
          :class="hasChanges ? 'bg-indigo-600 text-white hover:bg-indigo-700' : 'bg-gray-200 text-gray-400 cursor-not-allowed'">
          {{ saving ? 'Saving...' : '💾 Save' }}
        </button>
        <button v-if="hasChanges" @click="discardChanges" class="border px-4 py-2 rounded hover:bg-gray-50">↩ Discard</button>
        <button @click="$emit('delete', entry.dn)" class="bg-red-50 text-red-600 border border-red-200 px-4 py-2 rounded hover:bg-red-100">🗑 Delete</button>
      </div>
    </div>

    <!-- Success/Error Toast -->
    <div v-if="toast" class="mb-4 px-4 py-3 rounded-lg text-sm font-medium" :class="toast.type === 'success' ? 'bg-green-50 text-green-700 border border-green-200' : 'bg-red-50 text-red-700 border border-red-200'">
      {{ toast.message }}
    </div>

    <div class="space-y-4 max-w-4xl">
      <div v-for="(vlist, attr) in editForm" :key="attr" class="border rounded-lg overflow-hidden">
        <div class="bg-gray-50 px-4 py-2 border-b font-mono text-sm font-semibold flex justify-between items-center group">
          <span>{{ attr }}</span>
          <button @click="addValue(attr)" class="text-indigo-600 hover:underline text-xs opacity-0 group-hover:opacity-100">+ Add Value</button>
        </div>
        <div class="p-4 space-y-2">
          <div v-for="(val, idx) in vlist" :key="idx" class="flex gap-2">
            <input v-model="editForm[attr][idx]" class="w-full border rounded px-3 py-1.5 font-mono text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-shadow" :disabled="attr === 'objectClass' || isRdnAttribute(attr, val)" :class="{ 'bg-gray-100 text-gray-500': attr === 'objectClass' || isRdnAttribute(attr, val) }" />
            <button v-if="attr !== 'objectClass' && !isRdnAttribute(attr, val)" @click="removeValue(attr, idx)" class="text-red-400 hover:text-red-600 px-2">✕</button>
          </div>
          <div v-if="vlist.length === 0" class="text-gray-400 text-sm italic">No values</div>
        </div>
      </div>

      <!-- Add new attribute -->
      <div class="border border-dashed rounded-lg p-4 flex gap-3">
        <input v-model="newAttr" placeholder="New attribute (e.g. description)" class="border rounded px-3 py-1 text-sm font-mono w-48" @keydown.enter.prevent="addNewAttr" />
        <button @click="addNewAttr" class="bg-gray-100 border px-4 py-1 rounded text-sm hover:bg-gray-200">Add Attribute</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { apiV2 as api } from '../api/client'

const props = defineProps({
  dn: String
})

const emit = defineEmits(['delete', 'updated'])

const loading = ref(false)
const saving = ref(false)
const entry = ref(null)
const editForm = ref({})
const originalForm = ref({})
const newAttr = ref('')
const toast = ref(null)

const hasChanges = computed(() => JSON.stringify(editForm.value) !== JSON.stringify(originalForm.value))

watch(() => props.dn, loadEntry, { immediate: true })

async function loadEntry() {
  if (!props.dn) return
  loading.value = true
  toast.value = null
  try {
    const { data } = await api.get('/entry', { params: { dn: props.dn } })
    entry.value = data
    editForm.value = JSON.parse(JSON.stringify(data.attributes))
    originalForm.value = JSON.parse(JSON.stringify(data.attributes))
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

function isRdnAttribute(attr, val) {
  const rdnPart = `${attr}=${val}`
  return entry.value.dn.toLowerCase().startsWith(rdnPart.toLowerCase())
}

function addValue(attr) {
  editForm.value[attr].push('')
}

function removeValue(attr, idx) {
  editForm.value[attr].splice(idx, 1)
}

function addNewAttr() {
  if (newAttr.value && !editForm.value[newAttr.value]) {
    editForm.value[newAttr.value] = ['']
    newAttr.value = ''
  }
}

function discardChanges() {
  editForm.value = JSON.parse(JSON.stringify(originalForm.value))
  toast.value = null
}

function showToast(type, message) {
  toast.value = { type, message }
  setTimeout(() => { toast.value = null }, 4000)
}

async function saveChanges() {
  saving.value = true
  try {
    const cleanData = {}
    for (const k in editForm.value) {
      if (k === 'objectClass') continue
      const vals = editForm.value[k].filter(v => !!v.trim())
      if (vals.length > 0) {
        cleanData[k] = vals
      } else if (originalForm.value[k] && originalForm.value[k].length > 0) {
        cleanData[k] = []
      }
    }
    
    await api.put('/entry', cleanData, { params: { dn: props.dn } })
    await loadEntry()
    showToast('success', '✅ Entry saved successfully!')
    emit('updated')
  } catch (e) {
    showToast('error', '❌ Failed to save: ' + (e.response?.data?.detail || e.message))
  } finally {
    saving.value = false
  }
}
</script>
