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
      
      <!-- Template Selection -->
      <div>
        <label class="block font-semibold mb-2">Entry Template</label>
        <div class="grid grid-cols-2 gap-3">
          <label v-for="t in templates" :key="t.id" class="border rounded px-4 py-3 cursor-pointer hover:bg-gray-50 flex items-center gap-3" :class="{'ring-2 ring-indigo-500 bg-indigo-50': selectedTemplateId === t.id}">
            <input type="radio" :value="t.id" v-model="selectedTemplateId" class="hidden" />
            <span class="font-medium">{{ t.name }}</span>
          </label>
        </div>
      </div>

      <!-- Attributes Form -->
      <div v-if="currentTemplate" class="border rounded-lg p-5 bg-gray-50 space-y-4">
        
        <!-- RDN Field -->
        <div v-if="currentTemplate.rdn_attribute">
          <label class="block font-semibold mb-1">RDN ({{ currentTemplate.rdn_attribute }}) <span class="text-red-500">*</span></label>
          <div class="flex items-center gap-2">
            <span class="font-mono text-gray-500">{{ currentTemplate.rdn_attribute }}=</span>
            <input v-model="rdnValue" required class="flex-1 border rounded px-3 py-2 font-mono" placeholder="value" />
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
        <h3 v-if="requiredAttrs.length" class="font-semibold text-gray-700">Required Attributes</h3>
        <div v-for="attr in requiredAttrs" :key="attr">
          <label class="block text-sm font-medium mb-1">{{ attr }} <span class="text-red-500">*</span></label>
          <input v-model="form[attr]" required class="w-full border rounded px-3 py-2 font-mono" />
        </div>

        <!-- Optional Attributes -->
        <h3 v-if="optionalAttrs.length" class="font-semibold text-gray-700 mt-4">Optional Attributes</h3>
        <div v-for="attr in optionalAttrs" :key="attr" class="flex items-center gap-2 mb-2">
          <label class="w-48 text-sm font-medium">{{ attr }}</label>
          <input v-model="form[attr]" class="flex-1 border rounded px-3 py-2 font-mono text-sm" />
        </div>
        
        <!-- Custom objectClasses for Custom template -->
        <div v-if="selectedTemplateId === 'custom'" class="mt-4">
          <label class="block font-semibold mb-1">objectClass(es) (comma separated) <span class="text-red-500">*</span></label>
          <input v-model="customObjectClasses" required class="w-full border rounded px-3 py-2 font-mono" placeholder="e.g. top, inetOrgPerson" />
        </div>

      </div>

      <div class="flex gap-3 pt-4">
        <button type="submit" :disabled="submitting" class="bg-indigo-600 text-white px-6 py-2 rounded shadow hover:bg-indigo-700 disabled:opacity-50">
          {{ submitting ? 'Creating...' : 'Create Entry' }}
        </button>
      </div>

    </form>
  </div>
</template>

<script setup>
import { ref, watch, computed, onMounted } from 'vue'
import api from '../api/client'

const props = defineProps({
  parentDn: String
})

const emit = defineEmits(['created', 'cancel'])

const templates = ref([])
const loadingTemplates = ref(true)
const selectedTemplateId = ref('')
const currentTemplate = computed(() => templates.value.find(t => t.id === selectedTemplateId.value))

const rdnValue = ref('')
const customRdnAttr = ref('')
const customObjectClasses = ref('')
const form = ref({})
const submitting = ref(false)

onMounted(async () => {
  try {
    const { data } = await api.get('/schema/templates')
    templates.value = data
    if (data.length > 0) {
      selectedTemplateId.value = data[0].id
    }
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
    (tmpl.optional || []).forEach(a => form.value[a] = '')
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
