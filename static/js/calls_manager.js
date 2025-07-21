/**
 * Gestor de Llamadas - Lógica del Frontend
 * Este script maneja la interfaz de usuario para el gestor de llamadas,
 * incluyendo la carga de leads, inicio/detención de llamadas, y actualización de estados.
 */

class CallsManager {
    constructor() {
        this.elements = {};
        this.state = {
            leads: [],
            currentPage: 1,
            itemsPerPage: 15,
            isSystemRunning: false,
            socket: null,
            retryCount: 0,
            maxRetries: 5,
            retryDelay: 5000, // 5 segundos
            isLoading: false,
            isInitialized: false,
            filters: {
                estado1: '',
                estado2: '',
                status: '',
                priority: '',
                selected: ''
            }
        };
        this.config = {
            maxConcurrentCalls: 3
        };
    }

    init() {
        if (this.state.isInitialized) {
            console.warn('⚠️ CallsManager ya está inicializado');
            return;
        }
        
        console.log('🚀 Inicializando CallsManager...');
        
        // Asegurar que los métodos utilitarios existen
        if (!this.setLoading) this.setLoading = (flag) => { this.state.isLoading = flag; };
        if (!this.showToast) this.showToast = (msg, type='info') => {
            console.log(`📢 ${type.toUpperCase()}: ${msg}`);
            this.showNotification(msg, type);
        };
        
        // Función para normalizar datos de leads
        if (!this.normalizeLeadsData) this.normalizeLeadsData = (leads) => {
            return leads.map(lead => {
                return {
                    ...lead,
                    selected_for_calling: lead.selected_for_calling || false,
                    call_status: lead.call_status || 'no_selected',
                    call_priority: lead.call_priority || 3,
                    call_attempts_count: lead.call_attempts_count || 0,
                    status_level_1: lead.status_level_1 || '',
                    status_level_2: lead.status_level_2 || ''
                };
            });
        };
        
        // Métodos de filtros mínimos
        if (!this.getFilteredLeads) this.getFilteredLeads = () => {
            return this.state.leads.filter(l => {
                const f = this.state.filters;
                if (f.estado1 && l.status_level_1 !== f.estado1) return false;
                if (f.estado2 && l.status_level_2 !== f.estado2) return false;
                if (f.status && l.call_status !== f.status) return false;
                if (f.priority && String(l.call_priority) !== String(f.priority)) return false;
                if (f.selected === 'true' && !l.selected_for_calling) return false;
                if (f.selected === 'false' && l.selected_for_calling) return false;
                return true;
            });
        };
        
        if (!this.updateFilters) this.updateFilters = () => {
            // Rellenar combos con valores únicos
            const estados1 = [...new Set(this.state.leads.map(l => l.status_level_1).filter(Boolean))].sort();
            const estados2 = [...new Set(this.state.leads.map(l => l.status_level_2).filter(Boolean))].sort();
            
            if (this.elements.estado1Filter) {
                this.elements.estado1Filter.innerHTML = '<option value="">Todos</option>' + 
                    estados1.map(e=>`<option value="${e}">${e}</option>`).join('');
            }
            
            if (this.elements.estado2Filter) {
                this.elements.estado2Filter.innerHTML = '<option value="">Todos</option>' + 
                    estados2.map(e=>`<option value="${e}">${e}</option>`).join('');
            }
        };
        
        if (!this.loadFilters) this.loadFilters = () => this.updateFilters();
        
        // Inicialización paso a paso
        this.cacheElements();
        this.bindEvents();
        this.connectWebSocket();
        
        // Solo cargar datos iniciales una vez
        this.loadInitialData();
        
        // Cargar configuración al final
        this.loadConfiguration().catch(error => {
            console.warn('Error cargando configuración:', error);
        });
        
        // Marcar como inicializado
        this.state.isInitialized = true;
        
        console.log('✅ CallsManager inicializado correctamente');
    }

    cacheElements() {
        this.elements = {
            startCallsBtn: document.getElementById('startCallsBtn'),
            stopCallsBtn: document.getElementById('stopCallsBtn'),
            refreshBtn: document.getElementById('refreshBtn'),
            systemStatus: document.getElementById('systemStatus'),
            connectionStatus: document.getElementById('connectionStatus'),
            leadsTableBody: document.getElementById('leadsTableBody'),
            leadsInfo: document.getElementById('leadsInfo'),
            pagination: document.getElementById('pagination'),
            masterCheckbox: document.getElementById('masterCheckbox'),
            selectAllBtn: document.getElementById('selectAllBtn'),
            deselectAllBtn: document.getElementById('deselectAllBtn'),
            resetLeadsBtn: document.getElementById('resetLeadsBtn'),
            toastContainer: document.getElementById('toastContainer'),
            // Filtros
            estado1Filter: document.getElementById('estado1Filter'),
            estado2Filter: document.getElementById('estado2Filter'),
            statusFilter: document.getElementById('statusFilter'),
            priorityFilter: document.getElementById('priorityFilter'),
            selectedFilter: document.getElementById('selectedFilter'),
            clearFiltersBtn: document.getElementById('clearFiltersBtn'),
            // Modales
            configModal: document.getElementById('configModal'),
            maxConcurrentCalls: document.getElementById('maxConcurrentCalls'),
            saveConfigBtn: document.getElementById('saveConfigBtn'),
            testConnectionBtn: document.getElementById('testConnectionBtn'),
            pearlConnectionStatus: document.getElementById('pearlConnectionStatus'),
            leadDetailsModal: document.getElementById('leadDetailsModal'),
            leadDetailsContent: document.getElementById('leadDetailsContent'),
            // Contadores
            totalCallsCount: document.getElementById('totalCallsCount'),
            successCallsCount: document.getElementById('successCallsCount'),
            failedCallsCount: document.getElementById('failedCallsCount'),
            activeCallsCount: document.getElementById('activeCallsCount'),
            // Progreso
            progressSection: document.getElementById('progressSection'),
            progressBar: document.getElementById('progressBar'),
            progressText: document.getElementById('progressText'),
            // Modo Prueba
            testModeSwitch: document.getElementById('testModeSwitch'),
            testPhoneContainer: document.getElementById('testPhoneContainer'),
            overridePhoneInput: document.getElementById('overridePhoneInput')
        };
    }

