document.addEventListener('DOMContentLoaded', () => {
    const API_BASE_URL = '/api/v1';

    const createCampaignForm = document.getElementById('create-campaign-form');
    const campaignListContainer = document.getElementById('campaign-list');
    const editorSection = document.getElementById('editor-section');
    const notificationsContainer = document.getElementById('notifications');

    let allOffers = [];
    let allCampaigns = [];
    let activeCampaign = null;
    let stagedStreams = []; // Рабочая копия потоков для редактирования
    let createOfferChoiceInstance = null; // Для селекта в форме создания
    let choiceInstances = {}; // Хранилище для экземпляров Choices.js
    function showNotification(message, type = 'success') {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        notificationsContainer.prepend(notification);
        setTimeout(() => {
            notification.classList.add('fade-out');
            notification.addEventListener('animationend', () => {
                notification.remove();
            });
        }, 5000);
    }

    async function apiCall(endpoint, options = {}) {
        try {
            const response = await fetch(`${API_BASE_URL}${endpoint}`, options);
            if (!response.ok) {
                let errorDetail = `Ошибка ${response.status}: ${response.statusText}`;
                try {
                    const errorData = await response.json();
                    errorDetail = errorData.detail || JSON.stringify(errorData);
                } catch (e) {
                }
                throw new Error(errorDetail);
            }
            const contentType = response.headers.get("content-type");
            if (contentType && contentType.indexOf("application/json") !== -1) {
                return await response.json();
            }
            return {};
        } catch (error) {
            showNotification(`Ошибка: ${error.message}`, 'error');
            throw error;
        }
    }

    createCampaignForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(createCampaignForm);
        const data = Object.fromEntries(formData.entries());
        
        data.country_codes = data.country_codes.split(',')
            .map(code => code.trim().toUpperCase())
            .filter(code => code.length === 2);
        data.offer_id = parseInt(data.offer_id, 10);

        try {
            const createdCampaign = await apiCall('/campaigns', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
            });
            showNotification(`Кампания "${createdCampaign.name}" (ID: ${createdCampaign.id}) успешно создана!`);
            createCampaignForm.reset();
            allCampaigns = await apiCall('/campaigns');
            renderCampaignList();
        } catch (error) {
        }
    });

    async function loadAllOffers() {
        try {
            allOffers = await apiCall('/offers');
        } catch (error) {
            showNotification('Не удалось загрузить список офферов.', 'error');
        }
    }
    async function initializeEditor() {
        try {
            [allCampaigns, allOffers] = await Promise.all([
                apiCall('/campaigns'),
                apiCall('/offers')
            ]);
            renderCampaignList();
            initializeCreateFormChoices();
        } catch (error) {
            showNotification('Не удалось загрузить начальные данные.', 'error');
        }
    }

    function renderCampaignList() {
        campaignListContainer.innerHTML = '';
        allCampaigns.forEach(campaign => {
            const item = document.createElement('div');
            item.className = 'campaign-list-item';
            item.textContent = campaign.name;
            item.dataset.campaignId = campaign.id;
            if (activeCampaign && activeCampaign.id === campaign.id) {
                item.classList.add('active');
            }
            campaignListContainer.appendChild(item);
        });
    }

    campaignListContainer.addEventListener('click', async (e) => {
        if (e.target.classList.contains('campaign-list-item')) {
            const campaignId = e.target.dataset.campaignId;
            loadCampaignForEditing(campaignId);
        }
    });

    async function loadCampaignForEditing(campaignId) {
        editorSection.innerHTML = '<p>Загрузка...</p>';
        editorSection.classList.remove('hidden');

        try {
            const campaign = await apiCall(`/campaigns/${campaignId}`);
            activeCampaign = campaign;
            stagedStreams = JSON.parse(JSON.stringify(campaign.streams));
            renderCampaignList();
            renderStreamsTable();
        } catch (error) {
            console.error('Failed to load campaign for editing:', error);
            editorSection.innerHTML = '<p>Не удалось загрузить кампанию.</p>';
        }
    }

    function renderStreamsTable() {
        let tableHtml = `<div class="editor-header">
                <h3>Редактирование: ${activeCampaign.name}</h3>
                <button id="publish-changes-btn" class="hidden">Опубликовать изменения</button>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Оффер, Тип, Регион</th>
                        <th>Share</th>
                        <th>Stats</th>
                        <th>Trends</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>`;

        stagedStreams.forEach(stream => {
            tableHtml += `<tr class="stream-header-row" data-stream-id="${stream.id}"><td colspan="5">${stream.name}</td></tr>`;

            const isEditableStream = stream.schema === 'landings';

            if (isEditableStream) {
                const streamOffers = stream.offers || [];
                if (streamOffers.length > 0) {
                    streamOffers.forEach(offer => {
                        const offerDetails = allOffers.find(o => o.id === offer.offer_id);
                        const offerName = offerDetails ? offerDetails.name : `ID ${offer.offer_id}`;
                        const offerInfo = `${offerName}, Основной, ALL`;
                        tableHtml += `<tr data-offer-id="${offer.offer_id}" class="${offer.changed ? 'changed' : ''}">
                            <td>${offerInfo}</td>
                            <td>${offer.share}%</td>
                            <td>-</td>
                            <td>-</td>
                            <td><button class="remove-offer-btn" data-stream-id="${stream.id}" data-offer-id="${offer.offer_id}">&times;</button></td>
                        </tr>`;
                    });
                } else {
                     tableHtml += `<tr><td colspan="5">В этом потоке нет офферов. Добавьте первый.</td></tr>`;
                }

                let options = allOffers.map(o => `<option value="${o.id}">${o.name}</option>`).join('');
                tableHtml += `<tr class="add-offer-row" data-stream-id="${stream.id}">
                    <td colspan="4">
                        <select class="offer-select-searchable" data-stream-id="${stream.id}"></select>
                    </td>
                    <td><button class="add-offer-btn" data-stream-id="${stream.id}">Добавить</button></td>
                </tr>`;
            } else {
                const streamInfo = stream.action_payload || "Системное действие";
                tableHtml += `<tr>
                    <td colspan="4">Действие: <strong>Редирект на ${streamInfo}</strong></td>
                    <td></td>
                </tr>`;
            }
        });

        tableHtml += `</tbody></table>`;
        editorSection.innerHTML = tableHtml;

        initializeChoices();

        document.getElementById('publish-changes-btn').addEventListener('click', publishChanges);
    }

    editorSection.addEventListener('click', (e) => {
        const streamId = parseInt(e.target.dataset.streamId, 10);

        const targetStream = stagedStreams.find(s => s.id === streamId);
        if (!targetStream) return;

        if (e.target.classList.contains('add-offer-btn')) {
            const select = e.target.closest('.add-offer-row').querySelector('.offer-select-searchable');
            const offerId = parseInt(select.value, 10);
            if (!offerId) return;

            targetStream.offers.push({ offer_id: offerId, share: 0, changed: true });
            recalculateShares(targetStream.offers);
            renderStreamsTable();
            document.getElementById('publish-changes-btn').classList.remove('hidden');
        }

        if (e.target.classList.contains('remove-offer-btn')) {
            const offerId = parseInt(e.target.dataset.offerId, 10);
            targetStream.offers = targetStream.offers.filter(o => o.offer_id !== offerId);
            recalculateShares(targetStream.offers);
            renderStreamsTable();
            document.getElementById('publish-changes-btn').classList.remove('hidden');
        }
    });

    function initializeChoices() {
        Object.values(choiceInstances).forEach(instance => instance.destroy());
        choiceInstances = {};

        document.querySelectorAll('.offer-select-searchable').forEach(selectElement => {
            const streamId = selectElement.dataset.streamId;
            const choices = new Choices(selectElement, {
                searchEnabled: true,
                removeItemButton: true,
                placeholder: true,
                placeholderValue: '-- Выберите оффер для добавления --',
                searchPlaceholderValue: 'Введите для поиска...',
            });
            const offerChoices = allOffers.map(o => ({ value: o.id, label: o.name }));
            choices.setChoices(offerChoices, 'value', 'label', false);
            choiceInstances[streamId] = choices;
        });
    }

    function initializeCreateFormChoices() {
        const selectElement = document.getElementById('offer-select-create');
        if (!selectElement) return;

        if (createOfferChoiceInstance) {
            createOfferChoiceInstance.destroy();
        }
        createOfferChoiceInstance = new Choices(selectElement, {
            searchEnabled: true,
            placeholder: true,
            placeholderValue: '-- Выберите оффер --',
            searchPlaceholderValue: 'Введите для поиска...',
        });
        const offerChoices = allOffers.map(o => ({ value: o.id, label: o.name }));
        createOfferChoiceInstance.setChoices(offerChoices, 'value', 'label', false);
    }

    async function publishChanges() {
        try {
            const streamsToPublish = JSON.parse(JSON.stringify(stagedStreams));
            streamsToPublish.forEach(s => s.offers && s.offers.forEach(o => delete o.changed));

            await apiCall(`/campaigns/${activeCampaign.id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ streams: streamsToPublish }),
            });
            showNotification('Изменения успешно опубликованы!');
            stagedStreams.forEach(s => s.offers && s.offers.forEach(o => delete o.changed));
            renderStreamsTable();
            document.getElementById('publish-changes-btn').classList.add('hidden');
        } catch (error) {
            showNotification('Не удалось опубликовать изменения.', 'error');
        }
    }

    function recalculateShares(offers) {
        if (!offers || offers.length === 0) return;

        const numOffers = offers.length;
        const baseShare = Math.floor(100 / numOffers);
        let remainder = 100 % numOffers;

        offers.forEach((offer, index) => {
            offer.share = baseShare;
            if (remainder > 0) {
                offer.share++;
                remainder--;
            }
            offer.changed = true;
        });
    }

    initializeEditor();
});