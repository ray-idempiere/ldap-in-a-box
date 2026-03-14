<template>
  <div class="p-6 h-full overflow-y-auto bg-gray-950 text-gray-200">
    <div class="flex justify-between items-center mb-6 border-b border-gray-800 pb-4">
      <h2 class="text-xl font-bold">✚ New Entry</h2>
      <button @click="$emit('cancel')" class="text-gray-500 hover:text-gray-300 transition-colors">✕ Cancel</button>
    </div>

    <div class="mb-6 bg-indigo-950/50 text-indigo-300 p-4 rounded-lg border border-indigo-800/50">
      <div class="font-semibold mb-1 text-xs uppercase tracking-wider text-indigo-400">Parent DN</div>
      <div class="font-mono text-sm break-all">{{ parentDn }}</div>
    </div>

    <!-- Toast -->
    <div v-if="toast" class="mb-4 px-4 py-3 rounded-lg text-sm font-medium"
      :class="toast.type === 'success' ? 'bg-green-900/50 text-green-300 border border-green-800' : 'bg-red-900/50 text-red-300 border border-red-800'">
      {{ toast.message }}
    </div>

    <div v-if="loadingTemplates" class="text-gray-500 flex items-center gap-2">
      <span class="animate-spin">⟳</span> Loading templates...
    </div>
    <form v-else @submit.prevent="submitForm" class="max-w-2xl space-y-6">
      
      <!-- Template Selection -->
      <div>
        <label class="block text-xs font-semibold mb-3 text-gray-400 uppercase tracking-wider">Entry Type</label>
        <div class="flex gap-2 border-b border-gray-800">
          <button v-for="t in mainTemplates" :key="t.id" type="button" @click="selectedTemplateId = t.id"
            class="px-5 py-3 font-medium text-sm border-b-2 -mb-px transition-colors"
            :class="selectedTemplateId === t.id ? 'border-indigo-500 text-indigo-300 bg-indigo-950/50' : 'border-transparent text-gray-500 hover:text-gray-300 hover:border-gray-600'">
            {{ t.icon }} {{ t.label }}
          </button>
        </div>
      </div>

      <!-- Attributes Form -->
      <div v-if="currentTemplate" class="border border-gray-800 rounded-lg p-5 bg-gray-900/50 space-y-4">
        
        <!-- RDN Field -->
        <div v-if="currentTemplate.rdn_attribute">
          <label class="block font-semibold mb-1 text-sm text-gray-300">{{ rdnLabel }} <span class="text-red-400">*</span></label>
          <div class="flex items-center gap-2">
            <span class="font-mono text-gray-500 bg-gray-800 border border-gray-700 rounded px-2 py-2 text-sm">{{ currentTemplate.rdn_attribute }}=</span>
            <input v-model="rdnValue" required 
              class="flex-1 bg-gray-800 border border-gray-700 rounded px-3 py-2 font-mono text-gray-200 focus:ring-1 focus:ring-indigo-500 outline-none" 
              :placeholder="rdnPlaceholder" />
          </div>
        </div>

        <!-- Custom RDN -->
        <div v-else class="flex gap-2">
          <div class="w-1/3">
            <label class="block font-semibold mb-1 text-sm text-gray-300">RDN Attribute <span class="text-red-400">*</span></label>
            <input v-model="customRdnAttr" required class="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 font-mono text-gray-200" placeholder="e.g. cn" />
          </div>
          <div class="w-2/3">
            <label class="block font-semibold mb-1 text-sm text-gray-300">RDN Value <span class="text-red-400">*</span></label>
            <input v-model="rdnValue" required class="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 font-mono text-gray-200" placeholder="value" />
          </div>
        </div>

        <div class="h-px bg-gray-800 my-4"></div>

        <!-- Required Attributes -->
        <div v-if="requiredAttrs.length">
          <h3 class="font-semibold text-gray-400 mb-3 text-xs uppercase tracking-wider">Required Fields</h3>
          <div v-for="attr in requiredAttrs" :key="attr" class="mb-3">
            <label class="block text-sm font-medium mb-1 text-gray-300">{{ attr }} <span class="text-red-400">*</span></label>
            <input v-model="form[attr]" required class="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 font-mono text-gray-200 focus:ring-1 focus:ring-indigo-500 outline-none" />
          </div>
        </div>

        <!-- Optional Attributes -->
        <div v-if="optionalAttrs.length">
          <h3 class="font-semibold text-gray-400 mb-3 mt-4 text-xs uppercase tracking-wider">Optional Fields</h3>
          <div v-for="attr in optionalAttrs" :key="attr" class="mb-3">
            <label class="block text-sm font-medium mb-1 text-gray-400">{{ attr }}</label>
            <input v-model="form[attr]" class="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 font-mono text-sm text-gray-200 focus:ring-1 focus:ring-indigo-500 outline-none" />
          </div>
        </div>
        
        <!-- Custom objectClasses -->
        <div v-if="selectedTemplateId === 'custom'" class="mt-4">
          <label class="block font-semibold mb-1 text-sm text-gray-300">objectClass(es) <span class="text-red-400">*</span></label>
          <input v-model="customObjectClasses" required class="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 font-mono text-gray-200" placeholder="e.g. top, inetOrgPerson" />
        </div>
      </div>

      <!-- Preview DN -->
      <div v-if="previewDn" class="bg-gray-900 border border-gray-800 rounded-lg p-3 font-mono text-sm text-gray-400">
        <span class="text-gray-600">Will create:</span> <span class="text-indigo-300">{{ previewDn }}</span>
      </div>

      <div class="flex gap-3 pt-2">
        <button type="submit" :disabled="submitting" 
          class="bg-indigo-600 text-white px-6 py-2.5 rounded font-medium hover:bg-indigo-700 disabled:opacity-50 shadow-lg shadow-indigo-900/50 transition-all">
          {{ submitting ? '⟳ Creating...' : '✚ Create Entry' }}
        </button>
        <button type="button" @click="$emit('cancel')" class="bg-gray-800 border border-gray-700 text-gray-300 px-6 py-2.5 rounded font-medium hover:bg-gray-700">Cancel</button>
      </div>
    </form>
  </div>