    bindEvents() {
        this.elements.startCallsBtn?.addEventListener('click', () => this.startCalling());
        this.elements.stopCallsBtn?.addEventListener('click', () => this.stopCalling());
        this.elements.refreshBtn?.addEventListener('click', () => this.loadInitialData());
        this.elements.estado1Filter?.addEventListener('change', () => this.applyFilters());
        this.elements.estado2Filter?.addEventListener('change', () => this.applyFilters());
        this.elements.statusFilter?.addEventListener('change', () => this.applyFilters());
        this.elements.priorityFilter?.addEventListener('change', () => this.applyFilters());
        this.elements.selectedFilter?.addEventListener('change', () => this.applyFilters());
        this.elements.clearFiltersBtn?.addEventListener('click', () => this.clearFilters());
        this.elements.selectAllBtn?.addEventListener('click', () => this.selectAllLeads(true));
        this.elements.deselectAllBtn?.addEventListener('click', () => this.selectAllLeads(false));
        this.elements.resetLeadsBtn?.addEventListener('click', () => this.resetLeads());
        this.elements.masterCheckbox?.addEventListener('change', (e) => this.toggleAllCheckboxes(e.target.checked));
        this.elements.testConnectionBtn?.addEventListener('click', () => this.testConnection());
        this.elements.saveConfigBtn?.addEventListener('click', () => this.saveConfiguration());

        if (this.elements.testModeSwitch) {
            this.elements.testModeSwitch.addEventListener('change', (e) => {
                this.elements.testPhoneContainer.style.display = e.target.checked ? 'block' : 'none';
            });
        }
    }

    async apiCall(method, endpoint, body = null) {
        // SOLUCIÓN AL PROBLEMA: Construir URL correctamente
        const baseUrl = '/api/calls';
        let url;
        
        if (endpoint.startsWith('/')) {
            url = `${baseUrl}${endpoint}`;
        } else {
            url = `${baseUrl}/${endpoint}`;
        }
        
        console.log(`🌐 API Call: ${method} ${url}`);
        
        const options = {
            method,
            headers: {
                'Content-Type': 'application/json'
            }
        };
        
        if (body) {
            options.body = JSON.stringify(body);
            console.log('📤 Body:', body);
        }

        try {
            const response = await fetch(url, options);
            console.log(`📡 Response: ${response.status} ${response.statusText}`);
            
            if (!response.ok) {
                let errorData;
                try {
                    errorData = await response.json();
                } catch {
                    errorData = { 
                        error: `Error HTTP ${response.status}: ${response.statusText}` 
                    };
                }
                throw new Error(errorData.error || `Error ${response.status}`);
            }
            
            const result = await response.json();
            console.log('📥 Result:', result);
            return result;
            
        } catch (error) {
            console.error(`❌ API call failed: ${method} ${url}`, error);
            
            // No mostrar toast para todos los errores, solo loggear
            if (error.message.includes('404')) {
                console.warn('⚠️ Endpoint no encontrado - esto es normal si la API no está implementada aún');
            } else {
                this.showToast(`Error en la API: ${error.message}`, 'error');
            }
            
            throw error;
        }
    }

