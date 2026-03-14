<template>
  <div v-if="loading" class="p-8 text-gray-500 flex items-center gap-2">
    <span class="animate-spin">⟳</span> Loading attributes...
  </div>
  <div v-else-if="entry" class="p-6 h-full overflow-y-auto bg-gray-950 text-gray-200">
    <!-- Header -->
    <div class="flex justify-between items-start mb-5 border-b border-gray-800 pb-4">
      <div class="min-w-0">
        <h2 class="text-xl font-bold mb-2 break-all text-gray-100 font-mono">{{ entryRdn }}</h2>
        <div class="flex flex-wrap gap-1.5 text-xs">
          <span v-for="oc in entry.attributes.objectClass" :key="oc" 
            class="bg-gray-800 text-gray-400 px-2 py-0.5 rounded border border-gray-700">{{ oc }}</span>
        </div>
      </div>
      <div class="flex gap-2 flex-shrink-0 ml-4">
        <button @click="saveChanges" :disabled="!hasChanges || saving"
          class="px-4 py-2 rounded text-sm font-medium transition-all"
          :class="hasChanges ? 'bg-indigo-600 text-white hover:bg-indigo-700 shadow-lg shadow-indigo-900/50' : 'bg-gray-800 text-gray-600 cursor-not-allowed'">
          {{ saving ? '⟳ Saving...' : '💾 Save' }}
        </button>
        <button v-if="hasChanges" @click="discardChanges" class="bg-gray-800 border border-gray-700 text-gray-300 px-4 py-2 rounded text-sm hover:bg-gray-700">↩ Discard</button>
        <button @click="$emit('delete', entry.dn)" class="bg-red-950 text-red-400 border border-red-900 px-4 py-2 rounded text-sm hover:bg-red-900">🗑 Delete</button>
      </div>
    </div>

    <!-- Toast -->
    <div v-if="toast" class="mb-4 px-4 py-3 rounded-lg text-sm font-medium transition-all"
      :class="toast.type === 'success' ? 'bg-green-900/50 text-green-300 border border-green-800' : 'bg-red-900/50 text-red-300 border border-red-800'">
      {{ toast.message }}
    </div>

    <!-- Diff summary bar -->
    <div v-if="hasChanges" class="mb-4 px-4 py-2 bg-yellow-900/30 border border-yellow-800/50 rounded-lg text-sm text-yellow-300 flex items-center gap-2">
      <span>📝</span> {{ changedCount }} attribute(s) modified — press <kbd class="px-1.5 py-0.5 bg-gray-800 rounded text-xs mx-1">Ctrl+S</kbd> to save
    </div>

    <!-- Attribute Groups -->
    <div class="space-y-3 max-w-4xl">
      <template v-for="group in attributeGroups" :key="group.name">
        <div v-if="group.attrs.length" class="border border-gray-800 rounded-lg overflow-hidden">
          <!-- Group Header (collapsible) -->
          <button @click="group.expanded = !group.expanded" 
            class="w-full flex items-center justify-between px-4 py-2.5 bg-gray-900 text-sm font-semibold text-gray-300 hover:bg-gray-800 transition-colors">
            <span class="flex items-center gap-2">
              <span>{{ group.icon }}</span> {{ group.name }}
              <span class="text-xs text-gray-600">({{ group.attrs.length }})</span>
            </span>
            <span class="text-gray-600 text-xs transform transition-transform" :class="{ 'rotate-180': group.expanded }">▼</span>
          </button>

          <!-- Group Content -->
          <div v-if="group.expanded" class="divide-y divide-gray-800/50">
            <div v-for="attr in group.attrs" :key="attr" class="px-4 py-3">
              <!-- Attribute label -->
              <div class="flex justify-between items-center mb-2">
                <span class="font-mono text-xs font-semibold text-gray-400 flex items-center gap-2">
                  {{ attr }}
                  <span v-if="isAttrChanged(attr)" class="w-2 h-2 rounded-full bg-yellow-500" title="Modified"></span>
                </span>
                <button @click="addValue(attr)" class="text-indigo-400 hover:text-indigo-300 text-xs">+ Add Value</button>
              </div>

              <!-- Password field -->
              <div v-if="attr === 'userPassword'" class="space-y-2">
                <div class="flex gap-2 items-center">
                  <input :type="showPassword ? 'text' : 'password'" v-model="editForm[attr][0]" 
                    class="w-full bg-gray-800 border border-gray-700 rounded px-3 py-1.5 font-mono text-sm text-gray-200 focus:ring-1 focus:ring-indigo-500 outline-none"
                    placeholder="Enter new password" />
                  <button @click="showPassword = !showPassword" class="text-gray-500 hover:text-gray-300 px-2 text-sm" :title="showPassword ? 'Hide' : 'Show'">
                    {{ showPassword ? '🙈' : '👁' }}
                  </button>
                </div>
              </div>

              <!-- Regular attribute values -->
              <div v-else class="space-y-2">
                <div v-for="(val, idx) in editForm[attr]" :key="idx" class="flex gap-2">
                  <input v-model="editForm[attr][idx]" 
                    class="w-full bg-gray-800 border rounded px-3 py-1.5 font-mono text-sm text-gray-200 focus:ring-1 focus:ring-indigo-500 outline-none transition-colors"
                    :class="isValueChanged(attr, idx) ? 'border-yellow-600/50 bg-yellow-900/10' : 'border-gray-700'"
                    :disabled="attr === 'objectClass' || isRdnAttribute(attr, val)" 
                    :placeholder="getPlaceholder(attr)"
                  />
                  <button v-if="attr !== 'objectClass' && !isRdnAttribute(attr, val)" @click="removeValue(attr, idx)" class="text-red-500 hover:text-red-400 px-2">✕</button>
                </div>
                <div v-if="editForm[attr].length === 0" class="text-gray-600 text-sm italic">No values</div>
              </div>
            </div>
          </div>
        </div>
      </template>

      <!-- Add new attribute -->
      <div class="border border-dashed border-gray-700 rounded-lg p-4 flex gap-3 items-center">
        <input v-model="newAttr" placeholder="New attribute name..." 
          class="bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm font-mono w-56 text-gray-200 placeholder-gray-600 focus:ring-1 focus:ring-indigo-500 outline-none" 
          @keydown.enter.prevent="addNewAttr" />
        <button @click="addNewAttr" class="bg-gray-800 border border-gray-700 text-gray-300 px-4 py-1.5 rounded text-sm hover:bg-gray-700">+ Add</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, watch, computed } from 'vue'
