<template>
  <div class="bg-gray-900 border border-gray-700 rounded-lg p-3 text-sm text-gray-200">
    <div class="flex items-center justify-between mb-3 border-b border-gray-800 pb-2">
      <h3 class="font-bold text-gray-300">{{ $t('tree.advancedSearch') }}</h3>
      <button @click="$emit('close')" class="text-gray-500 hover:text-gray-300">✕</button>
    </div>

    <!-- Match Type -->
    <div class="flex items-center gap-2 mb-4">
      <span class="text-gray-400">{{ $t('tree.match') }}</span>
      <select v-model="matchType" class="bg-gray-800 border border-gray-700 rounded px-2 py-1 focus:ring-1 focus:ring-indigo-500 outline-none">
        <option value="&">{{ $t('tree.allAnd') }}</option>
        <option value="|">{{ $t('tree.anyOr') }}</option>
      </select>
      <span class="text-gray-400">{{ $t('tree.rules') }}</span>
    </div>

    <!-- Rules List -->
    <div class="space-y-2 mb-4">
      <div v-for="(rule, idx) in rules" :key="idx" class="flex items-center gap-2 bg-gray-800/50 p-2 rounded border border-gray-700/50">
        <input 
          v-model="rule.attribute" 
          placeholder="Attribute (e.g. uid)" 
          class="w-1/3 bg-gray-950 border border-gray-700 rounded px-2 py-1 focus:ring-1 focus:ring-indigo-500 outline-none font-mono text-xs"
        />
        
        <select v-model="rule.operator" class="bg-gray-950 border border-gray-700 rounded px-2 py-1 focus:ring-1 focus:ring-indigo-500 outline-none">
          <option value="=">Equals (=)</option>
          <option value="">Contains (*val*)</option>
          <option value="^">Starts with (val*)</option>
          <option value="$">Ends with (*val)</option>
          <option value=">=">Greater than (>=)</option>
          <option value="<=">Less than (<=)</option>
        </select>
        
        <input 
          v-model="rule.value" 
          placeholder="Value" 
          class="flex-1 bg-gray-950 border border-gray-700 rounded px-2 py-1 focus:ring-1 focus:ring-indigo-500 outline-none font-mono text-xs"
          @keydown.enter="submitSearch"
        />
        
        <button @click="removeRule(idx)" class="text-gray-500 hover:text-red-400 px-1" title="Remove Rule">✕</button>
      </div>
    </div>

    <!-- Controls -->
    <div class="flex items-center justify-between mt-2">
      <button @click="addRule" class="text-indigo-400 hover:text-indigo-300 flex items-center gap-1 text-xs font-semibold">
        <span>+</span> {{ $t('tree.addRule') }}
      </button>
      
      <div class="flex gap-2">
        <button @click="$emit('close')" class="px-3 py-1.5 border border-gray-700 text-gray-400 hover:text-gray-200 rounded transition-colors">{{ $t('groups.cancel') }}</button>
        <button @click="submitSearch" class="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white font-medium rounded transition-colors shadow-lg shadow-indigo-900/20">{{ $t('tree.search') }}</button>
      </div>
    </div>

    <!-- Generated Query Preview -->
    <div class="mt-4 pt-3 border-t border-gray-800">
      <span class="text-xs text-gray-500 mb-1 block">{{ $t('tree.preview') }}</span>
      <div class="bg-gray-950 border border-gray-800 rounded p-2 text-xs font-mono text-indigo-300 break-all">
        {{ generatedFilter }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const emit = defineEmits(['search', 'close'])

const matchType = ref('&') // & for AND, | for OR
const rules = ref([
  { attribute: 'objectClass', operator: '=', value: '*' }
])

function addRule() {
  rules.value.push({ attribute: '', operator: '=', value: '' })
}

function removeRule(index) {
  rules.value.splice(index, 1)
  if (rules.value.length === 0) {
    addRule() // always keep at least one
  }
}

const generatedFilter = computed(() => {
  if (rules.value.length === 0) return '(objectClass=*)'
  
  const ruleStrings = rules.value.map(r => {
    let attr = r.attribute.trim() || '*'
    let val = r.value.trim()
    let op = r.operator
    
    // Construct the LDAP assertion
    if (op === '=') return `(${attr}=${val || '*'})`
    if (op === '') return `(${attr}=*${val}*)`
    if (op === '^') return `(${attr}=${val}*)`
    if (op === '$') return `(${attr}=*${val})`
    if (op === '>=') return `(${attr}>=${val})`
    if (op === '<=') return `(${attr}<=${val})`
    return `(${attr}=${val})`
  })

  if (ruleStrings.length === 1) {
    return ruleStrings[0]
  }
  
  return `(${matchType.value}${ruleStrings.join('')})`
})

function submitSearch() {
  emit('search', generatedFilter.value)
}
</script>