    connectWebSocket() {
        // WebSocket deshabilitado temporalmente - usando solo HTTP fallback
        console.log('⚠️ WebSocket deshabilitado, usando HTTP fallback');
        this.updateConnectionStatus(false);
        return;
        
        // Código WebSocket comentado
        /*
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/calls`;
        
        console.log(`🔌 Conectando WebSocket: ${wsUrl}`);
        
        try {
            this.state.socket = new WebSocket(wsUrl);

            this.state.socket.onopen = () => {
                console.log('✅ WebSocket conectado.');
                this.state.retryCount = 0;
                this.updateConnectionStatus(true);
                this.getStatus();
            };

            this.state.socket.onmessage = (event) => {
                console.log('📨 Mensaje WebSocket:', event.data);
                try {
                    const data = JSON.parse(event.data);
                    this.handleWebSocketMessage(data);
                } catch (error) {
                    console.error('❌ Error parseando mensaje WebSocket:', error);
                }
            };

            this.state.socket.onclose = (event) => {
                console.log('🔌 WebSocket desconectado.', event.code, event.reason);
                this.updateConnectionStatus(false);
                
                if (this.state.retryCount < this.state.maxRetries) {
                    console.log(`🔄 Intentando reconectar... (${this.state.retryCount + 1}/${this.state.maxRetries})`);
                    setTimeout(() => {
                        this.state.retryCount++;
                        this.connectWebSocket();
                    }, this.state.retryDelay);
                } else {
                    console.warn('⚠️ Máximo número de reintentos alcanzado para WebSocket');
                }
            };

            this.state.socket.onerror = (error) => {
                console.error('❌ Error de WebSocket:', error);
                this.updateConnectionStatus(false);
            };
            
        } catch (error) {
            console.error('❌ Error creando WebSocket:', error);
            this.updateConnectionStatus(false);
        }
        */
    }

    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'status_update':
                this.updateSystemStatus(data.data);
                break;
            case 'lead_update':
                this.updateLeadInTable(data.data);
                break;
            case 'call_log':
                console.log('Log de llamada:', data.message);
                break;
            case 'error':
                this.showToast(data.message, 'error');
                break;
            case 'initial_status':
                this.updateSystemStatus(data.data);
                break;
            case 'all_leads':
                // Normalizar datos antes de asignar
                this.state.leads = this.normalizeLeadsData(data.data);
                console.log('📄 Leads normalizados:', this.state.leads);
                this.updateFilters();
                this.renderTable();
                break;
            case 'toast':
                this.showToast(data.message, data.category || 'info');
                break;
        }
    }

    // Función para normalizar datos de leads
    normalizeLeadsData(leads) {
        return leads.map(lead => {
            // Normalizar campos que pueden ser null
            return {
                ...lead,
                ciudad: lead.ciudad || 'N/A',
                nombre: lead.nombre || 'N/A',
                apellidos: lead.apellidos || '',
                nombre_clinica: lead.nombre_clinica || 'N/A',
                // Mapear campos para compatibilidad
                prioridad: lead.call_priority || 3,
                selected: Boolean(lead.selected_for_calling),
                // Asegurar que selected_for_calling sea boolean
                selected_for_calling: Boolean(lead.selected_for_calling),
                // Formatear fechas
                last_call_time: lead.last_call_attempt,
                // Añadir campo nombre_lead para compatibilidad
                nombre_lead: `${lead.nombre || 'N/A'} ${lead.apellidos || ''}`.trim()
            };
        });
    }

    updateConnectionStatus(isConnected) {
        if (!this.elements.connectionStatus) return;
        const icon = this.elements.connectionStatus.querySelector('i');
        if (isConnected) {
            this.elements.connectionStatus.classList.remove('text-danger', 'text-warning');
            this.elements.connectionStatus.classList.add('text-success');
            this.elements.connectionStatus.innerHTML = '<i class="bi bi-check-circle-fill"></i> Conectado';
        } else {
            this.elements.connectionStatus.classList.remove('text-success', 'text-warning');
            this.elements.connectionStatus.classList.add('text-danger');
            this.elements.connectionStatus.innerHTML = '<i class="bi bi-x-circle-fill"></i> Desconectado';
        }
    }

    async sendMessage(type, payload = {}) {
        // Si WebSocket está disponible, úsalo
        if (this.state.socket && this.state.socket.readyState === WebSocket.OPEN) {
            this.state.socket.send(JSON.stringify({ type, ...payload }));
            return;
        }
        // Fallback a peticiones HTTP para los mensajes básicos
        switch (type) {
            case 'get_all_leads': {
                try {
                    console.log('🚀 Cargando leads desde API...');
                    const resp = await this.apiCall('GET', '/leads');
                    const leads = resp.leads || [];
                    console.log('📊 API devuelve', leads.length, 'leads');
                    this.handleWebSocketMessage({ type: 'all_leads', data: leads });
                } catch (error) {
                    console.error('❌ Error cargando leads:', error);
                    this.showToast('Error cargando leads: ' + error.message, 'error');
                }
                break;
            }
            case 'get_status': {
                try {
                    const data = await this.apiCall('GET', '/status');
                    this.handleWebSocketMessage({ type: 'initial_status', data });
                } catch (_) {}
                break;
            }
            case 'mark_lead': {
                // payload: { lead_id, selected }
                try {
                    await this.apiCall('POST', '/leads/select', {
                        lead_ids: [payload.lead_id],
                        selected: payload.selected
                    });
                } catch (error) {
                    console.error('❌ Error marcando lead:', error);
                }
                break;
            }
            case 'mark_leads': {
                // payload: { lead_ids, selected }
                try {
                    await this.apiCall('POST', '/leads/select', {
                        lead_ids: payload.lead_ids,
                        selected: payload.selected
                    });
                } catch (error) {
                    console.error('❌ Error marcando leads:', error);
                }
                break;
            }
            default:
                console.warn(`Mensaje ${type} ignorado en modo fallback.`);
        }
    }

    async loadInitialData() {
        if (this.state.isLoading) {
            console.warn('⚠️ Ya se están cargando datos iniciales');
            return;
        }
        
        this.setLoading(true);
        try {
            await this.sendMessage('get_all_leads');
            await this.getStatus();
        } catch (error) {
            this.showToast('Error al cargar datos iniciales.', 'error');
        } finally {
            this.setLoading(false);
        }
    }

    async getStatus() {
        await this.sendMessage('get_status');
    }

    updateSystemStatus(data) {
        const wasRunning = this.state.isSystemRunning;
        this.state.isSystemRunning = data.is_running;
        
        this.elements.systemStatus.textContent = data.is_running ? 'Activo' : 'Detenido';
        this.elements.systemStatus.className = `badge fs-6 ${data.is_running ? 'bg-success' : 'bg-danger'}`;
        this.elements.startCallsBtn.disabled = data.is_running;
        this.elements.stopCallsBtn.disabled = !data.is_running;

        // Clear loading state when system stops
        if (wasRunning && !data.is_running) {
            this.showLoader(this.elements.startCallsBtn, false);
            this.showLoader(this.elements.stopCallsBtn, false);
            
            // Deselect all leads when calls complete
            this.deselectAllLeads();
            
            console.log('✅ Sistema detenido - leads deseleccionados y loading limpiado');
        }

        if (data.stats) {
            this.updateStats(data.stats);
        }
        
        if (data.is_running) {
            this.elements.progressSection.style.display = 'block';
            this.updateProgressBar(data.stats);
        } else {
            this.elements.progressSection.style.display = 'none';
        }
    }

    updateStats(stats) {
        this.elements.totalCallsCount.textContent = stats.total || 0;
        this.elements.successCallsCount.textContent = stats.completed || 0;
        this.elements.failedCallsCount.textContent = stats.error || 0;
        this.elements.activeCallsCount.textContent = stats.in_progress || 0;
    }

    updateProgressBar(stats) {
        const total = stats.total || 0;
        const completed = (stats.completed || 0) + (stats.error || 0);
        const percentage = total > 0 ? (completed / total) * 100 : 0;

        this.elements.progressBar.style.width = `${percentage}%`;
        this.elements.progressBar.setAttribute('aria-valuenow', percentage);
        this.elements.progressText.textContent = `${completed} / ${total}`;
    }

    async startCalling() {
        console.log('🚀 === INICIANDO SISTEMA DE LLAMADAS ===');
        
        const selectedIds = this.getSelectedLeadIds();
        console.log('IDs seleccionados:', selectedIds);
        
        if (selectedIds.length === 0) {
            console.warn('⚠️ No hay leads seleccionados');
            this.showToast('Debe seleccionar al menos un lead para iniciar las llamadas.', 'warning');
            return;
        }
        
        console.log(`✅ Iniciando llamadas para ${selectedIds.length} leads`);

        this.showLoader(this.elements.startCallsBtn, true);
        
        try {
            // Debug detallado del modo de prueba
            console.log('🔍 === DEBUG MODO PRUEBA ===');
            console.log('testModeSwitch element:', this.elements.testModeSwitch);
            console.log('overridePhoneInput element:', this.elements.overridePhoneInput);
            
            const testModeEnabled = this.elements.testModeSwitch?.checked || false;
            const overridePhone = this.elements.overridePhoneInput?.value || '';
            
            console.log('🧪 Modo prueba enabled:', testModeEnabled);
            console.log('📞 Teléfono override value:', `'${overridePhone}'`);
            console.log('📞 Override phone length:', overridePhone.length);

            const config = {
                max_concurrent: this.config.maxConcurrentCalls,
                selected_leads: selectedIds,
                override_phone: testModeEnabled ? overridePhone : null
            };
            
            console.log('🔧 Configuración FINAL de llamadas:', JSON.stringify(config, null, 2));

            if (testModeEnabled && !overridePhone) {
                console.error('❌ Modo prueba activo pero sin teléfono');
                this.showToast('Por favor, introduce un número de teléfono para el modo de prueba.', 'warning');
                this.showLoader(this.elements.startCallsBtn, false);
                return;
            }
            
            if (testModeEnabled && overridePhone) {
                console.warn('🧪 MODO PRUEBA CONFIRMADO - Se enviará override_phone:', overridePhone);
            }

            console.log('📡 Enviando petición POST /api/calls/start...');
            const response = await this.apiCall('POST', '/start', config);
            console.log('📥 Respuesta recibida:', response);
            
            if (response.success) {
                console.log('✅ Sistema iniciado correctamente');
                console.log('📢 SUCCESS: Sistema de llamadas iniciado.');
                // this.showToast('Sistema de llamadas iniciado.', 'success');
            } else {
                console.error('❌ Error:', response.error);
                console.log('📢 ERROR:', response.error || 'No se pudo iniciar el sistema.');
                // this.showToast(response.error || 'No se pudo iniciar el sistema.', 'error');
            }
        } catch (error) {
            console.error('❌ Error en startCalling:', error);
            this.showToast('Error iniciando sistema: ' + error.message, 'error');
        } finally {
            this.showLoader(this.elements.startCallsBtn, false);
        }
    }

    async stopCalling() {
        this.showLoader(this.elements.stopCallsBtn, true);
        try {
            const response = await this.apiCall('POST', '/stop');
            if (response.success) {
                this.showToast('Sistema de llamadas detenido.', 'info');
            } else {
                this.showToast(response.error || 'No se pudo detener el sistema.', 'error');
            }
        } catch (error) {
            // apiCall ya muestra el toast
        } finally {
            this.showLoader(this.elements.stopCallsBtn, false);
        }
    }

    renderTable() {
        console.log('🎨 Renderizando tabla...');
        console.log('Total leads en state:', this.state.leads.length);
        
        this.elements.leadsTableBody.innerHTML = '';
        const filteredLeads = this.getFilteredLeads();
        console.log('Leads después de filtros:', filteredLeads.length);
        
        const paginatedLeads = this.paginate(filteredLeads, this.state.currentPage, this.state.itemsPerPage);
        console.log('Leads paginados:', paginatedLeads.length);

        if (paginatedLeads.length === 0) {
            this.elements.leadsTableBody.innerHTML = `
                <tr>
                    <td colspan="10" class="text-center py-4">
                        <i class="bi bi-info-circle-fill fs-3 text-muted"></i>
                        <p class="mt-2 mb-0">No hay leads que coincidan con los filtros.</p>
                    </td>
                </tr>`;
        } else {
            paginatedLeads.forEach(lead => {
                const row = this.createLeadRow(lead);
                this.elements.leadsTableBody.appendChild(row);
            });
        }
        this.renderPagination(filteredLeads.length);
        this.updateLeadsInfo(filteredLeads.length);
        this.updateMasterCheckbox();
        
        console.log('✅ Tabla renderizada correctamente');
    }

    createLeadRow(lead) {
        console.log('🧑 Creando fila para lead:', lead.id, lead.nombre_lead);
        
        const row = document.createElement('tr');
        row.dataset.leadId = lead.id;
        row.className = lead.selected_for_calling ? 'table-primary' : '';

        let statusClass = 'bg-secondary';
        if (lead.call_status === 'completed') statusClass = 'bg-success';
        else if (['in_progress', 'calling', 'selected'].includes(lead.call_status)) statusClass = 'bg-warning text-dark';
        else if (['error', 'failed', 'busy', 'no_answer'].includes(lead.call_status)) statusClass = 'bg-danger';

        const lastCallTime = lead.last_call_time ? new Date(lead.last_call_time).toLocaleString('es-ES') : 'Nunca';
        const callStatus = (lead.call_status || 'pendiente').replace('_', ' ');

        row.innerHTML = `
            <td><input type="checkbox" class="form-check-input lead-checkbox" data-lead-id="${lead.id}" ${lead.selected_for_calling ? 'checked' : ''}></td>
            <td>${lead.nombre_lead || 'N/A'}</td>
            <td>${lead.telefono || 'N/A'}</td>
            <td>${lead.status_level_1 || 'N/A'}</td>
            <td>${lead.status_level_2 || 'N/A'}</td>
            <td><span class="badge ${statusClass}">${callStatus}</span></td>
            <td>${lead.call_priority || 3}</td>
            <td>${lead.call_attempts_count || 0}</td>
            <td>${lastCallTime}</td>
            <td>
                <button class="btn btn-sm btn-outline-info" title="Ver Detalles" onclick="window.CallsManager.showLeadDetails('${lead.id}')">
                    <i class="bi bi-eye"></i>
                </button>
            </td>
        `;
        
        // Añadir event listener al checkbox
        const checkbox = row.querySelector('.lead-checkbox');
        if (checkbox) {
            checkbox.addEventListener('change', (e) => {
                this.toggleLeadSelection(lead.id, e.target.checked);
            });
        }
        
        return row;
    }

    updateLeadInTable(lead) {
        const index = this.state.leads.findIndex(l => l.id === lead.id);
        if (index !== -1) {
            this.state.leads[index] = { ...this.state.leads[index], ...lead };
        }
        this.renderTable();
    }

    showLeadDetails(leadId) {
        console.log('🔍 Mostrando detalles del lead:', leadId);
        const lead = this.state.leads.find(l => l.id == leadId);
        if (lead) {
            // Por ahora, solo mostrar en consola
            console.log('Detalles del lead:', lead);
            this.showToast(`Detalles del lead ${lead.nombre_lead}: Tel: ${lead.telefono}`, 'info');
        }
    }

    getSelectedLeadIds() {
        console.log('📊 Obteniendo IDs de leads seleccionados...');
        const selectedIds = this.state.leads
            .filter(lead => lead.selected_for_calling)
            .map(lead => lead.id);
        console.log(`✅ Encontrados ${selectedIds.length} leads seleccionados:`, selectedIds);
        return selectedIds;
    }

    selectAllLeads(selected) {
        console.log(`📊 ${selected ? 'Seleccionando' : 'Deseleccionando'} todos los leads visibles...`);
        
        // Obtener leads visibles (filtrados y paginados)
        const filteredLeads = this.getFilteredLeads();
        const paginatedLeads = this.paginate(filteredLeads, this.state.currentPage, this.state.itemsPerPage);
        
        const leadIds = [];
        
        // Actualizar estado local
        paginatedLeads.forEach(lead => {
            const leadInState = this.state.leads.find(l => l.id === lead.id);
            if (leadInState) {
                leadInState.selected_for_calling = selected;
                leadInState.selected = selected; // Para compatibilidad
                leadIds.push(lead.id);
            }
        });
        
        // Enviar al servidor
        if (leadIds.length > 0) {
            this.sendMessage('mark_leads', { lead_ids: leadIds, selected });
        }
        
        // Re-renderizar tabla
        this.renderTable();
        
        console.log(`✅ ${selected ? 'Seleccionados' : 'Deseleccionados'} ${leadIds.length} leads`);
    }

    resetLeads() {
        console.log('🔄 Reiniciando estado de leads...');
        this.showConfirm(
            'Reiniciar Leads', 
            '¿Estás seguro de que quieres reiniciar el estado de todos los leads?'
        ).then(confirmed => {
            if (confirmed) {
                // Llamar al endpoint de reset
                this.apiCall('POST', '/leads/reset', {
                    reset_attempts: true,
                    reset_selection: false
                }).then(() => {
                    this.showToast('Estado de leads reiniciado correctamente', 'success');
                    this.loadInitialData(); // Recargar datos
                }).catch(error => {
                    this.showToast('Error reiniciando leads: ' + error.message, 'error');
                });
            }
        });
    }

    applyFilters() {
        console.log('🔍 Aplicando filtros...');
        
        // Leer valores de los filtros
        this.state.filters.city = this.elements.cityFilter?.value || '';
        this.state.filters.status = this.elements.statusFilter?.value || '';
        this.state.filters.priority = this.elements.priorityFilter?.value || '';
        this.state.filters.selected = this.elements.selectedFilter?.checked || false;
        
        console.log('Filtros aplicados:', this.state.filters);
        
        // Resetear a la primera página
        this.state.currentPage = 1;
        
        // Re-renderizar tabla
        this.renderTable();
    }

    toggleLeadSelection(leadId, isSelected) {
        console.log(`🔄 Cambiando selección del lead ${leadId} a ${isSelected}`);
        const lead = this.state.leads.find(l => l.id === leadId);
        if (lead) {
            lead.selected_for_calling = isSelected;
            lead.selected = isSelected; // Para compatibilidad
            
            // Enviar al servidor
            this.sendMessage('mark_lead', { lead_id: leadId, selected: isSelected });
            
            // Re-renderizar tabla para actualizar estilos
            this.renderTable();
        }
    }

    toggleAllCheckboxes(isChecked) {
        const checkboxes = this.elements.leadsTableBody.querySelectorAll('.lead-checkbox');
        const visibleLeadIds = Array.from(checkboxes).map(cb => parseInt(cb.dataset.leadId));
        
        this.state.leads.forEach(lead => {
            if (visibleLeadIds.includes(lead.id)) {
                lead.selected = isChecked;
            }
        });

        this.sendMessage('mark_leads', { lead_ids: visibleLeadIds, selected: isChecked });
        this.renderTable();
    }

    updateMasterCheckbox() {
        const checkboxes = this.elements.leadsTableBody.querySelectorAll('.lead-checkbox');
        if (checkboxes.length === 0) {
            this.elements.masterCheckbox.checked = false;
            this.elements.masterCheckbox.indeterminate = false;
            return;
        }
        const checkedCount = Array.from(checkboxes).filter(cb => cb.checked).length;
        if (checkedCount === 0) {
            this.elements.masterCheckbox.checked = false;
            this.elements.masterCheckbox.indeterminate = false;
        } else if (checkedCount === checkboxes.length) {
            this.elements.masterCheckbox.checked = true;
            this.elements.masterCheckbox.indeterminate = false;
        } else {
            this.elements.masterCheckbox.checked = false;
            this.elements.masterCheckbox.indeterminate = true;
        }
    }

    getSelectedLeadIds() {
        // Get IDs of leads that are currently selected for calling
        return this.state.leads
            .filter(lead => lead.selected_for_calling)
            .map(lead => lead.id);
    }

    getSelectedCount() {
        // Count leads that are selected for calling
        return this.state.leads.filter(lead => lead.selected_for_calling).length;
    }

    selectAllLeads(select) {
        // Select or deselect all visible leads
        const filteredLeads = this.getFilteredLeads();
        const paginatedLeads = this.paginate(filteredLeads, this.state.currentPage, this.state.itemsPerPage);
        
        paginatedLeads.forEach(lead => {
            lead.selected_for_calling = select;
            lead.selected = select; // For compatibility
        });
        
        // Update the UI
        this.renderTable();
        
        console.log(`📎 ${select ? 'Seleccionados' : 'Deseleccionados'} ${paginatedLeads.length} leads visibles`);
    }

    deselectAllLeads() {
        // Deselect all leads in the state
        this.state.leads.forEach(lead => {
            lead.selected_for_calling = false;
            lead.selected = false; // For compatibility
        });
        
        // Update the UI
        this.renderTable();
        
        console.log('🚫 Todos los leads deseleccionados');
    }

    showLoader(element, show) {
        if (!element) return;
        
        if (show) {
            // Store original text and show loading
            if (!element.dataset.originalText) {
                element.dataset.originalText = element.innerHTML;
            }
            element.innerHTML = '<i class="bi bi-arrow-clockwise spin"></i> Cargando...';
            element.disabled = true;
        } else {
            // Restore original text and enable
            if (element.dataset.originalText) {
                element.innerHTML = element.dataset.originalText;
                delete element.dataset.originalText;
            }
            element.disabled = false;
        }
    }

    async sendMessage(type, data = {}) {
        // Since WebSocket is disabled, use HTTP API calls instead
        console.log(`📡 sendMessage: ${type}`);
        
        try {
            switch (type) {
                case 'get_all_leads':
                    const response = await this.apiCall('GET', '/leads');
                    if (response.success && response.data) {
                        this.state.leads = this.normalizeLeadsData(response.data);
                        // Solo actualizar filtros y tabla si no están ya inicializados
                        if (this.elements.leadsTableBody) {
                            this.updateFilters();
                            this.renderTable();
                        }
                    }
                    break;
                case 'get_status':
                    const statusResponse = await this.apiCall('GET', '/status');
                    if (statusResponse.success) {
                        this.updateSystemStatus(statusResponse.data);
                    }
                    break;
                case 'mark_lead':
                    await this.apiCall('POST', '/mark_lead', data);
                    break;
                case 'mark_leads':
                    await this.apiCall('POST', '/mark_leads', data);
                    break;
                default:
                    console.warn('Tipo de mensaje no reconocido:', type);
            }
        } catch (error) {
            console.error('Error en sendMessage:', error);
        }
    }

    resetLeads() {
        // Reset all leads to default state
        this.state.leads.forEach(lead => {
            lead.selected_for_calling = false;
            lead.selected = false;
            lead.call_status = 'no_selected';
        });
        
        this.renderTable();
        this.showNotification('Leads reiniciados', 'info');
        console.log('🔄 Leads reiniciados');
    }

    showLeadDetails(leadId) {
        const lead = this.state.leads.find(l => l.id == leadId);
        if (!lead) {
            this.showNotification('Lead no encontrado', 'error');
            return;
        }
        
        // Create details content
        const detailsHtml = `
            <div class="row">
                <div class="col-md-6">
                    <h6>Información Personal</h6>
                    <p><strong>Nombre:</strong> ${lead.nombre_lead || 'N/A'}</p>
                    <p><strong>Teléfono:</strong> ${lead.telefono || 'N/A'}</p>
                    <p><strong>Email:</strong> ${lead.email || 'N/A'}</p>
                </div>
                <div class="col-md-6">
                    <h6>Estados</h6>
                    <p><strong>Estado 1:</strong> ${lead.status_level_1 || 'N/A'}</p>
                    <p><strong>Estado 2:</strong> ${lead.status_level_2 || 'N/A'}</p>
                    <p><strong>Estado Llamada:</strong> ${lead.call_status || 'N/A'}</p>
                </div>
            </div>
            <div class="row mt-3">
                <div class="col-12">
                    <h6>Información de Llamadas</h6>
                    <p><strong>Prioridad:</strong> ${lead.call_priority || 3}</p>
                    <p><strong>Intentos:</strong> ${lead.call_attempts_count || 0}</p>
                    <p><strong>Última Llamada:</strong> ${lead.last_call_attempt ? new Date(lead.last_call_attempt).toLocaleString('es-ES') : 'Nunca'}</p>
                </div>
            </div>
        `;
        
        // Update modal content
        if (this.elements.leadDetailsContent) {
            this.elements.leadDetailsContent.innerHTML = detailsHtml;
        }
        
        // Show modal
        if (this.elements.leadDetailsModal) {
            const modal = new bootstrap.Modal(this.elements.leadDetailsModal);
            modal.show();
        }
    }

    async loadConfiguration() {
        try {
            const response = await this.apiCall('GET', '/config');
            if (response.success && response.data) {
                this.config = { ...this.config, ...response.data };
                console.log('⚙️ Configuración cargada:', this.config);
            }
        } catch (error) {
            console.warn('Error cargando configuración:', error);
        }
    }

    async saveConfiguration() {
        try {
            const config = {
                maxConcurrentCalls: parseInt(this.elements.maxConcurrentCalls?.value) || 3
            };
            
            const response = await this.apiCall('POST', '/config', config);
            if (response.success) {
                this.config = { ...this.config, ...config };
                this.showNotification('Configuración guardada', 'success');
                console.log('⚙️ Configuración guardada:', config);
            }
        } catch (error) {
            this.showNotification('Error guardando configuración', 'error');
            console.error('Error guardando configuración:', error);
        }
    }

    paginate(items, page, perPage) {
        const start = (page - 1) * perPage;
        const end = start + perPage;
        return items.slice(start, end);
    }

    renderPagination(totalItems) {
        this.elements.pagination.innerHTML = '';
        const pageCount = Math.ceil(totalItems / this.state.itemsPerPage);
        if (pageCount <= 1) return;

        for (let i = 1; i <= pageCount; i++) {
            const li = document.createElement('li');
            li.className = `page-item ${i === this.state.currentPage ? 'active' : ''}`;
            const a = document.createElement('a');
            a.className = 'page-link';
            a.href = '#';
            a.innerText = i;
            a.addEventListener('click', (e) => {
                e.preventDefault();
                this.state.currentPage = i;
                this.renderTable();
            });
            li.appendChild(a);
            this.elements.pagination.appendChild(li);
        }
    }

    updateLeadsInfo(totalFiltered) {
        if (!this.elements.leadsInfo) return;
        
        // Calcular información de paginación
        const start = (this.state.currentPage - 1) * this.state.itemsPerPage + 1;
        const end = Math.min(start + this.state.itemsPerPage - 1, totalFiltered);
        const selectedCount = this.getSelectedCount();
        
        this.elements.leadsInfo.textContent = `Mostrando ${start}-${end} de ${totalFiltered} leads | ${selectedCount} seleccionados`;
        console.log(`📊 Info actualizada: ${start}-${end} de ${totalFiltered}, ${selectedCount} seleccionados`);
    }

    updatePagination() {
        if (!this.elements.pagination) return;
        const { offset, limit, total } = this.state.pagination;
        const currentPage = Math.floor(offset / limit) + 1;
        const totalPages = Math.ceil(total / limit);
        let html = `<li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
                       <a class="page-link" href="#" data-page="${currentPage - 1}"><i class="bi bi-chevron-left"></i></a></li>`;
        const startPage = Math.max(1, currentPage - 2);
        const endPage = Math.min(totalPages, currentPage + 2);
        for (let page = startPage; page <= endPage; page++) {
            html += `<li class="page-item ${page === currentPage ? 'active' : ''}">
                        <a class="page-link" href="#" data-page="${page}">${page}</a></li>`;
        }
        html += `<li class="page-item ${currentPage === totalPages ? 'disabled' : ''}">
                    <a class="page-link" href="#" data-page="${currentPage + 1}"><i class="bi bi-chevron-right"></i></a></li>`;
        this.elements.pagination.innerHTML = html;
        this.elements.pagination.querySelectorAll('.page-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const page = parseInt(e.target.dataset.page);
                if (page && page !== currentPage) this.goToPage(page);
            });
        });
    }

    async goToPage(page) {
        this.state.pagination.offset = (page - 1) * this.state.pagination.limit;
        await this.loadLeads();
    }

    async testConnection() {
        try {
            if (this.elements.testConnectionBtn) this.showLoader(this.elements.testConnectionBtn, true);
            const response = await this.apiCall('GET', '/test/connection');
            if (response.success && response.pearl_connection) {
                this.updateConnectionStatus(true);
                if (this.elements.pearlConnectionStatus) this.elements.pearlConnectionStatus.value = 'Conectado correctamente';
                this.showNotification('Conexión con Pearl AI exitosa', 'success');
            } else {
                this.updateConnectionStatus(false);
                if (this.elements.pearlConnectionStatus) this.elements.pearlConnectionStatus.value = 'Error de conexión';
                this.showNotification('Error conectando con Pearl AI', 'error');
            }
        } catch (error) {
            console.error('Error probando conexión:', error);
            this.updateConnectionStatus(false);
            this.showNotification('Error al probar conexión', 'error');
        } finally {
            if (this.elements.testConnectionBtn) this.showLoader(this.elements.testConnectionBtn, false);
        }
    }

    // Método saveConfiguration duplicado - REMOVIDO (usar el de arriba)

    handleKeyboard(e) {
        if (e.ctrlKey && e.key === 'r') { e.preventDefault(); this.refreshAll(); }
        if (e.code === 'Space' && e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
            e.preventDefault();
            this.state.isRunning ? this.stopCalling() : this.startCalling();
        }
    }

    async refreshAll() {
        this.showLoader(this.elements.refreshBtn, true);
        try {
            await this.loadInitialData();
            this.showNotification('Datos actualizados', 'info');
        } catch (error) {
            console.error('Error en refresh:', error);
            this.showNotification('Error actualizando datos', 'error');
        } finally {
            this.showLoader(this.elements.refreshBtn, false);
        }
    }

    startAutoRefresh() {
        this.stopAutoRefresh();
        if (this.config.autoRefresh) {
            this.intervals.status = setInterval(() => this.updateSystemStatus(), this.config.refreshInterval);
            this.intervals.leads = setInterval(() => this.loadLeads(), this.config.refreshInterval * 2);
        }
    }

    stopAutoRefresh() {
        Object.values(this.intervals).forEach(interval => { if (interval) clearInterval(interval); });
        this.intervals = { status: null, leads: null };
    }

    // Método apiCall duplicado - REMOVIDO (usar el de arriba)

    applyFilters() {
        // Update filters state from UI elements
        this.state.filters.estado1 = this.elements.estado1Filter?.value || '';
        this.state.filters.estado2 = this.elements.estado2Filter?.value || '';
        this.state.filters.status = this.elements.statusFilter?.value || '';
        this.state.filters.priority = this.elements.priorityFilter?.value || '';
        this.state.filters.selected = this.elements.selectedFilter?.value || '';
        
        // Reset to first page when applying filters
        this.state.currentPage = 1;
        
        // Re-render table with filters applied
        this.renderTable();
        
        console.log('🔍 Filtros aplicados:', this.state.filters);
    }

    clearFilters() {
        // Reset all filter values
        this.state.filters = {
            estado1: '',
            estado2: '',
            status: '',
            priority: '',
            selected: ''
        };
        
        // Reset UI elements
        if (this.elements.estado1Filter) this.elements.estado1Filter.value = '';
        if (this.elements.estado2Filter) this.elements.estado2Filter.value = '';
        if (this.elements.statusFilter) this.elements.statusFilter.value = '';
        if (this.elements.priorityFilter) this.elements.priorityFilter.value = '';
        if (this.elements.selectedFilter) this.elements.selectedFilter.value = '';
        
        // Reset to first page
        this.state.currentPage = 1;
        
        // Re-render table
        this.renderTable();
        
        console.log('🧹 Filtros limpiados');
    }

    showNotification(message, type = 'info') {
        const toastContainer = document.getElementById('toastContainer');
        if (!toastContainer) {
            // Fallback: usar console.log si no hay contenedor de toasts
            console.log(`📢 ${type.toUpperCase()}: ${message}`);
            return;
        }
        
        const types = {
            success: { icon: 'check-circle-fill', class: 'bg-success' },
            error: { icon: 'x-circle-fill', class: 'bg-danger' },
            warning: { icon: 'exclamation-triangle-fill', class: 'bg-warning' },
            info: { icon: 'info-circle-fill', class: 'bg-info' }
        };
        const { icon, class: bgClass } = types[type] || types.info;
        
        const toastHtml = `<div class="toast align-items-center text-white border-0 ${bgClass}" role="alert">
                <div class="d-flex"><div class="toast-body"><i class="bi bi-${icon} me-2"></i>${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button></div></div>`;
        
        const toastElement = document.createElement('div');
        toastElement.innerHTML = toastHtml;
        toastContainer.appendChild(toastElement.firstElementChild);
        
        // Verificar que Bootstrap esté disponible
        if (typeof bootstrap !== 'undefined' && bootstrap.Toast) {
            const toast = new bootstrap.Toast(toastElement.firstElementChild, { delay: 5000 });
            toast.show();
            toastElement.firstElementChild.addEventListener('hidden.bs.toast', () => toastElement.remove());
        } else {
            // Fallback: mostrar por 5 segundos sin Bootstrap
            setTimeout(() => {
                if (toastElement.firstElementChild.parentNode) {
                    toastElement.firstElementChild.parentNode.removeChild(toastElement.firstElementChild);
                }
            }, 5000);
        }
    }

    async showConfirm(title, message) {
        return new Promise((resolve) => {
            const result = confirm(`${title}\n\n${message}`);
            resolve(result);
        });
    }

    showLoader(button, show) {
        if (!button) return;
        if (show) {
            button.disabled = true;
            const originalHtml = button.innerHTML;
            button.dataset.originalHtml = originalHtml;
            button.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Cargando...';
        } else {
            button.disabled = false;
            button.innerHTML = button.dataset.originalHtml || button.innerHTML;
        }
    }

    // Método loadConfiguration - AGREGADO
    async loadConfiguration() {
        try {
            console.log('📡 Cargando configuración...');
            
            // Intentar cargar configuración desde la API
            const response = await this.apiCall('GET', '/configuration');
            
            if (response && response.success && response.configuration) {
                this.config = { ...this.config, ...response.configuration };
                console.log('✅ Configuración cargada desde API:', this.config);
                
                // Actualizar UI con la configuración cargada
                if (this.elements.maxConcurrentCalls) {
                    this.elements.maxConcurrentCalls.value = this.config.maxConcurrentCalls || 3;
                }
            }
        } catch (error) {
            console.warn('⚠️ No se pudo cargar configuración desde API, usando valores por defecto:', error);
            
            // Usar configuración por defecto
            this.config = {
                maxConcurrentCalls: 3,
                retryAttempts: 3,
                retryDelay: 30,
                testMode: false,
                ...this.config
            };
            
            console.log('🔧 Usando configuración por defecto:', this.config);
        }
    }

    // Método saveConfiguration - CORREGIDO
    async saveConfiguration() {
        try {
            const configForm = document.getElementById('configForm');
            if (!configForm) {
                // Si no hay formulario, usar valores actuales
                console.log('💾 Guardando configuración actual...');
                
                const config = {
                    maxConcurrentCalls: this.elements.maxConcurrentCalls ? 
                        parseInt(this.elements.maxConcurrentCalls.value) || 3 : 3
                };
                
                const response = await this.apiCall('POST', '/configuration', config);
                
                if (response && response.success) {
                    this.config = { ...this.config, ...config };
                    this.showToast('Configuración guardada correctamente', 'success');
                }
                return;
            }
            
            const formData = new FormData(configForm);
            const config = Object.fromEntries(formData.entries());
            
            // Convertir valores numéricos
            config.maxConcurrentCalls = parseInt(config.maxConcurrentCalls) || 3;
            config.retryAttempts = parseInt(config.retryAttempts) || 3;
            config.retryDelay = parseInt(config.retryDelay) || 30;
            
            console.log('💾 Guardando configuración:', config);
            
            const response = await this.apiCall('POST', '/configuration', config);
            
            if (response && response.success) {
                this.config = { ...this.config, ...config };
                this.showToast('Configuración guardada correctamente', 'success');
                
                // Cerrar modal si existe
                const configModal = this.elements.configModal;
                if (configModal) {
                    const modal = bootstrap.Modal.getInstance(configModal);
                    if (modal) modal.hide();
                }
            }
        } catch (error) {
            console.error('❌ Error al guardar configuración:', error);
            this.showToast('Error al guardar configuración: ' + error.message, 'error');
        }
    }

    // Método testConnection - CORREGIDO
    async testConnection() {
        const button = this.elements.testConnectionBtn;
        this.showLoader(button, true);
        
        try {
            console.log('🔗 Probando conexión...');
            
            const response = await this.apiCall('GET', '/test-connection');
            
            if (response && response.success) {
                this.showToast('Conexión exitosa con Pearl API', 'success');
                if (this.elements.pearlConnectionStatus) {
                    this.elements.pearlConnectionStatus.innerHTML = 
                        '<span class="badge bg-success"><i class="bi bi-check-circle"></i> Conectado</span>';
                }
            } else {
                this.showToast('Error de conexión con Pearl API', 'error');
                if (this.elements.pearlConnectionStatus) {
                    this.elements.pearlConnectionStatus.innerHTML = 
                        '<span class="badge bg-danger"><i class="bi bi-x-circle"></i> Error</span>';
                }
            }
        } catch (error) {
            console.error('❌ Error probando conexión:', error);
            this.showToast('Error al probar conexión: ' + error.message, 'error');
            if (this.elements.pearlConnectionStatus) {
                this.elements.pearlConnectionStatus.innerHTML = 
                    '<span class="badge bg-danger"><i class="bi bi-x-circle"></i> Error</span>';
            }
        } finally {
            this.showLoader(button, false);
        }
    }
}

// Instancia global del CallsManager
window.CallsManager = new CallsManager();

// Prevenir múltiples inicializaciones
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        if (!window.CallsManager.state.isInitialized) {
            window.CallsManager.init();
        }
    });
} else {
    // Si el DOM ya está cargado
    if (!window.CallsManager.state.isInitialized) {
        window.CallsManager.init();
    }
}

// Instancia global y auto-inicialización
window.CallsManager = new CallsManager();
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => window.CallsManager.init());
} else {
    window.CallsManager.init();
}
window.addEventListener('beforeunload', () => window.CallsManager.destroy());