</template>

<script setup>
import { ref, watch, computed, onMounted } from 'vue'
import { apiV2 as api } from '../api/client'

const props = defineProps({ parentDn: String })
const emit = defineEmits(['created', 'cancel'])

const templates = ref([])
const loadingTemplates = ref(true)
const selectedTemplateId = ref('')
const currentTemplate = computed(() => templates.value.find(t => t.id === selectedTemplateId.value))
const toast = ref(null)

const mainTemplates = computed(() => [
  { id: 'organizationalUnit', icon: '📁', label: 'OU' },
  { id: 'inetOrgPerson', icon: '👤', label: 'User' },
  { id: 'posixGroup', icon: '👥', label: 'Group' },
  { id: 'custom', icon: '📄', label: 'Custom' }
])

const rdnLabel = computed(() => {
  const t = currentTemplate.value
  if (!t) return 'RDN'
  if (t.id === 'organizationalUnit') return 'OU Name'
  if (t.id === 'inetOrgPerson') return 'User ID (uid)'
  if (t.id === 'posixGroup') return 'Group Name (cn)'
  return `RDN (${t.rdn_attribute})`
})

const rdnPlaceholder = computed(() => {
  const t = currentTemplate.value
  if (!t) return 'value'
  if (t.id === 'organizationalUnit') return 'e.g. engineering'
  if (t.id === 'inetOrgPerson') return 'e.g. john.doe'
  if (t.id === 'posixGroup') return 'e.g. developers'
  return 'value'
})

const previewDn = computed(() => {
  if (!rdnValue.value || !currentTemplate.value) return ''
  const rdnAttr = currentTemplate.value.rdn_attribute || customRdnAttr.value
  if (!rdnAttr) return ''
  return `${rdnAttr}=${rdnValue.value},${props.parentDn}`
})

const rdnValue = ref('')
const customRdnAttr = ref('')
const customObjectClasses = ref('')
const form = ref({})
const submitting = ref(false)

function showToast(type, message) {
  toast.value = { type, message }
  setTimeout(() => { toast.value = null }, 4000)
}

onMounted(async () => {
  try {
    const { data } = await api.get('/schema/templates')
    templates.value = data
    selectedTemplateId.value = 'organizationalUnit'
  } catch (e) {
    console.error('Failed to load templates')
  } finally {
    loadingTemplates.value = false
  }
})

watch(currentTemplate, (tmpl) => {
  form.value = {}
  rdnValue.value = ''
  if (tmpl) {
    (tmpl.required || []).forEach(a => { if(a !== tmpl.rdn_attribute) form.value[a] = '' })
    ;(tmpl.optional || []).forEach(a => form.value[a] = '')
  }
}, { immediate: true })

const requiredAttrs = computed(() => {
  if (!currentTemplate.value) return []
  return currentTemplate.value.required.filter(a => a !== currentTemplate.value.rdn_attribute)
})

const optionalAttrs = computed(() => {
  if (!currentTemplate.value) return []
  return currentTemplate.value.optional
})

async function submitForm() {
  submitting.value = true
  try {
    const template = currentTemplate.value
    const rdnAttr = template.rdn_attribute || customRdnAttr.value
    const rdn = `${rdnAttr}=${rdnValue.value}`
    
    let objectClasses = template.objectClasses
    if (template.id === 'custom') {
      objectClasses = customObjectClasses.value.split(',').map(s => s.trim()).filter(Boolean)
    }

    const payload = {
      parent_dn: props.parentDn,
      rdn: rdn,
      objectClasses: objectClasses,
      attributes: { [rdnAttr]: rdnValue.value }
    }

    for (const key in form.value) {
      const val = form.value[key]
      if (val && val.trim() !== '') payload.attributes[key] = val
    }

    await api.post('/entry', payload)
    emit('created')
  } catch (e) {
    showToast('error', '❌ Failed: ' + (e.response?.data?.detail || e.message))
  } finally {
    submitting.value = false
  }
}
</script>
