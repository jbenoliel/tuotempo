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
            filters: {
                city: '',
                status: '',
                priority: '',
                selected: false
            }
        };
        this.config = {
            maxConcurrentCalls: 3
        };
    }

    init() {
        this.cacheElements();
        this.bindEvents();
        this.connectWebSocket();
        this.loadInitialData();
        this.loadFilters();
        this.loadConfiguration();
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
            cityFilter: document.getElementById('cityFilter'),
            statusFilter: document.getElementById('statusFilter'),
            priorityFilter: document.getElementById('priorityFilter'),
            selectedFilter: document.getElementById('selectedFilter'),
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
        this.elements.cityFilter?.addEventListener('change', () => this.applyFilters());
        this.elements.statusFilter?.addEventListener('change', () => this.applyFilters());
        this.elements.priorityFilter?.addEventListener('change', () => this.applyFilters());
        this.elements.selectedFilter?.addEventListener('change', () => this.applyFilters());
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
        const url = `/api/calls${endpoint}`;
        const options = {
            method,
            headers: {
                'Content-Type': 'application/json'
            }
        };
        if (body) {
            options.body = JSON.stringify(body);
        }

        try {
            const response = await fetch(url, options);
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ error: 'Error desconocido en la API' }));
                throw new Error(errorData.error || `Error ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            this.showToast(`Error en la API: ${error.message}`, 'error');
            console.error(`API call failed: ${method} ${endpoint}`, error);
            throw error;
        }
    }

    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/calls`;
        this.state.socket = new WebSocket(wsUrl);

        this.state.socket.onopen = () => {
            console.log('WebSocket conectado.');
            this.state.retryCount = 0;
            this.updateConnectionStatus(true);
            this.getStatus(); // Solicitar estado al conectar
        };

        this.state.socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleWebSocketMessage(data);
        };

        this.state.socket.onclose = () => {
            console.log('WebSocket desconectado. Intentando reconectar...');
            this.updateConnectionStatus(false);
            if (this.state.retryCount < this.state.maxRetries) {
                setTimeout(() => {
                    this.state.retryCount++;
                    this.connectWebSocket();
                }, this.state.retryDelay);
            }
        };

        this.state.socket.onerror = (error) => {
            console.error('Error de WebSocket:', error);
            this.updateConnectionStatus(false);
            this.state.socket.close();
        };
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
                this.state.leads = data.data;
                this.updateFilters();
                this.renderTable();
                break;
            case 'toast':
                this.showToast(data.message, data.category || 'info');
                break;
        }
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

    sendMessage(type, payload = {}) {
        if (this.state.socket && this.state.socket.readyState === WebSocket.OPEN) {
            this.state.socket.send(JSON.stringify({ type, ...payload }));
        } else {
            console.error('WebSocket no está conectado.');
        }
    }

    async loadInitialData() {
        this.setLoading(true);
        try {
            this.sendMessage('get_all_leads');
            this.getStatus();
        } catch (error) {
            this.showToast('Error al cargar datos iniciales.', 'error');
        } finally {
            this.setLoading(false);
        }
    }

    async getStatus() {
        this.sendMessage('get_status');
    }

    updateSystemStatus(data) {
        this.state.isSystemRunning = data.is_running;
        this.elements.systemStatus.textContent = data.is_running ? 'Activo' : 'Detenido';
        this.elements.systemStatus.className = `badge fs-6 ${data.is_running ? 'bg-success' : 'bg-danger'}`;
        this.elements.startCallsBtn.disabled = data.is_running;
        this.elements.stopCallsBtn.disabled = !data.is_running;

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
        const selectedIds = this.getSelectedLeadIds();
        if (selectedIds.length === 0) {
            this.showToast('Debe seleccionar al menos un lead para iniciar las llamadas.', 'warning');
            return;
        }

        this.showLoader(this.elements.startCallsBtn, true);
        try {
            const testModeEnabled = this.elements.testModeSwitch?.checked;
            const overridePhone = this.elements.overridePhoneInput?.value;

            const config = {
                max_concurrent: this.config.maxConcurrentCalls,
                selected_leads: selectedIds,
                override_phone: testModeEnabled ? overridePhone : null
            };

            if (testModeEnabled && !overridePhone) {
                this.showToast('Por favor, introduce un número de teléfono para el modo de prueba.', 'warning');
                this.showLoader(this.elements.startCallsBtn, false);
                return;
            }

            const response = await this.apiCall('POST', '/start', config);
            if (response.success) {
                this.showToast('Sistema de llamadas iniciado.', 'success');
            } else {
                this.showToast(response.error || 'No se pudo iniciar el sistema.', 'error');
            }
        } catch (error) {
            // apiCall ya muestra el toast
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
        this.elements.leadsTableBody.innerHTML = '';
        const filteredLeads = this.getFilteredLeads();
        const paginatedLeads = this.paginate(filteredLeads, this.state.currentPage, this.state.itemsPerPage);

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
    }

    createLeadRow(lead) {
        const row = document.createElement('tr');
        row.dataset.leadId = lead.id;
        row.className = lead.selected ? 'table-primary' : '';

        let statusClass = 'bg-secondary';
        if (lead.call_status === 'completed') statusClass = 'bg-success';
        else if (['in_progress', 'calling'].includes(lead.call_status)) statusClass = 'bg-warning text-dark';
        else if (['error', 'failed', 'busy', 'no_answer'].includes(lead.call_status)) statusClass = 'bg-danger';

        const lastCallTime = lead.last_call_time ? new Date(lead.last_call_time).toLocaleString('es-ES') : 'Nunca';
        const callStatus = (lead.call_status || 'pendiente').replace('_', ' ');

        row.innerHTML = `
            <td><input type="checkbox" class="form-check-input lead-checkbox" data-lead-id="${lead.id}" ${lead.selected ? 'checked' : ''}></td>
            <td>${lead.nombre_lead || 'N/A'}</td>
            <td>${lead.telefono || 'N/A'}</td>
            <td>${lead.ciudad || 'N/A'}</td>
            <td>${lead.nombre_clinica || 'N/A'}</td>
            <td><span class="badge ${statusClass}">${callStatus}</span></td>
            <td>${lead.prioridad || 'N/A'}</td>
            <td>${lead.call_attempts || 0}</td>
            <td>${lastCallTime}</td>
            <td>
                <button class="btn btn-sm btn-outline-info" title="Ver Detalles" onclick="window.CallsManager.showLeadDetails('${lead.id}')">
                    <i class="bi bi-eye"></i>
                </button>
            </td>
        `;
        row.querySelector('.lead-checkbox').addEventListener('change', (e) => {
            this.toggleLeadSelection(lead.id, e.target.checked);
        });
        return row;
    }

    updateLeadInTable(lead) {
        const index = this.state.leads.findIndex(l => l.id === lead.id);
        if (index !== -1) {
            this.state.leads[index] = { ...this.state.leads[index], ...lead };
        }
        this.renderTable();
    }

    toggleLeadSelection(leadId, isSelected) {
        const lead = this.state.leads.find(l => l.id === leadId);
        if (lead) {
            lead.selected = isSelected;
            this.sendMessage('mark_lead', { lead_id: leadId, selected: isSelected });
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
                // Usamos los leads de la respuesta directamente, sin tocar this.state.currentLeads
                const cities = [...new Set(response.leads.map(lead => lead.ciudad).filter(city => city))].sort();
                if (this.elements.cityFilter) {
                    this.elements.cityFilter.innerHTML = '<option value="">Todas las ciudades</option>' +
                        cities.map(city => `<option value="${city}">${city}</option>`).join('');
                }
            }
        } catch (error) { console.error('Error cargando ciudades:', error); }
    }

    updateLeadsInfo() {
        if (!this.elements.leadsInfo) return;
        const { offset, limit, total } = this.state.pagination;
        const start = offset + 1;
        const end = Math.min(offset + limit, total);
        this.elements.leadsInfo.textContent = `Mostrando ${start}-${end} de ${total} leads`;
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

    saveConfiguration() {
        if (this.elements.maxConcurrentCalls) {
            this.config.maxConcurrentCalls = parseInt(this.elements.maxConcurrentCalls.value);
            this.showNotification('Configuración guardada', 'success');
            const modal = bootstrap.Modal.getInstance(document.getElementById('configModal'));
            if (modal) modal.hide();
        }
    }

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

    async apiCall(method, endpoint, data = null) {
        const url = `${this.apiBaseUrl}${endpoint}`;
        const config = { method, headers: { 'Content-Type': 'application/json' } };
        if (data && (method === 'POST' || method === 'PUT')) config.body = JSON.stringify(data);
        const response = await fetch(url, config);
        if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        return await response.json();
    }

    showNotification(message, type = 'info') {
        const toastContainer = document.getElementById('toastContainer');
        if (!toastContainer) return;
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
        const toast = new bootstrap.Toast(toastElement.firstElementChild, { delay: 5000 });
        toast.show();
        toastElement.firstElementChild.addEventListener('hidden.bs.toast', () => toastElement.remove());
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

    destroy() {
        this.stopAutoRefresh();
        console.log('📴 CallsManager destruido');
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
