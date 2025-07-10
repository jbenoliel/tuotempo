/**
 * Gestor de Llamadas Automáticas - Cliente JavaScript
 * TuoTempo - Sistema de llamadas con Pearl AI
 */

class CallsManager {
    constructor() {
        this.apiBaseUrl = '/api/calls';
        this.state = {
            isRunning: false,
            currentLeads: [],
            selectedLeads: new Set(),
            filters: { city: '', status: '', priority: '', selectedOnly: false },
            pagination: { limit: 50, offset: 0, total: 0 },
            stats: { total_calls: 0, successful_calls: 0, failed_calls: 0, active_calls: 0 }
        };
        this.elements = {};
        this.intervals = { status: null, leads: null };
        this.config = { refreshInterval: 10000, maxConcurrentCalls: 3, autoRefresh: true };
    }

    async init() {
        console.log('🚀 Iniciando CallsManager...');
        try {
            this.cacheElements();
            this.attachEventListeners();
            await this.loadInitialData();
            this.startAutoRefresh();
            console.log('✅ CallsManager inicializado correctamente');
            this.showNotification('Sistema iniciado correctamente', 'success');
        } catch (error) {
            console.error('❌ Error inicializando CallsManager:', error);
            this.showNotification('Error al inicializar el sistema', 'error');
        }
    }

    cacheElements() {
        const elementIds = [
            'startCallsBtn', 'stopCallsBtn', 'refreshBtn', 'systemStatus', 'connectionStatus',
            'totalCallsCount', 'successCallsCount', 'activeCallsCount', 'failedCallsCount',
            'progressSection', 'progressBar', 'progressText', 'cityFilter', 'statusFilter', 
            'priorityFilter', 'selectedFilter', 'selectAllBtn', 'deselectAllBtn', 'resetLeadsBtn',
            'leadsTableBody', 'leadsInfo', 'pagination', 'masterCheckbox', 'maxConcurrentCalls', 
            'pearlConnectionStatus', 'testConnectionBtn', 'saveConfigBtn'
        ];
        elementIds.forEach(id => { this.elements[id] = document.getElementById(id); });
    }

    attachEventListeners() {
        this.elements.startCallsBtn?.addEventListener('click', () => this.startCalling());
        this.elements.stopCallsBtn?.addEventListener('click', () => this.stopCalling());
        this.elements.refreshBtn?.addEventListener('click', () => this.refreshAll());
        ['cityFilter', 'statusFilter', 'priorityFilter'].forEach(filterId => {
            this.elements[filterId]?.addEventListener('change', () => this.applyFilters());
        });
        this.elements.selectedFilter?.addEventListener('change', () => this.applyFilters());
        this.elements.selectAllBtn?.addEventListener('click', () => this.selectAllLeads(true));
        this.elements.deselectAllBtn?.addEventListener('click', () => this.selectAllLeads(false));
        this.elements.resetLeadsBtn?.addEventListener('click', () => this.resetLeads());
        this.elements.masterCheckbox?.addEventListener('change', (e) => this.toggleAllCheckboxes(e.target.checked));
        this.elements.testConnectionBtn?.addEventListener('click', () => this.testConnection());
        this.elements.saveConfigBtn?.addEventListener('click', () => this.saveConfiguration());
        document.addEventListener('keydown', (e) => this.handleKeyboard(e));
    }

    async loadInitialData() {
        // Primero, cargamos los leads y esperamos a que la tabla se dibuje.
        await this.loadLeads();
        
        // Una vez que los leads están cargados y visibles, cargamos el resto en paralelo.
        await Promise.all([
            this.updateSystemStatus(),
            this.loadCities(),
            this.testConnection()
        ]);
    }

    async startCalling() {
        try {
            this.showLoader(this.elements.startCallsBtn, true);
            const config = {
                max_concurrent: this.config.maxConcurrentCalls,
                selected_leads: this.getSelectedLeadIds()
            };
            const response = await this.apiCall('POST', '/start', config);
            if (response.success) {
                this.state.isRunning = true;
                this.updateControlButtons();
                this.showNotification('Sistema de llamadas iniciado', 'success');
                this.elements.progressSection.style.display = 'block';
                this.config.refreshInterval = 1000;
                this.startAutoRefresh();
            } else {
                throw new Error(response.error || 'Error desconocido');
            }
        } catch (error) {
            console.error('Error iniciando llamadas:', error);
            this.showNotification(`Error: ${error.message}`, 'error');
        } finally {
            this.showLoader(this.elements.startCallsBtn, false);
        }
    }

