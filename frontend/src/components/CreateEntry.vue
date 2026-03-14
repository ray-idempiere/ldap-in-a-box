<template>
  <div class="p-6 h-full overflow-y-auto bg-white">
    <div class="flex justify-between items-center mb-6 border-b pb-4">
      <h2 class="text-2xl font-bold text-gray-800">New Entry</h2>
      <button @click="$emit('cancel')" class="text-gray-500 hover:text-gray-800">✕ Cancel</button>
    </div>

    <div class="mb-6 bg-blue-50 text-blue-800 p-4 rounded-lg">
      <div class="font-semibold mb-1">Parent DN:</div>
      <div class="font-mono text-sm break-all">{{ parentDn }}</div>
    </div>

    <div v-if="loadingTemplates" class="text-gray-500">Loading templates...</div>
    <form v-else @submit.prevent="submitForm" class="max-w-2xl space-y-6">
      
      <!-- Template Selection — large clear tabs -->
      <div>
        <label class="block font-semibold mb-3 text-gray-700">What do you want to create?</label>
        <div class="flex gap-2 border-b">
          <button v-for="t in mainTemplates" :key="t.id" type="button" @click="selectedTemplateId = t.id"
            class="px-5 py-3 font-medium text-sm border-b-2 -mb-px transition-colors"
            :class="selectedTemplateId === t.id ? 'border-indigo-600 text-indigo-700 bg-indigo-50' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'">
            {{ t.icon }} {{ t.label }}
          </button>
        </div>
      </div>

      <!-- Attributes Form -->
      <div v-if="currentTemplate" class="border rounded-lg p-5 bg-gray-50 space-y-4">
        
        <!-- RDN Field -->
        <div v-if="currentTemplate.rdn_attribute">
          <label class="block font-semibold mb-1">{{ rdnLabel }} <span class="text-red-500">*</span></label>
          <div class="flex items-center gap-2">
            <span class="font-mono text-gray-500 bg-white border rounded px-2 py-2 text-sm">{{ currentTemplate.rdn_attribute }}=</span>
            <input v-model="rdnValue" required class="flex-1 border rounded px-3 py-2 font-mono focus:ring-2 focus:ring-indigo-500 outline-none" :placeholder="rdnPlaceholder" />
          </div>
        </div>

        <!-- Custom RDN for 'custom' template -->
        <div v-else class="flex gap-2">
          <div class="w-1/3">
            <label class="block font-semibold mb-1">RDN Attribute <span class="text-red-500">*</span></label>
            <input v-model="customRdnAttr" required class="w-full border rounded px-3 py-2 font-mono" placeholder="e.g. cn" />
          </div>
          <div class="w-2/3">
            <label class="block font-semibold mb-1">RDN Value <span class="text-red-500">*</span></label>
            <input v-model="rdnValue" required class="w-full border rounded px-3 py-2 font-mono" placeholder="value" />
          </div>
        </div>

        <div class="h-px bg-gray-200 my-4"></div>

        <!-- Required Attributes -->
        <div v-if="requiredAttrs.length">
          <h3 class="font-semibold text-gray-700 mb-3">Required Fields</h3>
          <div v-for="attr in requiredAttrs" :key="attr" class="mb-3">
            <label class="block text-sm font-medium mb-1">{{ attr }} <span class="text-red-500">*</span></label>
            <input v-model="form[attr]" required class="w-full border rounded px-3 py-2 font-mono focus:ring-2 focus:ring-indigo-500 outline-none" />
          </div>
        </div>

        <!-- Optional Attributes -->
        <div v-if="optionalAttrs.length">
          <h3 class="font-semibold text-gray-700 mb-3 mt-4">Optional Fields</h3>
          <div v-for="attr in optionalAttrs" :key="attr" class="mb-3">
            <label class="block text-sm font-medium mb-1">{{ attr }}</label>
            <input v-model="form[attr]" class="w-full border rounded px-3 py-2 font-mono text-sm focus:ring-2 focus:ring-indigo-500 outline-none" />
          </div>
        </div>
        
        <!-- Custom objectClasses for Custom template -->
        <div v-if="selectedTemplateId === 'custom'" class="mt-4">
          <label class="block font-semibold mb-1">objectClass(es) (comma separated) <span class="text-red-500">*</span></label>
          <input v-model="customObjectClasses" required class="w-full border rounded px-3 py-2 font-mono" placeholder="e.g. top, inetOrgPerson" />
        </div>

      </div>

      <!-- Preview DN -->
      <div v-if="previewDn" class="bg-gray-100 border rounded-lg p-3 font-mono text-sm text-gray-600">
        <span class="text-gray-400">Will create:</span> {{ previewDn }}
      </div>

      <div class="flex gap-3 pt-2">
        <button type="submit" :disabled="submitting" class="bg-indigo-600 text-white px-6 py-2.5 rounded shadow hover:bg-indigo-700 disabled:opacity-50 font-medium">
          {{ submitting ? 'Creating...' : '✚ Create Entry' }}
        </button>
        <button type="button" @click="$emit('cancel')" class="border px-6 py-2.5 rounded hover:bg-gray-50 font-medium">Cancel</button>
      </div>

    </form>
  </div>
</template>

<script setup>
import { ref, watch, computed, onMounted } from 'vue'
import { apiV2 as api } from '../api/client'

const props = defineProps({
  parentDn: String
})

const emit = defineEmits(['created', 'cancel'])

const templates = ref([])
const loadingTemplates = ref(true)
const selectedTemplateId = ref('')
const currentTemplate = computed(() => templates.value.find(t => t.id === selectedTemplateId.value))

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

// Initialize form when template changes
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
      attributes: {
        [rdnAttr]: rdnValue.value
      }
    }

    // Add required/optional
    for (const key in form.value) {
      const val = form.value[key]
      if (val && val.trim() !== '') {
        payload.attributes[key] = val
      }
    }

    await api.post('/entry', payload)
    emit('created')
  } catch (e) {
    alert('Failed to create: ' + (e.response?.data?.detail || e.message))
  } finally {
    submitting.value = false
  }
}
</script>
