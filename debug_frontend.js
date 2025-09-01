// Script de debug para la UI - Copia y pega esto en la consola del navegador
// en la página /calls-manager

console.log('🐛 INICIANDO DEBUG DE LA UI...');

// 1. Verificar que el objeto CallsManager existe
if (typeof callsManager !== 'undefined') {
    console.log('✅ callsManager encontrado:', callsManager);
    console.log('📊 Estado actual:', callsManager.state);
    console.log('📊 Leads en estado:', callsManager.state.leads.length);
    console.log('📊 Filtros:', callsManager.state.filters);
} else {
    console.error('❌ callsManager no encontrado - problema de inicialización');
}

// 2. Verificar elementos del DOM
const elementos = {
    selectAllBtn: document.getElementById('selectAllBtn'),
    deselectAllBtn: document.getElementById('deselectAllBtn'),
    leadsTableBody: document.getElementById('leadsTableBody'),
    masterCheckbox: document.getElementById('masterCheckbox')
};

console.log('🔍 Elementos del DOM:', elementos);

// 3. Función de prueba manual
window.debugSelectAll = function(selected = true) {
    console.log(`🧪 PROBANDO SELECCIÓN MANUAL - selected=${selected}`);
    
    if (!callsManager) {
        console.error('❌ callsManager no disponible');
        return;
    }
    
    console.log('📊 Estado ANTES:', {
        totalLeads: callsManager.state.leads.length,
        selectedCount: callsManager.state.leads.filter(l => l.selected_for_calling).length,
        filtros: callsManager.state.filters
    });
    
    // Ejecutar selectAllLeads
    callsManager.selectAllLeads(selected);
    
    setTimeout(() => {
        console.log('📊 Estado DESPUÉS:', {
            totalLeads: callsManager.state.leads.length,
            selectedCount: callsManager.state.leads.filter(l => l.selected_for_calling).length,
            filtros: callsManager.state.filters
        });
        
        const rows = document.querySelectorAll('#leadsTableBody tr');
        console.log('📊 Filas visibles en tabla:', rows.length);
    }, 100);
};

// 4. Función para resetear filtros
window.debugClearFilters = function() {
    console.log('🧹 Limpiando filtros...');
    if (callsManager) {
        callsManager.state.filters = {
            estado1: '',
            estado2: '',
            status: '',
            priority: '',
            selected: ''
        };
        callsManager.clearFilters();
    }
};

// 5. Función para inspeccionar leads
window.debugInspectLeads = function() {
    if (!callsManager) return;
    
    console.log('🔍 INSPECCIÓN DE LEADS:');
    const leads = callsManager.state.leads.slice(0, 5); // Primeros 5
    leads.forEach((lead, i) => {
        console.log(`Lead ${i + 1}:`, {
            id: lead.id,
            nombre: lead.nombre_lead || `${lead.nombre} ${lead.apellidos}`,
            selected_for_calling: lead.selected_for_calling,
            call_status: lead.call_status,
            status_level_1: lead.status_level_1,
            status_level_2: lead.status_level_2
        });
    });
};

console.log('🎮 COMANDOS DISPONIBLES:');
console.log('- debugSelectAll(true)   // Seleccionar todos');
console.log('- debugSelectAll(false)  // Deseleccionar todos'); 
console.log('- debugClearFilters()    // Limpiar filtros');
console.log('- debugInspectLeads()    // Inspeccionar primeros 5 leads');
console.log('');
console.log('💡 INSTRUCCIONES:');
console.log('1. Carga la página /calls-manager');
console.log('2. Abre DevTools (F12)');
console.log('3. Copia y pega este script en la consola');
console.log('4. Usa debugSelectAll(true) para probar la selección');
console.log('5. Revisa los logs detallados para encontrar el problema');