    async stopCalling() {
        try {
            this.showLoader(this.elements.stopCallsBtn, true);
            const response = await this.apiCall('POST', '/stop');
            if (response.success) {
                this.state.isRunning = false;
                this.updateControlButtons();
                this.showNotification('Sistema de llamadas detenido', 'warning');
                this.elements.progressSection.style.display = 'none';
                this.config.refreshInterval = 10000;
                this.startAutoRefresh();
            } else {
                throw new Error(response.error || 'Error desconocido');
            }
        } catch (error) {
            console.error('Error deteniendo llamadas:', error);
            this.showNotification(`Error: ${error.message}`, 'error');
        } finally {
            this.showLoader(this.elements.stopCallsBtn, false);
        }
    }

    async updateSystemStatus() {
        try {
            const response = await this.apiCall('GET', '/status');
            if (response.success) {
                const { system_status } = response;
                this.state.isRunning = system_status.call_manager.is_running;
                this.state.stats = system_status.call_manager.stats;
                this.updateSystemStatusUI(system_status);
                this.updateStatsUI(this.state.stats);
                this.updateProgressUI(system_status.call_manager);
                this.updateControlButtons();
            }
        } catch (error) {
            console.error('Error actualizando estado:', error);
            this.updateConnectionStatus(false);
        }
    }

    updateSystemStatusUI(systemStatus) {
        const { call_manager, pearl_connection } = systemStatus;
        if (this.elements.systemStatus) {
            if (call_manager.is_running) {
                this.elements.systemStatus.textContent = 'ACTIVO';
                this.elements.systemStatus.className = 'badge bg-success fs-6';
            } else {
                this.elements.systemStatus.textContent = 'INACTIVO';
                this.elements.systemStatus.className = 'badge bg-secondary fs-6';
            }
        }
        this.updateConnectionStatus(pearl_connection);
    }

    updateConnectionStatus(connected) {
        if (!this.elements.connectionStatus) return;
        if (connected) {
            this.elements.connectionStatus.innerHTML = '<i class="bi bi-circle-fill"></i> Conectado';
            this.elements.connectionStatus.className = 'text-success';
        } else {
            this.elements.connectionStatus.innerHTML = '<i class="bi bi-circle-fill"></i> Desconectado';
            this.elements.connectionStatus.className = 'text-danger';
        }
    }

    updateStatsUI(stats) {
        if (this.elements.totalCallsCount) this.elements.totalCallsCount.textContent = stats.total_calls || 0;
        if (this.elements.successCallsCount) this.elements.successCallsCount.textContent = stats.successful_calls || 0;
        if (this.elements.activeCallsCount) this.elements.activeCallsCount.textContent = stats.active_calls || 0;
        if (this.elements.failedCallsCount) this.elements.failedCallsCount.textContent = stats.failed_calls || 0;
    }

    updateProgressUI(managerStatus) {
        if (!this.elements.progressBar || !this.elements.progressText) return;
        const { queue_size, active_calls, stats } = managerStatus;
        const total = stats.total_calls + queue_size + active_calls;
        const completed = stats.total_calls;
        if (total > 0) {
            const percentage = Math.round((completed / total) * 100);
            this.elements.progressBar.style.width = `${percentage}%`;
            this.elements.progressBar.setAttribute('aria-valuenow', percentage);
            this.elements.progressText.textContent = `${completed} / ${total}`;
        } else {
            this.elements.progressBar.style.width = '0%';
            this.elements.progressText.textContent = '0 / 0';
        }
    }

    updateControlButtons() {
        if (this.elements.startCallsBtn && this.elements.stopCallsBtn) {
            if (this.state.isRunning) {
                this.elements.startCallsBtn.disabled = true;
                this.elements.stopCallsBtn.disabled = false;
                this.elements.stopCallsBtn.classList.add('btn-pulsing');
            } else {
                this.elements.startCallsBtn.disabled = false;
                this.elements.stopCallsBtn.disabled = true;
                this.elements.stopCallsBtn.classList.remove('btn-pulsing');
            }
        }
    }

