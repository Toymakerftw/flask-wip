// Configuration and Constants
const CONFIG = {
    REFRESH_INTERVAL: 5 * 60 * 1000, // 5 minutes
    BASE_URL: window.location.origin,
    ENDPOINTS: {
        ADD_WATCHLIST: '/watchlist/add',
        DELETE_WATCHLIST: '/watchlist/delete',
        GET_WATCHLIST_DATA: '/watchlist/data'
    }
};

// DOM Elements
const elements = {
    watchlistModal: document.getElementById('watchlistModal'),
    watchlistForm: document.getElementById('watchlistForm'),
    watchlistContainer: document.getElementById('watchlistContainer'),
    currentDate: document.getElementById('current-date'),
    currentTime: document.getElementById('current-time'),
    lastUpdate: document.getElementById('lastUpdate'),
    gainersCount: document.getElementById('gainersCount'),
    losersCount: document.getElementById('losersCount')
};

// API Service
const apiService = {
    async fetchWithErrorHandling(endpoint, options = {}) {
        try {
            const response = await fetch(`${CONFIG.BASE_URL}${endpoint}`, options);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Request failed');
            }
            
            return data;
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    },

    async addToWatchlist(formData) {
        return this.fetchWithErrorHandling(CONFIG.ENDPOINTS.ADD_WATCHLIST, {
            method: 'POST',
            body: formData
        });
    },

    async deleteFromWatchlist(itemId) {
        return this.fetchWithErrorHandling(`${CONFIG.ENDPOINTS.DELETE_WATCHLIST}/${itemId}`, {
            method: 'DELETE'
        });
    },

    async getWatchlistData() {
        return this.fetchWithErrorHandling(CONFIG.ENDPOINTS.GET_WATCHLIST_DATA);
    }
};