import { apiV2 as api } from '../api/client'

const props = defineProps({ dn: String })
const emit = defineEmits(['delete', 'updated'])

const loading = ref(false)
const saving = ref(false)
const entry = ref(null)
const editForm = ref({})
const originalForm = ref({})
const newAttr = ref('')
const toast = ref(null)
const showPassword = ref(false)

// Attribute placeholder hints
const placeholderMap = {
  mail: 'user@example.com',
  telephoneNumber: '+886-2-1234-5678',
  mobile: '+886-912-345-678',
  title: 'e.g. Software Engineer',
  description: 'A brief description...',
  cn: 'Common Name',
  sn: 'Surname',
  givenName: 'First name',
  displayName: 'Display name',
  employeeNumber: 'e.g. EMP001',
  homeDirectory: '/home/username',
  loginShell: '/bin/bash',
  uidNumber: 'e.g. 10001',
  gidNumber: 'e.g. 10001',
  o: 'Organisation name',
  l: 'City / Locality',
  st: 'State / Province',
  postalCode: 'e.g. 100',
  street: 'Street address',
}

function getPlaceholder(attr) { return placeholderMap[attr] || '' }

// Attribute grouping
const identityAttrs = ['uid', 'cn', 'sn', 'givenName', 'displayName', 'employeeNumber', 'title', 'description']
const contactAttrs = ['mail', 'telephoneNumber', 'mobile', 'facsimileTelephoneNumber', 'street', 'l', 'st', 'postalCode', 'o']
const securityAttrs = ['userPassword', 'loginShell', 'homeDirectory', 'uidNumber', 'gidNumber', 'objectClass']
const systemAttrs = ['objectClass', 'entryUUID', 'entryDN', 'structuralObjectClass', 'subschemaSubentry']

const attributeGroups = reactive([
  { name: 'Identity', icon: '🪪', expanded: true, attrs: [] },
  { name: 'Contact', icon: '📞', expanded: true, attrs: [] },
  { name: 'Security', icon: '🔒', expanded: true, attrs: [] },
  { name: 'Other', icon: '📄', expanded: true, attrs: [] },
])

function categorizeAttributes() {
  const allAttrs = Object.keys(editForm.value)
  attributeGroups[0].attrs = allAttrs.filter(a => identityAttrs.includes(a))
  attributeGroups[1].attrs = allAttrs.filter(a => contactAttrs.includes(a))
  attributeGroups[2].attrs = allAttrs.filter(a => securityAttrs.includes(a))
  attributeGroups[3].attrs = allAttrs.filter(a => !identityAttrs.includes(a) && !contactAttrs.includes(a) && !securityAttrs.includes(a))
}

const entryRdn = computed(() => entry.value?.dn?.split(',')[0] || '')
const hasChanges = computed(() => JSON.stringify(editForm.value) !== JSON.stringify(originalForm.value))
const changedCount = computed(() => {
  let count = 0
  for (const k in editForm.value) {
    if (JSON.stringify(editForm.value[k]) !== JSON.stringify(originalForm.value[k])) count++
  }
  return count
})

function isAttrChanged(attr) {
  return JSON.stringify(editForm.value[attr]) !== JSON.stringify(originalForm.value[attr])
}

function isValueChanged(attr, idx) {
  if (!originalForm.value[attr]) return true
  return editForm.value[attr][idx] !== (originalForm.value[attr][idx] ?? '')
}

watch(() => props.dn, loadEntry, { immediate: true })

async function loadEntry() {
  if (!props.dn) return
  loading.value = true
  toast.value = null
  showPassword.value = false
  try {
    const { data } = await api.get('/entry', { params: { dn: props.dn } })
    entry.value = data
    editForm.value = JSON.parse(JSON.stringify(data.attributes))
    originalForm.value = JSON.parse(JSON.stringify(data.attributes))
    categorizeAttributes()
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

function addValue(attr) { editForm.value[attr].push('') }
function removeValue(attr, idx) { editForm.value[attr].splice(idx, 1) }

function addNewAttr() {
  if (newAttr.value && !editForm.value[newAttr.value]) {
    editForm.value[newAttr.value] = ['']
    newAttr.value = ''
    categorizeAttributes()
  }
}

function discardChanges() {
  editForm.value = JSON.parse(JSON.stringify(originalForm.value))
  toast.value = null
  categorizeAttributes()
}

function showToast(type, message) {
  toast.value = { type, message }
  setTimeout(() => { toast.value = null }, 4000)
}

async function saveChanges() {
  if (!hasChanges.value) return
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

// Expose for keyboard shortcut
defineExpose({ saveChanges })
</script>
