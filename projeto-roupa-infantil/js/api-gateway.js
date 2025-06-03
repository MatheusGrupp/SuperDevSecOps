// API Gateway Integration for SuperDevSecOps
// Conecta as páginas existentes com os microsserviços Django

const API_CONFIG = {
    BASE_URL: window.location.hostname === 'localhost' 
        ? 'http://localhost:8000/api' 
        : 'https://api.superdevsecops.com/api',
    TIMEOUT: 30000,
    RETRY_ATTEMPTS: 3
};

// Classe principal para comunicação com API Gateway
class APIGateway {
    constructor() {
        this.token = localStorage.getItem('auth_token');
        this.refreshToken = localStorage.getItem('refresh_token');
    }

    // Configuração dos headers padrão
    getHeaders(additionalHeaders = {}) {
        const headers = {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRF-Token': this.getCSRFToken(),
            ...additionalHeaders
        };

        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }

        return headers;
    }

    // Obter CSRF Token
    getCSRFToken() {
        const name = 'csrftoken';
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // Método genérico para requisições
    async request(endpoint, options = {}) {
        const url = `${API_CONFIG.BASE_URL}${endpoint}`;
        const config = {
            ...options,
            headers: this.getHeaders(options.headers || {})
        };

        try {
            const response = await fetch(url, config);

            // Verificar se o token expirou
            if (response.status === 401) {
                const refreshed = await this.refreshAuthToken();
                if (refreshed) {
                    // Tentar novamente com novo token
                    config.headers['Authorization'] = `Bearer ${this.token}`;
                    return await fetch(url, config);
                } else {
                    // Redirecionar para login
                    window.location.href = '/login.html';
                    return;
                }
            }

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('API Request Error:', error);
            throw error;
        }
    }

    // Refresh do token de autenticação
    async refreshAuthToken() {
        try {
            const response = await fetch(`${API_CONFIG.BASE_URL}/auth/refresh`, {
                method: 'POST',
                headers: this.getHeaders(),
                body: JSON.stringify({ refresh_token: this.refreshToken })
            });

            if (response.ok) {
                const data = await response.json();
                this.token = data.access_token;
                this.refreshToken = data.refresh_token;
                localStorage.setItem('auth_token', this.token);
                localStorage.setItem('refresh_token', this.refreshToken);
                return true;
            }
        } catch (error) {
            console.error('Token refresh failed:', error);
        }
        return false;
    }

    // === Métodos de Autenticação ===
    async login(email, password) {
        const response = await this.request('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ email, password })
        });

        if (response.access_token) {
            this.token = response.access_token;
            this.refreshToken = response.refresh_token;
            localStorage.setItem('auth_token', this.token);
            localStorage.setItem('refresh_token', this.refreshToken);
            localStorage.setItem('user_data', JSON.stringify(response.user));
        }

        return response;
    }

    async logout() {
        try {
            await this.request('/auth/logout', { method: 'POST' });
        } finally {
            localStorage.removeItem('auth_token');
            localStorage.removeItem('refresh_token');
            localStorage.removeItem('user_data');
            window.location.href = '/login.html';
        }
    }

    async register(userData) {
        return await this.request('/auth/register', {
            method: 'POST',
            body: JSON.stringify(userData)
        });
    }

    async forgotPassword(email) {
        return await this.request('/auth/forgot-password', {
            method: 'POST',
            body: JSON.stringify({ email })
        });
    }

    async resetPassword(token, newPassword) {
        return await this.request('/auth/reset-password', {
            method: 'POST',
            body: JSON.stringify({ token, new_password: newPassword })
        });
    }

    // === Métodos de Tarefas ===
    async getTasks(filters = {}) {
        const queryParams = new URLSearchParams(filters).toString();
        return await this.request(`/tasks?${queryParams}`);
    }

    async getTask(taskId) {
        return await this.request(`/tasks/${taskId}`);
    }

    async createTask(taskData) {
        return await this.request('/tasks', {
            method: 'POST',
            body: JSON.stringify(taskData)
        });
    }

    async updateTask(taskId, taskData) {
        return await this.request(`/tasks/${taskId}`, {
            method: 'PUT',
            body: JSON.stringify(taskData)
        });
    }

    async deleteTask(taskId) {
        return await this.request(`/tasks/${taskId}`, {
            method: 'DELETE'
        });
    }

    // === Métodos de Usuário ===
    async getProfile() {
        return await this.request('/users/profile');
    }

    async updateProfile(profileData) {
        return await this.request('/users/profile', {
            method: 'PUT',
            body: JSON.stringify(profileData)
        });
    }

    async changePassword(currentPassword, newPassword) {
        return await this.request('/users/change-password', {
            method: 'POST',
            body: JSON.stringify({
                current_password: currentPassword,
                new_password: newPassword
            })
        });
    }

    // === Métodos de Relatórios ===
    async getReports(type, filters = {}) {
        const queryParams = new URLSearchParams(filters).toString();
        return await this.request(`/reports/${type}?${queryParams}`);
    }

    // === Métodos de Notificações ===
    async getNotifications() {
        return await this.request('/notifications');
    }

    async markNotificationAsRead(notificationId) {
        return await this.request(`/notifications/${notificationId}/read`, {
            method: 'POST'
        });
    }

    // === Upload de Arquivos ===
    async uploadFile(file, taskId) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('task_id', taskId);

        return await this.request('/files/upload', {
            method: 'POST',
            headers: {
                // Não definir Content-Type para FormData
            },
            body: formData
        });
    }

    // === Métodos Admin ===
    async getUsers(filters = {}) {
        const queryParams = new URLSearchParams(filters).toString();
        return await this.request(`/admin/users?${queryParams}`);
    }

    async getUserById(userId) {
        return await this.request(`/admin/users/${userId}`);
    }

    async updateUser(userId, userData) {
        return await this.request(`/admin/users/${userId}`, {
            method: 'PUT',
            body: JSON.stringify(userData)
        });
    }

    async deleteUser(userId) {
        return await this.request(`/admin/users/${userId}`, {
            method: 'DELETE'
        });
    }

    // === Métricas e Monitoramento ===
    async getSystemMetrics() {
        return await this.request('/metrics/system');
    }

    async getSecurityMetrics() {
        return await this.request('/metrics/security');
    }
}

// Instância global do API Gateway
window.apiGateway = new APIGateway();

// Funções auxiliares para integração com páginas existentes
function setupAuthCheck() {
    const publicPages = ['/login.html', '/cadastro.html', '/index.html'];
    const currentPage = window.location.pathname;

    if (!publicPages.includes(currentPage) && !window.apiGateway.token) {
        window.location.href = '/login.html';
    }
}

// Executar verificação ao carregar a página
document.addEventListener('DOMContentLoaded', setupAuthCheck);