// UI Update Functions
const uiUpdater = {
    updateDateTime() {
        const now = new Date();
        if (elements.currentDate) {
            elements.currentDate.textContent = now.toLocaleDateString('en-US', {
                weekday: 'long',
                year: 'numeric',
                month: 'long',
                day: 'numeric'
            });
        }
        if (elements.currentTime) {
            elements.currentTime.textContent = now.toLocaleTimeString('en-US', {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
        }
    },

    updateMarketOverview(data = {}) {
        let gainers = 0;
        let losers = 0;
        
        Object.values(data).forEach(info => {
            if (info.stock_data?.percent_change) {
                if (info.stock_data.percent_change > 0) gainers++;
                else if (info.stock_data.percent_change < 0) losers++;
            }
        });
        
        if (elements.gainersCount) elements.gainersCount.textContent = gainers;
        if (elements.losersCount) elements.losersCount.textContent = losers;
        if (elements.lastUpdate) elements.lastUpdate.textContent = new Date().toLocaleTimeString();
    },

    createWatchlistItemHTML(data) {
        return `
            <div class="flex justify-between items-start">
                <div>
                    <h3 class="font-medium text-gray-900 dark:text-gray-100">${data.company_name}</h3>
                    <p class="text-sm text-gray-600 dark:text-gray-400">Loading data...</p>
                </div>
                <div class="flex items-center gap-3">
                    <button onclick="window.dashboardApp.deleteWatchlistItem(${data.id})" 
                            class="text-red-500 hover:text-red-600 p-1 rounded-full hover:bg-red-50 dark:hover:bg-red-900/20">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                                  d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                        </svg>
                    </button>
                </div>
            </div>
            <div class="error-message text-sm text-red-500 mt-2"></div>
        `;
    },

    addWatchlistItemToDOM(data) {
        const noStocksMessage = elements.watchlistContainer.querySelector('div:last-child');
        if (noStocksMessage?.textContent.trim() === 'No stocks added yet') {
            noStocksMessage.remove();
        }

        const newItem = document.createElement('div');
        newItem.id = `watchlist-item-${data.id}`;
        newItem.setAttribute('data-company', data.company_name);
        newItem.className = 'p-4 border-b border-gray-200 dark:border-gray-700';
        newItem.innerHTML = this.createWatchlistItemHTML(data);
        
        elements.watchlistContainer.insertBefore(newItem, elements.watchlistContainer.firstChild);
    },

    updateStockData(element, data) {
        if (!data || data.error) {
            const errorElement = element.querySelector('.error-message');
            if (errorElement) {
                errorElement.textContent = data?.error || 'Error loading data';
            }
            return;
        }

        // Update stock information
        const priceElement = element.querySelector('.stock-price');
        const changeElement = element.querySelector('.stock-change');
        
        if (priceElement && data.stock_data?.current_price) {
            priceElement.textContent = `$${data.stock_data.current_price.toFixed(2)}`;
        }
        
        if (changeElement && data.stock_data?.percent_change) {
            changeElement.textContent = `${data.stock_data.percent_change.toFixed(2)}%`;
            changeElement.className = `stock-change ${
                data.stock_data.percent_change > 0 ? 'text-green-500' : 'text-red-500'
            }`;
        }

        // Update technical indicators if they exist
        if (data.stock_data?.technical_indicators) {
            const indicators = data.stock_data.technical_indicators;
            ['rsi', 'volatility', 'macd', 'macd-signal'].forEach(indicator => {
                const element = document.querySelector(`[data-indicator="${indicator}"]`);
                if (element && indicators[indicator]) {
                    element.textContent = indicators[indicator].toFixed(2);
                }
            });
        }
    }
};

// Main App Logic
const dashboardApp = {
    async refreshWatchlistData() {
        try {
            const data = await apiService.getWatchlistData();
            uiUpdater.updateMarketOverview(data);
            
            // Update each watchlist item
            Object.entries(data).forEach(([company, info]) => {
                const itemElement = document.querySelector(`[data-company="${company}"]`);
                if (itemElement) {
                    uiUpdater.updateStockData(itemElement, info);
                }
            });
        } catch (error) {
            console.error('Failed to refresh watchlist:', error);
            alert('Failed to refresh watchlist data. Please try again later.');
        }
    },

    async handleWatchlistSubmit(e) {
        e.preventDefault();
        
        try {
            const formData = new FormData(e.target);
            const data = await apiService.addToWatchlist(formData);
            
            uiUpdater.addWatchlistItemToDOM(data);
            this.closeWatchlistModal();
            await this.refreshWatchlistData();
        } catch (error) {
            alert(error.message || 'Failed to add to watchlist');
        }
    },

    async deleteWatchlistItem(itemId) {
        if (!confirm('Are you sure you want to remove this company from your watchlist?')) {
            return;
        }
        
        try {
            await apiService.deleteFromWatchlist(itemId);
            const item = document.getElementById(`watchlist-item-${itemId}`);
            item?.remove();
            
            if (elements.watchlistContainer.children.length === 0) {
                const placeholder = document.createElement('div');
                placeholder.className = 'p-4 text-center text-gray-500 dark:text-gray-400';
                placeholder.textContent = 'No stocks added yet';
                elements.watchlistContainer.appendChild(placeholder);
            }
        } catch (error) {
            alert(error.message || 'Failed to delete watchlist item');
        }
    },

    openWatchlistModal() {
        elements.watchlistModal?.classList.remove('hidden');
    },

    closeWatchlistModal() {
        elements.watchlistModal?.classList.add('hidden');
        elements.watchlistForm?.reset();
    },

    initialize() {
        // Initialize date/time updates
        uiUpdater.updateDateTime();
        setInterval(() => uiUpdater.updateDateTime(), 1000);

        // Set up event listeners
        elements.watchlistForm?.addEventListener('submit', (e) => this.handleWatchlistSubmit(e));

        // Initial data load
        this.refreshWatchlistData();

        // Set up periodic refresh
        setInterval(() => this.refreshWatchlistData(), CONFIG.REFRESH_INTERVAL);
    }
};

// Initialize the dashboard
document.addEventListener('DOMContentLoaded', () => dashboardApp.initialize());

// Export functions for global access
window.dashboardApp = {
    openWatchlistModal: () => dashboardApp.openWatchlistModal(),
    closeWatchlistModal: () => dashboardApp.closeWatchlistModal(),
    deleteWatchlistItem: (itemId) => dashboardApp.deleteWatchlistItem(itemId),
    refreshWatchlistData: () => dashboardApp.refreshWatchlistData()
};