    async loadLeads() {
        try {
            const params = new URLSearchParams({
                ...this.state.filters,
                limit: this.state.pagination.limit,
                offset: this.state.pagination.offset,
                selected_only: this.state.filters.selectedOnly
            });
            const response = await this.apiCall('GET', `/leads?${params}`);
            if (response.success) {
                this.state.currentLeads = response.leads;
                this.state.pagination.total = response.pagination.total;
                this.renderLeadsTable();
                this.updatePagination();
                this.updateLeadsInfo();
            }
        } catch (error) {
            console.error('Error cargando leads:', error);
            this.showNotification('Error cargando leads', 'error');
        }
    }

    renderLeadsTable() {
        if (!this.elements.leadsTableBody) return;
        if (this.state.currentLeads.length === 0) {
            this.elements.leadsTableBody.innerHTML = `
                <tr><td colspan="10" class="text-center py-4">
                    <i class="bi bi-inbox fs-1 text-muted"></i>
                    <p class="mt-2 mb-0 text-muted">No se encontraron leads</p>
                </td></tr>`;
            return;
        }
        const html = this.state.currentLeads.map(lead => this.renderLeadRow(lead)).join('');
        this.elements.leadsTableBody.innerHTML = html;
        this.attachLeadEventListeners();
    }

    attachLeadEventListeners() {
        this.elements.leadsTableBody.querySelectorAll('.lead-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                const leadId = parseInt(e.target.dataset.leadId);
                if (e.target.checked) {
                    this.state.selectedLeads.add(leadId);
                } else {
                    this.state.selectedLeads.delete(leadId);
                }
                this.updateMasterCheckbox();
            });
        });
        this.elements.leadsTableBody.querySelectorAll('.view-details-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const leadId = parseInt(e.target.dataset.leadId);
                this.showLeadDetails(leadId);
            });
        });
    }

    renderLeadRow(lead) {
        const isSelected = this.state.selectedLeads.has(lead.id);
        const statusClass = `status-${lead.call_status}`;
        const lastCall = lead.last_call_attempt ? 
            new Date(lead.last_call_attempt).toLocaleString('es-ES', {
                day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit'
            }) : '-';
        return `
            <tr class="fade-in ${lead.call_status === 'calling' ? 'calling-indicator' : ''}">
                <td><input type="checkbox" class="form-check-input lead-checkbox" 
                           data-lead-id="${lead.id}" ${isSelected ? 'checked' : ''}></td>
                <td><strong>${lead.nombre || ''} ${lead.apellidos || ''}</strong></td>
                <td><span class="text-monospace">${lead.telefono}</span>
                    ${lead.telefono2 ? `<br><small class="text-muted">${lead.telefono2}</small>` : ''}</td>
                <td>${lead.ciudad || '-'}</td>
                <td class="text-truncate-2" title="${lead.nombre_clinica || '-'}">${lead.nombre_clinica || '-'}</td>
                <td><span class="badge status-badge ${statusClass}">${this.getStatusLabel(lead.call_status)}</span></td>
                <td><span class="badge bg-info">${lead.call_priority || 3}</span></td>
                <td><span class="badge bg-secondary">${lead.call_attempts_count || 0}</span></td>
                <td><small>${lastCall}</small></td>
                <td><button class="btn btn-sm btn-outline-primary view-details-btn" 
                            data-lead-id="${lead.id}" title="Ver detalles"><i class="bi bi-eye"></i></button></td>
            </tr>`;
    }

    getStatusLabel(status) {
        const labels = {
            'no_selected': 'No Seleccionado', 'selected': 'Seleccionado', 'calling': 'Llamando',
            'completed': 'Completado', 'error': 'Error', 'busy': 'Ocupado', 'no_answer': 'Sin Respuesta'
        };
        return labels[status] || status;
    }

    async showLeadDetails(leadId) {
        const lead = this.state.currentLeads.find(l => l.id === leadId);
        if (!lead) return;
        const content = `
            <div class="row">
                <div class="col-md-6">
                    <h6>Información Personal</h6>
                    <p><strong>Nombre:</strong> ${lead.nombre} ${lead.apellidos}</p>
                    <p><strong>Teléfono:</strong> ${lead.telefono}</p>
                    ${lead.telefono2 ? `<p><strong>Teléfono 2:</strong> ${lead.telefono2}</p>` : ''}
                    <p><strong>Ciudad:</strong> ${lead.ciudad || '-'}</p>
                </div>
                <div class="col-md-6">
                    <h6>Estado de Llamadas</h6>
                    <p><strong>Estado:</strong> <span class="badge status-badge status-${lead.call_status}">${this.getStatusLabel(lead.call_status)}</span></p>
                    <p><strong>Prioridad:</strong> ${lead.call_priority}</p>
                    <p><strong>Intentos:</strong> ${lead.call_attempts_count || 0}</p>
                    <p><strong>Última llamada:</strong> ${lead.last_call_attempt ? new Date(lead.last_call_attempt).toLocaleString('es-ES') : '-'}</p>
                </div>
            </div>
            ${lead.call_error_message ? `<div class="alert alert-danger mt-3"><strong>Último error:</strong> ${lead.call_error_message}</div>` : ''}
            <div class="mt-3"><h6>Clínica</h6><p><strong>Nombre:</strong> ${lead.nombre_clinica || '-'}</p></div>`;
        document.getElementById('leadDetailsContent').innerHTML = content;
        new bootstrap.Modal(document.getElementById('leadDetailsModal')).show();
    }

    async applyFilters() {
        this.state.filters = {
            city: this.elements.cityFilter?.value || '',
            status: this.elements.statusFilter?.value || '',
            priority: this.elements.priorityFilter?.value || '',
            selectedOnly: this.elements.selectedFilter?.checked || false
        };
        this.state.pagination.offset = 0;
        await this.loadLeads();
    }

    async selectAllLeads(selected) {
        try {
            const leadIds = this.state.currentLeads.map(lead => lead.id);
            const response = await this.apiCall('POST', '/leads/select', { lead_ids: leadIds, selected: selected });
            if (response.success) {
                if (selected) {
                    leadIds.forEach(id => this.state.selectedLeads.add(id));
                } else {
                    leadIds.forEach(id => this.state.selectedLeads.delete(id));
                }
                this.renderLeadsTable();
                this.updateMasterCheckbox();
                this.showNotification(`${selected ? 'Seleccionados' : 'Deseleccionados'} ${leadIds.length} leads`, 'info');
            }
        } catch (error) {
            console.error('Error seleccionando leads:', error);
            this.showNotification('Error al actualizar selección', 'error');
        }
    }

    async resetLeads() {
        const confirm = await this.showConfirm('¿Reiniciar estados?', 'Esto reiniciará el estado de todos los leads visibles. ¿Continuar?');
        if (!confirm) return;
        try {
            const leadIds = this.state.currentLeads.map(lead => lead.id);
            const response = await this.apiCall('POST', '/leads/reset', {
                lead_ids: leadIds, reset_attempts: true, reset_selection: false
            });
            if (response.success) {
                await this.loadLeads();
                this.showNotification(`Reiniciados ${response.updated_count} leads`, 'success');
            }
        } catch (error) {
            console.error('Error reiniciando leads:', error);
            this.showNotification('Error al reiniciar leads', 'error');
        }
    }

    updateMasterCheckbox() {
        if (!this.elements.masterCheckbox) return;
        const currentLeadIds = this.state.currentLeads.map(l => l.id);
        const selectedCurrent = currentLeadIds.filter(id => this.state.selectedLeads.has(id));
        if (selectedCurrent.length === 0) {
            this.elements.masterCheckbox.checked = false;
            this.elements.masterCheckbox.indeterminate = false;
        } else if (selectedCurrent.length === currentLeadIds.length) {
            this.elements.masterCheckbox.checked = true;
            this.elements.masterCheckbox.indeterminate = false;
        } else {
            this.elements.masterCheckbox.checked = false;
            this.elements.masterCheckbox.indeterminate = true;
        }
    }

    toggleAllCheckboxes(checked) {
        const currentLeadIds = this.state.currentLeads.map(l => l.id);
        if (checked) {
            currentLeadIds.forEach(id => this.state.selectedLeads.add(id));
        } else {
            currentLeadIds.forEach(id => this.state.selectedLeads.delete(id));
        }
        this.renderLeadsTable();
    }

    getSelectedLeadIds() { return Array.from(this.state.selectedLeads); }

    async loadCities() {
        try {
            // Pedimos los leads solo para extraer las ciudades, sin afectar el estado principal.
            const response = await this.apiCall('GET', '/leads?limit=1000');
            if (response.success) {
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
