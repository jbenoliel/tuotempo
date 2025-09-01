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
            },
            // Sistema de caché para reducir solicitudes redundantes
            apiCache: {},
            cacheTimeout: 5000, // 5 segundos de validez para la caché
            pendingRequests: {} // Para evitar solicitudes duplicadas
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
        
        // Agregar propiedades para control de frecuencia de actualizaciones
        this.state.lastStatusUpdate = 0;
        this.state.statusUpdateInterval = 3000; // 3 segundos mínimo entre actualizaciones
        
        // Aplicar throttling a getStatus para reducir consumo de recursos
        const originalGetStatus = this.getStatus.bind(this);
        this.getStatus = this.throttle(originalGetStatus, this.state.statusUpdateInterval);
        
        // Asegurar que los métodos utilitarios existen
        if (!this.setLoading) this.setLoading = (flag) => { this.state.isLoading = flag; };
        if (!this.showToast) this.showToast = (msg, type='info') => {
            console.log(`📢 ${type.toUpperCase()}: ${msg}`);
            this.showNotification(msg, type);
        };
        
        // Función para normalizar datos de leads
        if (!this.normalizeLeadsData) this.normalizeLeadsData = (leads) => {
            console.log('🔄 Normalizando', leads.length, 'leads...');
            const normalized = leads.map(lead => {
                return {
                    ...lead,
                    selected_for_calling: Boolean(lead.selected_for_calling),
                    call_status: lead.call_status || 'no_selected',
                    call_priority: lead.call_priority || 3,
                    call_attempts_count: lead.call_attempts_count || 0,
                    status_level_1: lead.status_level_1 || '',
                    status_level_2: lead.status_level_2 || '',
                    // Añadir campos de compatibilidad
                    selected: Boolean(lead.selected_for_calling),
                    nombre_lead: `${lead.nombre || ''} ${lead.apellidos || ''}`.trim()
                };
            });
            console.log('✅ Leads normalizados, seleccionados:', normalized.filter(l => l.selected_for_calling).length);
            return normalized;
        };
        
        // Asegurarse de que los métodos de filtros existan
        if (!this.getFilteredLeads) {
            console.log('⚠️ Método getFilteredLeads no definido, usando implementación por defecto');
        }
        
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
            
            // Actualizar dropdown de selección por estado
            this.updateStatusDropdown(estados1);
        };
        
        if (!this.updateStatusDropdown) this.updateStatusDropdown = (estados1) => {
            const dropdown = document.querySelector('#selectByStatusDropdown + .dropdown-menu');
            if (!dropdown) return;
            
            // Actualizar dinámicamente las opciones del dropdown
            const statusOptions = estados1.map(estado => {
                let icon = 'bi-circle';
                if (estado.includes('Volver')) icon = 'bi-telephone';
                else if (estado.includes('No Interesado')) icon = 'bi-x-circle';
                else if (estado.includes('Éxito')) icon = 'bi-check-circle';
                else if (estado.includes('Cita')) icon = 'bi-calendar-check';
                
                return `<li><a class="dropdown-item" href="#" onclick="callsManager.selectByStatus('status_level_1', '${estado}')">
                    <i class="bi ${icon}"></i> ${estado}
                </a></li>`;
            }).join('');
            
            dropdown.innerHTML = `
                <li><h6 class="dropdown-header">Estado 1 (Principal)</h6></li>
                ${statusOptions}
                <li><hr class="dropdown-divider"></li>
                <li><h6 class="dropdown-header">Estado Llamada</h6></li>
                <li><a class="dropdown-item" href="#" onclick="callsManager.selectByStatus('call_status', 'no_selected')">
                    <i class="bi bi-circle"></i> Sin llamar
                </a></li>
                <li><a class="dropdown-item" href="#" onclick="callsManager.selectByStatus('call_status', 'completed')">
                    <i class="bi bi-check-circle-fill"></i> Completadas
                </a></li>
                <li><a class="dropdown-item" href="#" onclick="callsManager.selectByStatus('call_status', 'error')">
                    <i class="bi bi-exclamation-circle"></i> Con Error
                </a></li>
                <li><hr class="dropdown-divider"></li>
                <li><h6 class="dropdown-header">Acciones</h6></li>
                <li><a class="dropdown-item" href="#" onclick="callsManager.showStatusSelectionModal()">
                    <i class="bi bi-gear"></i> Selección Avanzada
                </a></li>
            `;
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
            // Contadores del dashboard de llamadas
            totalCallsCount: document.getElementById('totalCallsCount'),
            successCallsCount: document.getElementById('successCallsCount'),
            failedCallsCount: document.getElementById('failedCallsCount'),
            activeCallsCount: document.getElementById('activeCallsCount'),
            // Contadores de leads en la tabla
            totalLeadsCount: document.getElementById('totalLeadsCount'),
            selectedLeadsCount: document.getElementById('selectedLeadsCount'),
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


    
    async apiCall(method, endpoint, body = null, useCache = false) {
        // Construir URL correctamente
        const baseUrl = '/api/calls';
        let url;
        
        if (endpoint.startsWith('/')) {
            url = `${baseUrl}${endpoint}`;
        } else {
            url = `${baseUrl}/${endpoint}`;
        }
        
        // Sistema de caché para GET requests
        const cacheKey = `${method}:${url}:${body ? JSON.stringify(body) : ''}`;
        if (method === 'GET' && useCache && this.state.apiCache[cacheKey]) {
            const cachedData = this.state.apiCache[cacheKey];
            if (Date.now() - cachedData.timestamp < this.state.cacheTimeout) {
                console.log(`💾 Usando datos en caché para ${url}`);
                return cachedData.data;
            } else {
                // Eliminar caché expirada
                delete this.state.apiCache[cacheKey];
            }
        }
        
        // Reducir la verbosidad del logging para mejorar rendimiento
        console.log(`🌐 API Call: ${method} ${url}`);
        
        const options = {
            method,
            headers: {
                'Content-Type': 'application/json',
                // Añadir un encabezado para evitar caché del navegador
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache'
            },
            // Añadir un timeout para evitar solicitudes colgadas
            signal: AbortSignal.timeout(10000) // 10 segundos de timeout
        };
        
        if (body) {
            options.body = JSON.stringify(body);
            // Reducir verbosidad del logging
            if (method === 'POST') {
                console.log('📤 Enviando datos...');
            }
        }

        try {
            const response = await fetch(url, options);
            console.log(`📡 Response: ${response.status}`);
            
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
            
            // Optimizar el manejo de la respuesta JSON
            try {
                const result = await response.json();
                // Reducir verbosidad del logging
                console.log('📥 Result recibido');
                
                // Guardar en caché si es una solicitud GET
                if (method === 'GET' && useCache) {
                    const cacheKey = `${method}:${url}:${body ? JSON.stringify(body) : ''}`;
                    this.state.apiCache[cacheKey] = {
                        data: result,
                        timestamp: Date.now()
                    };
                }
                
                return result;
            } catch (jsonError) {
                console.warn('Error al procesar JSON de respuesta:', jsonError);
                return { success: true, data: {} }; // Devolver un objeto por defecto para evitar errores
            }
            
        } catch (error) {
            console.error(`❌ API call failed: ${method} ${url}`, error);
            
            // Mostrar errores de forma más informativa
            if (error.message.includes('404')) {
                console.warn('⚠️ Endpoint no encontrado:', url);
                this.showToast(`Endpoint no encontrado: ${url}. Verifica que la API esté registrada correctamente.`, 'warning');
            } else if (error.message.includes('500')) {
                this.showToast(`Error interno del servidor en ${url}. Revisa los logs del backend.`, 'error');
            } else if (error.message.includes('NetworkError') || error.message.includes('Failed to fetch')) {
                this.showToast(`Error de conexión. Verifica que el servidor esté ejecutándose.`, 'error');
            } else {
                this.showToast(`Error en ${method} ${url}: ${error.message}`, 'error');
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
                this.state.leads = this.normalizeLeadsData(data.data || data);
                console.log('🔥 [DEBUG] Leads recibidos en handleWebSocketMessage:', data);
                console.log('🔥 [DEBUG] Leads normalizados:', this.state.leads.length);
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
        // Prevenir solicitudes duplicadas
        const requestKey = `${type}:${JSON.stringify(payload)}`;
        
        // Si ya hay una solicitud pendiente del mismo tipo, devolver esa promesa
        if (this.state.pendingRequests[requestKey]) {
            console.log(`⏳ Ignorando solicitud duplicada: ${type}`);
            return this.state.pendingRequests[requestKey];
        }
        
        // Si WebSocket está disponible, úsalo
        if (this.state.socket && this.state.socket.readyState === WebSocket.OPEN) {
            this.state.socket.send(JSON.stringify({ type, ...payload }));
            return Promise.resolve();
        }
        
        // Crear una promesa para esta solicitud
        const requestPromise = (async () => {
            try {
                // Fallback a peticiones HTTP para los mensajes básicos
                switch (type) {
                    case 'get_all_leads':
                        try {
                            console.log('🚀 Cargando leads desde API...');
                            
                            // Construir parámetros de query con filtros
                            const params = new URLSearchParams();
                            if (this.state.filters.estado1) params.append('estado1', this.state.filters.estado1);
                            if (this.state.filters.estado2) params.append('estado2', this.state.filters.estado2);
                            if (this.state.filters.status) params.append('status', this.state.filters.status);
                            if (this.state.filters.priority) params.append('priority', this.state.filters.priority);
                            if (this.state.filters.selected === 'true') params.append('selected_only', 'true');
                            
                            const queryString = params.toString();
                            const endpoint = queryString ? `/leads?${queryString}` : '/leads';
                            
                            // Usar caché para reducir solicitudes al servidor
                            const resp = await this.apiCall('GET', endpoint, null, true);
                            const leads = resp.leads || [];
                            console.log('📊 API devuelve', leads.length, 'leads con filtros:', this.state.filters);
                            this.handleWebSocketMessage({ type: 'all_leads', data: leads });
                        } catch (error) {
                            console.error('❌ Error cargando leads:', error);
                            this.showToast('Error cargando leads: ' + error.message, 'error');
                        }
                        break;
                        
                    case 'get_status':
                        try {
                            // Usar caché para reducir solicitudes al servidor
                            const data = await this.apiCall('GET', '/status', null, true);
                            this.handleWebSocketMessage({ type: 'initial_status', data });
                        } catch (_) {}
                        break;
                        
                    case 'mark_lead':
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
                        
                    case 'mark_leads':
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
                        
                    default:
                        console.warn(`Mensaje ${type} ignorado en modo fallback.`);
                }
            } finally {
                // Limpiar la solicitud pendiente cuando termine
                delete this.state.pendingRequests[requestKey];
            }
        })();
        
        // Registrar esta solicitud como pendiente
        this.state.pendingRequests[requestKey] = requestPromise;
        
        return requestPromise;
    }

    // Control de frecuencia de actualizaciones
    throttle(func, delay) {
        let lastCall = 0;
        return function(...args) {
            const now = Date.now();
            if (now - lastCall >= delay) {
                lastCall = now;
                return func.apply(this, args);
            }
            return Promise.resolve(); // Devolver promesa vacía si se ignora la llamada
        };
    }
    
    // Método para obtener el estado del sistema
    async getStatus() {
        return this.sendMessage('get_status');
    }
    
    async loadInitialData() {
        if (this.state.isLoading) {
            console.warn('⚠️ Ya se están cargando datos iniciales');
            return;
        }
        
        this.setLoading(true);
        
        try {
            // Cargar datos de forma optimizada para reducir consumo de recursos
            await this.getStatus();
            
            // Solo cargar leads si la página sigue activa
            if (document.visibilityState === 'visible') {
                await this.sendMessage('get_all_leads');
            }
        } catch (error) {
            console.error('Error al cargar datos iniciales:', error);
        } finally {
            this.setLoading(false);
        }
    }

    async getStatus() {
        await this.sendMessage('get_status');
    }
    
    /**
     * Actualiza el estado del sistema basado en los datos recibidos
     * @param {Object} data - Datos de estado del sistema
     */
    updateSystemStatus(data) {
        // Verificar que data es un objeto válido
        if (!data || typeof data !== 'object') {
            console.error('Error: datos de estado inválidos', data);
            return;
        }

        // Extraer el estado de ejecución del sistema desde cualquier estructura posible
        let isRunning = false;
        
        // Intentar diferentes estructuras de datos posibles
        if (data.system_status && data.system_status.call_manager && typeof data.system_status.call_manager.is_running === 'boolean') {
            // Estructura completa: data.system_status.call_manager.is_running
            isRunning = data.system_status.call_manager.is_running;
            console.log('✅ Estado del sistema obtenido de system_status.call_manager.is_running:', isRunning);
        } else if (data.call_manager && typeof data.call_manager.is_running === 'boolean') {
            // Estructura alternativa: data.call_manager.is_running
            isRunning = data.call_manager.is_running;
            console.log('✅ Estado del sistema obtenido de call_manager.is_running:', isRunning);
        } else if (typeof data.is_running === 'boolean') {
            // Estructura simple: data.is_running
            isRunning = data.is_running;
            console.log('✅ Estado del sistema obtenido de is_running:', isRunning);
        } else if (data.data && typeof data.data.is_running === 'boolean') {
            // Estructura con wrapper: data.data.is_running
            isRunning = data.data.is_running;
            console.log('✅ Estado del sistema obtenido de data.is_running:', isRunning);
        } else {
            console.warn('⚠️ No se pudo determinar el estado del sistema, asumiendo detenido');
        }
        
        // Guardar el estado anterior para comparaciones
        const wasRunning = this.state.isSystemRunning;
        this.state.isSystemRunning = isRunning;
        
        // Actualizar UI según el estado
        if (this.elements.systemStatus) {
            this.elements.systemStatus.innerHTML = isRunning ? 
                '<span class="badge bg-success"><i class="bi bi-play-circle"></i> En ejecución</span>' : 
                '<span class="badge bg-secondary"><i class="bi bi-stop-circle"></i> Detenido</span>';
        }
        
        // Actualizar botones según el estado
        if (this.elements.startCallsBtn) this.elements.startCallsBtn.disabled = isRunning;
        if (this.elements.stopCallsBtn) this.elements.stopCallsBtn.disabled = !isRunning;
        
        // Clear loading state when system stops
        if (wasRunning && !isRunning) {
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
        console.log('🔥 [DEBUG] 🎨 Renderizando tabla...');
        console.log('🔥 [DEBUG] Total leads en state:', this.state.leads.length);
        console.log('🔥 [DEBUG] Filtros actuales:', this.state.filters);
        
        this.elements.leadsTableBody.innerHTML = '';
        const filteredLeads = this.getFilteredLeads();
        console.log('🔥 [DEBUG] Leads después de filtros:', filteredLeads.length);
        
        if (filteredLeads.length === 0) {
            console.log('🔥 [DEBUG] ❌ NO HAY LEADS FILTRADOS - esto puede ser el problema!');
            console.log('🔥 [DEBUG] Leads originales:', this.state.leads.slice(0, 3));
        }
        
        const paginatedLeads = this.paginate(filteredLeads, this.state.currentPage, this.state.itemsPerPage);
        console.log('Leads paginados:', paginatedLeads.length);

        if (paginatedLeads.length === 0) {
            this.elements.leadsTableBody.innerHTML = `
                <tr>
                    <td colspan="11" class="text-center py-4">
                        <i class="bi bi-info-circle-fill fs-3 text-muted"></i>
                        <p class="mt-2 mb-0">No hay leads que coincidan con los filtros.</p>
                        <small class="text-muted">Ajusta los filtros para ver más leads</small>
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
        
        // Forzar actualización de contadores después de renderizar
        const selectedCount = this.getSelectedCount();
        this.updateLeadsCounters(filteredLeads.length, selectedCount);
        
        console.log('✅ Tabla renderizada correctamente');
    }

    createLeadRow(lead) {
        console.log('🧑 Creando fila para lead:', lead.id, lead.nombre_lead);
        
        const row = document.createElement('tr');
        row.dataset.leadId = lead.id;
        
        // Hacer más visible la selección con estilos más marcados
        if (lead.selected_for_calling) {
            row.className = 'table-primary';
            row.style.backgroundColor = '#B5E0F4'; // Azul corporativo suave
            row.style.borderLeft = '4px solid #35C0F1'; // Borde azul corporativo
        } else {
            row.className = '';
            row.style.backgroundColor = '';
            row.style.borderLeft = '';
        }

        let statusClass = 'bg-secondary';
        if (lead.call_status === 'completed') statusClass = 'bg-success';
        else if (['in_progress', 'calling', 'selected'].includes(lead.call_status)) statusClass = 'bg-warning text-dark';
        else if (['error', 'failed', 'busy', 'no_answer'].includes(lead.call_status)) statusClass = 'bg-danger';

        const lastCallTime = lead.last_call_time ? new Date(lead.last_call_time).toLocaleString('es-ES') : 'Nunca';
        const callStatus = (lead.call_status || 'pendiente').replace('_', ' ');

        // Crear el nombre completo
        const nombreCompleto = `${lead.nombre || ''} ${lead.apellidos || ''}`.trim() || 'N/A';
        
        // Determinar colores para badges usando colores corporativos
        let statusBadgeStyle = 'background-color: #646762; color: white;'; // Gris corporativo por defecto
        if (lead.call_status === 'completed') statusBadgeStyle = 'background-color: #92D050; color: white;'; // Verde corporativo
        else if (['in_progress', 'calling', 'selected'].includes(lead.call_status)) statusBadgeStyle = 'background-color: #ffc107; color: #333;'; // Warning
        else if (['error', 'failed', 'busy', 'no_answer'].includes(lead.call_status)) statusBadgeStyle = 'background-color: #dc3545; color: white;'; // Danger
        
        // Badge para gestión manual
        const isManual = lead.manual_management;
        const manualBadgeStyle = isManual ? 'background-color: #ffc107; color: #333;' : 'background-color: #646762; color: white;';
        const manualBadgeText = isManual ? 'Manual' : 'Automático';
        
        row.innerHTML = `
            <td>
                <div class="form-check">
                    <input type="checkbox" class="form-check-input lead-checkbox" data-lead-id="${lead.id}" ${lead.selected_for_calling ? 'checked' : ''} style="${lead.selected_for_calling ? 'border-color: #35C0F1; background-color: #35C0F1; box-shadow: 0 0 0 0.25rem rgba(53, 192, 241, 0.25);' : ''}">
                    ${lead.selected_for_calling ? '<i class="bi bi-check-circle-fill text-primary" style="position: absolute; margin-left: 1.5rem; margin-top: -1.2rem; font-size: 0.8rem;"></i>' : ''}
                </div>
            </td>
            <td style="color: #333; font-weight: ${lead.selected_for_calling ? '600' : '500'};">${nombreCompleto}</td>
            <td style="color: #35C0F1; font-weight: 500;">${lead.telefono || lead.telefono2 || 'N/A'}</td>
            <td><span class="badge" style="background-color: #35C0F1; color: white;">${lead.status_level_1 || 'N/A'}</span></td>
            <td><span class="badge" style="background-color: #646762; color: white;">${lead.status_level_2 || 'N/A'}</span></td>
            <td><span class="badge" style="${statusBadgeStyle}">${callStatus}</span></td>
            <td><span class="badge" style="${manualBadgeStyle}">${manualBadgeText}</span></td>
            <td style="color: #333;">${lead.call_priority || 3}</td>
            <td style="color: #333;">${lead.call_attempts_count || 0}</td>
            <td style="color: #333;">${lastCallTime}</td>
            <td>
                <button class="btn btn-sm" style="border: 1px solid #35C0F1; color: #35C0F1;" title="Ver Detalles" onclick="window.callsManager.showLeadDetails('${lead.id}')">
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

    getSelectedCount() {
        return this.state.leads.filter(lead => lead.selected_for_calling).length;
    }

    updateSelectedCount() {
        // Actualizar el contador de leads seleccionados en la interfaz
        const selectedCount = this.getSelectedCount();
        const selectedCountElement = document.getElementById('selectedLeadsCount');
        if (selectedCountElement) {
            selectedCountElement.textContent = selectedCount;
            
            // Actualizar también la clase del badge para destacar visualmente
            const badge = document.getElementById('selectedLeadsCountBadge');
            if (badge) {
                if (selectedCount > 0) {
                    badge.classList.remove('bg-secondary');
                    badge.classList.add('bg-success');
                } else {
                    badge.classList.remove('bg-success');
                    badge.classList.add('bg-secondary');
                }
            }
        }
        
        // Actualizar también el contador total de leads
        const totalLeadsElement = document.getElementById('totalLeadsCount');
        if (totalLeadsElement) {
            totalLeadsElement.textContent = this.state.leads.length;
        }
    }
    
    updateLeadsCounters(totalCount, selectedCount) {
        // Actualizar contador total de leads
        const totalLeadsElement = document.getElementById('totalLeadsCount');
        if (totalLeadsElement) {
            totalLeadsElement.textContent = totalCount;
        }
        
        // Actualizar contador de leads seleccionados
        const selectedCountElement = document.getElementById('selectedLeadsCount');
        if (selectedCountElement) {
            selectedCountElement.textContent = selectedCount;
            
            // Actualizar también la clase del badge para destacar visualmente
            const badge = document.getElementById('selectedLeadsCountBadge');
            if (badge) {
                if (selectedCount > 0) {
                    badge.classList.remove('bg-secondary');
                    badge.classList.add('bg-success');
                } else {
                    badge.classList.remove('bg-success');
                    badge.classList.add('bg-secondary');
                }
            }
        }
        
        // Actualizar el texto del botón de selección por estado si existe
        const selectByStatusBtn = document.getElementById('selectByStatusDropdown');
        if (selectByStatusBtn) {
            if (selectedCount > 0) {
                selectByStatusBtn.innerHTML = `<i class="bi bi-funnel"></i> Seleccionados: ${selectedCount}`;
            } else {
                selectByStatusBtn.innerHTML = `<i class="bi bi-funnel"></i> Seleccionar por Estado`;
            }
        }
    }
    
    getFilteredLeads() {
        // Filtrar leads según los filtros actuales
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
    }

    async selectAllLeads(selected) {
        console.log(`🔥 [DEBUG] selectAllLeads iniciado - selected=${selected}`);
        console.log(`🔥 [DEBUG] Total leads en estado:`, this.state.leads.length);
        
        // CAMBIO: Usar TODOS los leads filtrados, no solo los paginados
        const filteredLeads = this.getFilteredLeads();
        console.log(`🔥 [DEBUG] Leads filtrados:`, filteredLeads.length);
        console.log(`🔥 [DEBUG] Seleccionando TODOS los leads filtrados (no solo página actual)`);
        
        const leadIds = [];
        
        // Actualizar estado local ANTES de enviar al servidor
        console.log(`🔥 [DEBUG] Actualizando estado local para ${filteredLeads.length} leads...`);
        filteredLeads.forEach((lead, index) => {
            const leadInState = this.state.leads.find(l => l.id === lead.id);
            if (leadInState) {
                leadInState.selected_for_calling = selected;
                leadInState.selected = selected; // Para compatibilidad
                leadIds.push(lead.id);
            }
        });
        
        console.log(`🔥 [DEBUG] Lead IDs para actualizar:`, leadIds);
        
        // Mostrar confirmación si son muchos leads
        if (leadIds.length > 50 && selected) {
            const confirmar = confirm(`¿Estás seguro de que quieres seleccionar ${leadIds.length} leads filtrados?\n\nEsto puede tomar unos segundos.`);
            if (!confirmar) {
                console.log('🔥 [DEBUG] Usuario canceló la selección masiva');
                return;
            }
        }
        
        // TEMPORAL: Limpiar filtro de selección para evitar que los leads desaparezcan
        const originalSelectedFilter = this.state.filters.selected;
        if (this.state.filters.selected !== '') {
            console.log(`🔥 [DEBUG] Limpiando filtro de selección temporalmente: ${this.state.filters.selected} -> ''`);
            this.state.filters.selected = '';
            if (this.elements.selectedFilter) {
                this.elements.selectedFilter.value = '';
            }
        }
        
        // Deshabilitar botón durante el procesamiento
        const selectAllBtn = document.getElementById('selectAllBtn');
        const deselectAllBtn = document.getElementById('deselectAllBtn');
        if (selectAllBtn) {
            selectAllBtn.disabled = true;
            selectAllBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> Procesando...';
        }
        if (deselectAllBtn) {
            deselectAllBtn.disabled = true;
        }
        
        // Re-renderizar tabla inmediatamente para mostrar cambios
        console.log(`🔥 [DEBUG] Renderizando tabla...`);
        this.renderTable();
        console.log(`🔥 [DEBUG] Tabla renderizada`);
        
        // Enviar al servidor con procesamiento por lotes si hay muchos leads
        if (leadIds.length > 0) {
            try {
                console.log(`🔥 [DEBUG] Enviando ${leadIds.length} leads al servidor...`);
                
                // Si hay más de 100 leads, procesar en lotes para evitar timeouts
                if (leadIds.length > 100) {
                    const batchSize = 100;
                    let totalUpdated = 0;
                    
                    for (let i = 0; i < leadIds.length; i += batchSize) {
                        const batch = leadIds.slice(i, i + batchSize);
                        console.log(`🔥 [DEBUG] Procesando lote ${Math.floor(i/batchSize) + 1} (${batch.length} leads)...`);
                        
                        const response = await this.apiCall('POST', '/leads/select', {
                            lead_ids: batch,
                            selected: selected
                        });
                        
                        totalUpdated += response.updated_count || batch.length;
                        
                        // Pequeña pausa entre lotes para no sobrecargar el servidor
                        if (i + batchSize < leadIds.length) {
                            await new Promise(resolve => setTimeout(resolve, 100));
                        }
                    }
                    
                    console.log(`✅ Servidor actualizado en lotes: ${totalUpdated} leads`);
                    this.showToast(`${selected ? 'Seleccionados' : 'Deseleccionados'} ${totalUpdated} leads filtrados`, 'success');
                } else {
                    // Para cantidades menores, enviar todo junto
                    const response = await this.apiCall('POST', '/leads/select', {
                        lead_ids: leadIds,
                        selected: selected
                    });
                    
                    const updated = response.updated_count || leadIds.length;
                    console.log(`✅ Servidor actualizado: ${updated} leads`);
                    this.showToast(`${selected ? 'Seleccionados' : 'Deseleccionados'} ${updated} leads filtrados`, 'success');
                }
                
            } catch (error) {
                console.error('🔥 [DEBUG] Error actualizando servidor:', error);
                this.showToast(`Error actualizando selección: ${error.message}`, 'error');
                // No revertir cambios locales - mantener la UI como está
            }
        } else {
            console.log(`🔥 [DEBUG] No hay leads para actualizar en servidor`);
            this.showToast('No hay leads que cumplan los filtros para seleccionar', 'info');
        }
        
        console.log(`✅ UI actualizada: ${selected ? 'Seleccionados' : 'Deseleccionados'} ${leadIds.length} leads`);
        
        // Restaurar botones
        if (selectAllBtn) {
            selectAllBtn.disabled = false;
            selectAllBtn.innerHTML = '<i class="bi bi-check-all"></i> Seleccionar Todo';
        }
        if (deselectAllBtn) {
            deselectAllBtn.disabled = false;
        }
        
        // Verificar estado después de renderizar
        const selectedCount = this.state.leads.filter(l => l.selected_for_calling).length;
        console.log(`🔥 [DEBUG] Estado final - Total seleccionados: ${selectedCount}`);
    }

    selectByStatus(statusField, statusValue) {
        console.log(`🎯 Seleccionando leads por ${statusField} = "${statusValue}"`);
        
        // Filtrar leads que coincidan con el estado especificado
        const matchingLeads = this.state.leads.filter(lead => {
            return lead[statusField] === statusValue;
        });
        
        if (matchingLeads.length === 0) {
            this.showToast(`No se encontraron leads con ${statusField} = "${statusValue}"`, 'warning');
            return;
        }
        
        // Contar cuántos ya están seleccionados
        const alreadySelected = matchingLeads.filter(lead => lead.selected_for_calling).length;
        const notSelected = matchingLeads.length - alreadySelected;
        
        // Caso especial para "Volver a llamar" - seleccionar automáticamente sin confirmación
        const autoSelect = (statusField === 'status_level_1' && statusValue === 'Volver a llamar');
        
        // Para otros estados, mostrar mensaje de confirmación
        let confirmed = autoSelect;
        
        if (!autoSelect) {
            // Mensaje más informativo
            let message = `Encontrados ${matchingLeads.length} leads con ${statusField} = "${statusValue}":\n\n`;
            message += `• ${alreadySelected} ya seleccionados\n`;
            message += `• ${notSelected} sin seleccionar\n\n`;
            message += `¿Seleccionar TODOS los ${matchingLeads.length} leads?`;
            
            confirmed = confirm(message);
        }
        
        if (confirmed) {
            const leadIds = [];
            
            // Actualizar estado local - seleccionar todos independientemente de su estado previo
            matchingLeads.forEach(lead => {
                lead.selected_for_calling = true;
                lead.selected = true;
                leadIds.push(lead.id);
            });
            
            // Enviar al servidor sin recargar datos
            if (leadIds.length > 0) {
                this.apiCall('POST', '/leads/select', {
                    lead_ids: leadIds,
                    selected: true
                }).catch(error => {
                    console.error('Error actualizando servidor:', error);
                    this.showToast('Error actualizando selección en el servidor', 'warning');
                });
            }
            
            // Re-renderizar tabla
            this.renderTable();
            
            // Actualizar el contador de leads seleccionados
            this.updateSelectedCount();
            
            // Actualizar filtros si es "Volver a llamar" para mostrar solo esos leads
            if (autoSelect) {
                // Establecer filtro para mostrar solo leads con estado "Volver a llamar"
                this.state.filters.estado1 = 'Volver a llamar';
                
                // Actualizar la interfaz de filtros si existe
                const filterEstado1 = document.getElementById('filterEstado1');
                if (filterEstado1) {
                    filterEstado1.value = 'Volver a llamar';
                }
                
                // Re-renderizar tabla con el nuevo filtro aplicado
                this.renderTable();
            }
            
            this.showToast(`✅ Seleccionados ${leadIds.length} leads con ${statusField} = "${statusValue}" (${notSelected} nuevos)`, 'success');
            console.log(`✅ Seleccionados ${leadIds.length} leads por estado:`, leadIds);
        }
    }

    showStatusSelectionModal() {
        // Obtener estados únicos
        const estados1 = [...new Set(this.state.leads.map(l => l.status_level_1).filter(Boolean))].sort();
        const callStatuses = [...new Set(this.state.leads.map(l => l.call_status).filter(Boolean))].sort();
        
        // Crear conteo por estado
        const status1Counts = {};
        const callStatusCounts = {};
        
        this.state.leads.forEach(lead => {
            if (lead.status_level_1) {
                status1Counts[lead.status_level_1] = (status1Counts[lead.status_level_1] || 0) + 1;
            }
            if (lead.call_status) {
                callStatusCounts[lead.call_status] = (callStatusCounts[lead.call_status] || 0) + 1;
            }
        });
        
        let modalContent = '<div class="row"><div class="col-12">';
        modalContent += '<h6>Seleccionar/Deseleccionar por Estado:</h6>';
        modalContent += '<div class="list-group mb-3">';
        
        // Estados 1
        estados1.forEach(estado => {
            const count = status1Counts[estado] || 0;
            modalContent += `
                <div class="list-group-item d-flex justify-content-between align-items-center">
                    <span><strong>${estado}</strong> (${count} leads)</span>
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-outline-success" onclick="callsManager.selectByStatus('status_level_1', '${estado}')">Seleccionar</button>
                        <button class="btn btn-outline-warning" onclick="callsManager.deselectByStatus('status_level_1', '${estado}')">Deseleccionar</button>
                    </div>
                </div>
            `;
        });
        
        modalContent += '</div></div></div>';
        
        // Mostrar modal simple con prompt
        const result = confirm(`Estados disponibles:\n\n${estados1.map(e => `• ${e}: ${status1Counts[e] || 0} leads`).join('\n')}\n\n¿Continuar con selección avanzada?`);
        if (result) {
            this.showToast('Usa el menú "Seleccionar por Estado" para elegir estados específicos', 'info');
        }
    }

    deselectByStatus(statusField, statusValue) {
        console.log(`🎯 Deseleccionando leads por ${statusField} = "${statusValue}"`);
        
        // Filtrar leads que coincidan con el estado especificado y estén seleccionados
        const matchingLeads = this.state.leads.filter(lead => {
            return lead[statusField] === statusValue && lead.selected_for_calling;
        });
        
        if (matchingLeads.length === 0) {
            this.showToast(`No se encontraron leads seleccionados con ${statusField} = "${statusValue}"`, 'warning');
            return;
        }
        
        // Confirmar la acción directamente
        const confirmed = confirm(`¿Deseleccionar todos los ${matchingLeads.length} leads seleccionados que tienen ${statusField} = "${statusValue}"?`);
        
        if (confirmed) {
            const leadIds = [];
            
            // Actualizar estado local
            matchingLeads.forEach(lead => {
                lead.selected_for_calling = false;
                lead.selected = false;
                leadIds.push(lead.id);
            });
            
            // Enviar al servidor sin recargar datos
            if (leadIds.length > 0) {
                this.apiCall('POST', '/leads/select', {
                    lead_ids: leadIds,
                    selected: false
                }).catch(error => {
                    console.error('Error actualizando servidor:', error);
                    this.showToast('Error actualizando selección en el servidor', 'warning');
                });
            }
            
            // Re-renderizar tabla
            this.renderTable();
            
            this.showToast(`✅ Deseleccionados ${leadIds.length} leads con ${statusField} = "${statusValue}"`, 'success');
            console.log(`✅ Deseleccionados ${leadIds.length} leads por estado:`, leadIds);
        }
    }

    setManualManagement(isManual) {
        console.log(`🔧 Configurando gestión manual = ${isManual}`);
        
        // Obtener leads seleccionados en la tabla actual
        const selectedCheckboxes = document.querySelectorAll('.lead-checkbox:checked');
        const selectedLeadIds = Array.from(selectedCheckboxes).map(cb => parseInt(cb.dataset.leadId));
        
        if (selectedLeadIds.length === 0) {
            this.showToast('Selecciona al menos un lead para cambiar su gestión', 'warning');
            return;
        }
        
        // Confirmar la acción
        const actionText = isManual ? 'gestión manual' : 'gestión automática';
        const confirmed = confirm(`¿Cambiar ${selectedLeadIds.length} leads a ${actionText}?`);
        
        if (confirmed) {
            // Actualizar estado local
            selectedLeadIds.forEach(leadId => {
                const lead = this.state.leads.find(l => l.id === leadId);
                if (lead) {
                    lead.manual_management = isManual;
                }
            });
            
            // Enviar al servidor
            this.apiCall('POST', '/api/calls/leads/manual-management', {
                lead_ids: selectedLeadIds,
                manual_management: isManual
            }).then(() => {
                this.showToast(`✅ Actualizados ${selectedLeadIds.length} leads a ${actionText}`, 'success');
                this.renderTable();
            }).catch(error => {
                this.showToast(`Error actualizando gestión: ${error.message}`, 'error');
            });
        }
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
        
        // Leer valores de los filtros incluyendo estado1 y estado2
        this.state.filters.estado1 = this.elements.estado1Filter?.value || '';
        this.state.filters.estado2 = this.elements.estado2Filter?.value || '';
        this.state.filters.status = this.elements.statusFilter?.value || '';
        this.state.filters.priority = this.elements.priorityFilter?.value || '';
        this.state.filters.selected = this.elements.selectedFilter?.value || '';
        
        console.log('Filtros aplicados:', this.state.filters);
        
        // Resetear a la primera página
        this.state.currentPage = 1;
        
        // Recargar datos con filtros desde el servidor
        this.sendMessage('get_all_leads');
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

        this.apiCall('POST', '/leads/select', {
            lead_ids: visibleLeadIds,
            selected: isChecked
        }).catch(error => {
            console.error('Error actualizando servidor:', error);
            this.showToast('Error actualizando selección en el servidor', 'warning');
        });
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
        
        // Evitar múltiples llamadas simultáneas del mismo tipo
        if (this.state.pendingRequests && this.state.pendingRequests[type]) {
            console.warn(`⚠️ Ya hay una solicitud pendiente de tipo ${type}, ignorando...`);
            return;
        }
        
        // Inicializar el registro de solicitudes pendientes si no existe
        if (!this.state.pendingRequests) {
            this.state.pendingRequests = {};
        }
        
        // Marcar esta solicitud como pendiente
        this.state.pendingRequests[type] = true;
        
        try {
            switch (type) {
                case 'get_all_leads':
                    const response = await this.apiCall('GET', '/leads');
                    if (response && response.success && response.data) {
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
                    if (statusResponse && statusResponse.success) {
                        this.updateSystemStatus(statusResponse.data || {});
                    } else {
                        // Si la respuesta no es exitosa, usar un objeto vacío para evitar errores
                        this.updateSystemStatus({});
                    }
                    break;
                case 'mark_lead':
                    await this.apiCall('POST', '/api/leads/select', {
                        lead_ids: [data.lead_id],
                        selected: data.selected
                    });
                    break;
                case 'mark_leads':
                    await this.apiCall('POST', '/api/leads/select', {
                        lead_ids: data.lead_ids,
                        selected: data.selected
                    });
                    break;
                default:
                    console.warn('Tipo de mensaje no reconocido:', type);
            }
        } catch (error) {
            console.error('Error en sendMessage:', error);
        } finally {
            // Limpiar el registro de solicitud pendiente
            if (this.state.pendingRequests) {
                this.state.pendingRequests[type] = false;
            }
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
        const start = totalFiltered > 0 ? (this.state.currentPage - 1) * this.state.itemsPerPage + 1 : 0;
        const end = Math.min(start + this.state.itemsPerPage - 1, totalFiltered);
        const selectedCount = this.getSelectedCount();
        const filteredSelectedCount = this.getFilteredLeads().filter(lead => lead.selected_for_calling).length;
        
        // Información más detallada y visible
        const info = totalFiltered > 0 
            ? `Mostrando ${start}-${end} de ${totalFiltered} leads | ${filteredSelectedCount} seleccionados de los filtrados | ${selectedCount} total seleccionados`
            : `Sin leads que mostrar | ${selectedCount} total seleccionados`;
            
        this.elements.leadsInfo.textContent = info;
        
        // Actualizar los contadores de leads en los badges del header
        this.updateLeadsCounters(totalFiltered, selectedCount);
        
        console.log(`📊 Info actualizada: ${info}`);
    }

    updateLeadsCounters(totalFiltered, selectedCount) {
        // Actualizar contador de total de leads mostrados
        if (this.elements.totalLeadsCount) {
            this.elements.totalLeadsCount.textContent = totalFiltered || 0;
        }
        
        // Actualizar contador de leads seleccionados
        if (this.elements.selectedLeadsCount) {
            this.elements.selectedLeadsCount.textContent = selectedCount || 0;
            
            // Cambiar color del badge según si hay leads seleccionados
            const selectedBadge = this.elements.selectedLeadsCount.parentElement;
            if (selectedBadge) {
                if (selectedCount > 0) {
                    selectedBadge.className = 'badge bg-success fs-6';
                    selectedBadge.style.animation = 'pulse 2s infinite';
                } else {
                    selectedBadge.className = 'badge bg-secondary fs-6';
                    selectedBadge.style.animation = '';
                }
            }
        }
        
        console.log(`🔢 Contadores actualizados: Total=${totalFiltered}, Seleccionados=${selectedCount}`);
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
        
        // Recargar datos desde el servidor sin filtros
        this.sendMessage('get_all_leads');
        
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

// Inicialización cuando el DOM esté listo
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

// Limpiar recursos al cerrar la página
window.addEventListener('beforeunload', () => {
    if (window.CallsManager && typeof window.CallsManager.destroy === 'function') {
        window.CallsManager.destroy();
    }
});
