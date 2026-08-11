/* ==========================================================================
   VARIABLE PRODUCT CREATION — CLIENT SCRIPT
   Handles attributes, terms, cartesian variation generator,
   rich variation cards matching WooCommerce UI, and n8n submission.
   ========================================================================== */

/* ==========================================================================
   1. CONFIGURATION & WEBHOOK ENDPOINTS
   ========================================================================== */
const CONFIG = {
    CATEGORY_LIST_API_URL:          "https://n8n.srv917960.hstgr.cloud/webhook/get-categories-acordell",
    CATEGORY_CREATE_API_URL:        "https://n8n.srv917960.hstgr.cloud/webhook/create-category-acordell",

    BRAND_LIST_API_URL:             "https://n8n.srv917960.hstgr.cloud/webhook/get-brands-acordell",
    BRAND_CREATE_API_URL:           "https://n8n.srv917960.hstgr.cloud/webhook/create-brand-acordell",

    ATTRIBUTE_LIST_API_URL:         "https://n8n.srv917960.hstgr.cloud/webhook/get-attributes-acordell",
    ATTRIBUTE_CREATE_API_URL:       "https://n8n.srv917960.hstgr.cloud/webhook/create-attribute-acordell",

    ATTRIBUTE_TERMS_API_URL:        "https://n8n.srv917960.hstgr.cloud/webhook/get-attribute-terms-acordell",
    ATTRIBUTE_TERM_CREATE_API_URL:  "https://n8n.srv917960.hstgr.cloud/webhook/create-attribute-term-acordell",

    CREATE_VARIABLE_PRODUCT_API_URL:"https://n8n.srv917960.hstgr.cloud/webhook/create-variable-product-acordell"
};


/* ==========================================================================
   2. APPLICATION STATE
   ========================================================================== */
const state = {
    categories: [],           // [{id, name, parent}]
    selectedCategories: [],   // [id, id, ...]
    brands: [],               // [{id, name}]
    tags: [],                 // ["tag1", "tag2"]
    availableAttributes: [],  // [{id, name, slug}] from database
    productAttributes: [],    // [{id, name, slug, terms: [{id, name}], selectedTermIds: [], isVariation: true, isVisible: true}]
    variations: [],           // Array of variation objects
    variationIdCounter: 1001, // ID sequence for UI display
    isSubmitting: false
};


/* ==========================================================================
   3. INITIALIZATION
   ========================================================================== */
document.addEventListener('DOMContentLoaded', () => {
    loadCategories();
    loadBrands();
    loadAvailableAttributes();

    document.getElementById('variableProductForm').addEventListener('submit', handleSubmit);

    // Close dropdowns when clicking outside
    document.addEventListener('click', (e) => {
        // Categories dropdown
        const catMs = document.getElementById('categoryMultiSelect');
        if (catMs && !catMs.contains(e.target)) {
            closeCategoryDropdown();
        }

        // Attribute term dropdowns
        const isInsideTermMs = e.target.closest('.multi-select') || e.target.closest('.modal');
        if (!isInsideTermMs) {
            closeAllTermDropdowns();
        }
    });
});


/* ==========================================================================
   4. CATEGORIES
   ========================================================================== */
async function loadCategories() {
    const listEl = document.getElementById('categoryList');
    const loadingEl = document.getElementById('categoryLoading');
    const emptyEl = document.getElementById('categoryEmpty');

    loadingEl.style.display = 'block';
    emptyEl.style.display = 'none';
    listEl.innerHTML = '';

    try {
        const res = await fetch(CONFIG.CATEGORY_LIST_API_URL);
        const data = await res.json();

        let rawCategories = [];
        if (Array.isArray(data)) {
            rawCategories = data;
        } else if (data.success && Array.isArray(data.categories)) {
            rawCategories = data.categories;
        }

        state.categories = rawCategories
            .filter(cat => cat && cat.id)
            .map(cat => ({
                id: cat.id,
                name: decodeHtml(cat.name || ''),
                parent: cat.parent || 0
            }));
    } catch (err) {
        console.error('Failed to load categories:', err);
        state.categories = [];
        showToast('error', 'Failed to load categories');
    }

    loadingEl.style.display = 'none';
    renderCategoryOptions();
    updateParentCategorySelect();
}

function renderCategoryOptions() {
    const listEl = document.getElementById('categoryList');
    const emptyEl = document.getElementById('categoryEmpty');
    listEl.innerHTML = '';

    if (state.categories.length === 0) {
        emptyEl.style.display = 'block';
        return;
    }
    emptyEl.style.display = 'none';

    state.categories.forEach(cat => {
        const opt = document.createElement('label');
        opt.className = 'ms-option';
        const checked = state.selectedCategories.includes(cat.id) ? 'checked' : '';
        opt.innerHTML = `
            <input type="checkbox" value="${cat.id}" ${checked}
                   onchange="toggleCategory(${cat.id})">
            <span>${escapeHtml(cat.name)}</span>
        `;
        listEl.appendChild(opt);
    });
}

function toggleCategory(id) {
    const idx = state.selectedCategories.indexOf(id);
    if (idx > -1) {
        state.selectedCategories.splice(idx, 1);
    } else {
        state.selectedCategories.push(id);
    }
    renderSelectedCategories();
}

function renderSelectedCategories() {
    const trigger = document.getElementById('categoryTrigger');
    const placeholder = document.getElementById('categoryPlaceholder');
    trigger.querySelectorAll('.ms-chip').forEach(c => c.remove());

    if (state.selectedCategories.length === 0) {
        placeholder.style.display = 'inline';
        return;
    }
    placeholder.style.display = 'none';

    state.selectedCategories.forEach(id => {
        const cat = state.categories.find(c => c.id === id);
        if (!cat) return;
        const chip = document.createElement('span');
        chip.className = 'ms-chip';
        chip.innerHTML = `
            ${escapeHtml(cat.name)}
            <span class="remove-chip" onclick="event.stopPropagation(); toggleCategory(${id}); renderCategoryOptions();">&times;</span>
        `;
        trigger.insertBefore(chip, trigger.querySelector('.arrow'));
    });
}

function toggleCategoryDropdown() {
    const dropdown = document.getElementById('categoryDropdown');
    const trigger = document.getElementById('categoryTrigger');
    const isOpen = dropdown.classList.contains('open');
    if (isOpen) {
        closeCategoryDropdown();
    } else {
        dropdown.classList.add('open');
        trigger.classList.add('open');
    }
}
function closeCategoryDropdown() {
    document.getElementById('categoryDropdown').classList.remove('open');
    document.getElementById('categoryTrigger').classList.remove('open');
}

function updateParentCategorySelect() {
    const sel = document.getElementById('parentCategory');
    sel.innerHTML = '<option value="0">None (Top Level)</option>';
    state.categories.forEach(cat => {
        sel.innerHTML += `<option value="${cat.id}">${escapeHtml(cat.name)}</option>`;
    });
}

async function createCategory() {
    const nameInput = document.getElementById('newCategoryName');
    const parentSel = document.getElementById('parentCategory');
    const btn = document.getElementById('createCategoryBtn');
    const name = nameInput.value.trim();

    if (!name) {
        showToast('error', 'Category name is required');
        nameInput.classList.add('input-error');
        return;
    }
    nameInput.classList.remove('input-error');

    btn.disabled = true;
    btn.textContent = 'Creating...';

    try {
        const res = await fetch(CONFIG.CATEGORY_CREATE_API_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: name,
                parent: parseInt(parentSel.value) || 0
            })
        });
        const data = await res.json();
        const catObj = data.category || (data.id ? data : null);

        if (catObj && catObj.id) {
            showToast('success', `Category "${decodeHtml(catObj.name)}" created`);
            await loadCategories();
            if (!state.selectedCategories.includes(catObj.id)) {
                state.selectedCategories.push(catObj.id);
                renderSelectedCategories();
                renderCategoryOptions();
            }
            closeModal('category');
            nameInput.value = '';
        } else {
            showToast('error', data.message || 'Failed to create category');
        }
    } catch (err) {
        console.error('Create category error:', err);
        showToast('error', 'Failed to create category');
    }

    btn.disabled = false;
    btn.textContent = 'Create';
}


/* ==========================================================================
   5. BRANDS
   ========================================================================== */
async function loadBrands() {
    const sel = document.getElementById('brandSelect');
    sel.innerHTML = '<option value="">Loading brands...</option>';

    try {
        const res = await fetch(CONFIG.BRAND_LIST_API_URL);
        const data = await res.json();

        let rawBrands = [];
        if (Array.isArray(data)) {
            rawBrands = data;
        } else if (data.success && Array.isArray(data.brands)) {
            rawBrands = data.brands;
        }

        state.brands = rawBrands
            .filter(b => b && b.id)
            .map(b => ({
                id: b.id,
                name: decodeHtml(b.name || '')
            }));
    } catch (err) {
        console.error('Failed to load brands:', err);
        state.brands = [];
        showToast('error', 'Failed to load brands');
    }

    renderBrandOptions();
}

function renderBrandOptions() {
    const sel = document.getElementById('brandSelect');
    sel.innerHTML = '<option value="">— Select a brand —</option>';
    state.brands.forEach(brand => {
        sel.innerHTML += `<option value="${brand.id}">${escapeHtml(brand.name)}</option>`;
    });
}

async function createBrand() {
    const nameInput = document.getElementById('newBrandName');
    const btn = document.getElementById('createBrandBtn');
    const name = nameInput.value.trim();

    if (!name) {
        showToast('error', 'Brand name is required');
        nameInput.classList.add('input-error');
        return;
    }
    nameInput.classList.remove('input-error');

    btn.disabled = true;
    btn.textContent = 'Creating...';

    try {
        const res = await fetch(CONFIG.BRAND_CREATE_API_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: name })
        });
        const data = await res.json();
        const brandObj = data.brand || (data.id ? data : null);

        if (brandObj && brandObj.id) {
            showToast('success', `Brand "${decodeHtml(brandObj.name)}" created`);
            await loadBrands();
            document.getElementById('brandSelect').value = brandObj.id;
            closeModal('brand');
            nameInput.value = '';
        } else {
            showToast('error', data.message || 'Failed to create brand');
        }
    } catch (err) {
        console.error('Create brand error:', err);
        showToast('error', 'Failed to create brand');
    }

    btn.disabled = false;
    btn.textContent = 'Create';
}


/* ==========================================================================
   6. TAGS
   ========================================================================== */
function handleTagKeydown(e) {
    const input = document.getElementById('tagInput');
    if (e.key === ',' || e.key === 'Enter') {
        e.preventDefault();
        const val = input.value.replace(/,/g, '').trim();
        if (val) addTag(val);
        input.value = '';
    }
    if (e.key === 'Backspace' && input.value === '' && state.tags.length > 0) {
        removeTag(state.tags.length - 1);
    }
}

function handleTagInput(e) {
    const input = document.getElementById('tagInput');
    if (input.value.includes(',')) {
        const parts = input.value.split(',');
        parts.forEach(part => {
            const val = part.trim();
            if (val) addTag(val);
        });
        input.value = '';
    }
}

function handleTagBlur() {
    flushPendingTags();
}

function handleTagPaste(e) {
    e.preventDefault();
    const text = (e.clipboardData || window.clipboardData).getData('text');
    text.split(',').forEach(part => {
        const val = part.trim();
        if (val) addTag(val);
    });
    document.getElementById('tagInput').value = '';
}

function flushPendingTags() {
    const input = document.getElementById('tagInput');
    if (input && input.value.trim()) {
        const parts = input.value.split(',');
        parts.forEach(part => {
            const val = part.trim();
            if (val) addTag(val);
        });
        input.value = '';
    }
}

function addTag(name) {
    const cleanName = name.replace(/,/g, '').trim();
    if (!cleanName) return;

    const exists = state.tags.some(t => t.toLowerCase() === cleanName.toLowerCase());
    if (exists) {
        return;
    }
    state.tags.push(cleanName);
    renderTags();
}

function removeTag(index) {
    state.tags.splice(index, 1);
    renderTags();
}

function renderTags() {
    const wrapper = document.getElementById('tagWrapper');
    const input = document.getElementById('tagInput');
    wrapper.querySelectorAll('.tag-chip').forEach(c => c.remove());

    state.tags.forEach((tag, i) => {
        const chip = document.createElement('span');
        chip.className = 'tag-chip';
        chip.innerHTML = `
            ${escapeHtml(tag)}
            <span class="remove-tag" onclick="removeTag(${i})">&times;</span>
        `;
        wrapper.insertBefore(chip, input);
    });

    input.placeholder = state.tags.length > 0 ? '' : 'Type a tag and press comma or Enter';
}


/* ==========================================================================
   7. IMAGES PREVIEW
   ========================================================================== */
function previewMainImage() {
    const input = document.getElementById('productImage');
    const previewEl = document.getElementById('mainImagePreview');
    previewEl.innerHTML = '';

    if (!input.files || !input.files[0]) return;
    const file = input.files[0];

    if (!isValidImageType(file)) {
        showToast('error', 'Invalid image type. Use JPG, PNG, or WebP.');
        input.value = '';
        return;
    }

    const thumb = createThumbnail(file, () => {
        input.value = '';
        previewEl.innerHTML = '';
    });
    previewEl.appendChild(thumb);
}

function previewGalleryImages() {
    const input = document.getElementById('galleryImages');
    const previewEl = document.getElementById('galleryPreview');
    previewEl.innerHTML = '';

    if (!input.files || input.files.length === 0) return;

    for (const file of input.files) {
        if (!isValidImageType(file)) {
            showToast('error', `"${file.name}" is not a valid image type.`);
            continue;
        }
        const thumb = createThumbnail(file);
        previewEl.appendChild(thumb);
    }
}

function createThumbnail(file, onRemove) {
    const div = document.createElement('div');
    div.className = 'preview-thumb';
    const img = document.createElement('img');
    img.src = URL.createObjectURL(file);
    img.alt = file.name;
    div.appendChild(img);

    if (onRemove) {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'remove-preview';
        btn.textContent = '×';
        btn.onclick = () => { onRemove(); };
        div.appendChild(btn);
    }
    return div;
}

function isValidImageType(file) {
    const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'];
    return validTypes.includes(file.type);
}


/* ==========================================================================
   8. ATTRIBUTES MANAGEMENT
   ========================================================================== */

/** Load all attributes from database via n8n webhook */
async function loadAvailableAttributes() {
    const sel = document.getElementById('availableAttributesSelect');
    sel.innerHTML = '<option value="">Loading attributes from database...</option>';

    try {
        const res = await fetch(CONFIG.ATTRIBUTE_LIST_API_URL);
        const data = await res.json();

        let rawAttributes = [];
        if (Array.isArray(data)) {
            rawAttributes = data;
        } else if (data.success && Array.isArray(data.attributes)) {
            rawAttributes = data.attributes;
        }

        state.availableAttributes = rawAttributes
            .filter(attr => attr && attr.id)
            .map(attr => ({
                id: attr.id,
                name: decodeHtml(attr.name || ''),
                slug: attr.slug || ''
            }));
    } catch (err) {
        console.error('Failed to load attributes:', err);
        state.availableAttributes = [];
        showToast('error', 'Failed to load product attributes');
    }

    renderAvailableAttributesSelect();
}

/** Render attributes in the "+ Add Attribute" dropdown */
function renderAvailableAttributesSelect() {
    const sel = document.getElementById('availableAttributesSelect');
    sel.innerHTML = '<option value="">— Select an attribute to add —</option>';

    // Filter out attributes already added to product
    const available = state.availableAttributes.filter(
        a => !state.productAttributes.some(pa => pa.id === a.id)
    );

    if (available.length === 0) {
        sel.innerHTML = '<option value="">(All available attributes already added)</option>';
        return;
    }

    available.forEach(attr => {
        sel.innerHTML += `<option value="${attr.id}">${escapeHtml(attr.name)}</option>`;
    });
}

/** Add selected attribute to the product configuration */
async function addAttributeToProduct() {
    const sel = document.getElementById('availableAttributesSelect');
    const attrId = parseInt(sel.value);

    if (!attrId) {
        showToast('info', 'Please select an attribute from the dropdown first');
        return;
    }

    const attr = state.availableAttributes.find(a => a.id === attrId);
    if (!attr) return;

    // Add to product attributes state
    const newAttr = {
        id: attr.id,
        name: attr.name,
        slug: attr.slug,
        terms: [],
        selectedTermIds: [],
        isVariation: true,
        isVisible: true,
        isLoadingTerms: true,
        dropdownOpen: true,
        filterText: ''
    };
    state.productAttributes.push(newAttr);

    renderAvailableAttributesSelect();
    renderProductAttributes();

    // Fetch terms for this attribute and keep dropdown open
    await loadTermsForAttribute(attr.id);
}

/** Remove an attribute from the product */
function removeAttributeFromProduct(attrId) {
    const idx = state.productAttributes.findIndex(a => a.id === attrId);
    if (idx > -1) {
        state.productAttributes.splice(idx, 1);
        renderAvailableAttributesSelect();
        renderProductAttributes();
    }
}

/** Fetch terms (values) for a specific attribute from WooCommerce */
async function loadTermsForAttribute(attrId) {
    const attr = state.productAttributes.find(a => a.id === attrId);
    if (!attr) return;

    attr.isLoadingTerms = true;
    attr.dropdownOpen = true;
    renderProductAttributes();

    try {
        const res = await fetch(`${CONFIG.ATTRIBUTE_TERMS_API_URL}?attribute_id=${attrId}`);
        const data = await res.json();

        let terms = [];
        if (Array.isArray(data)) {
            terms = data;
        } else if (data.success && Array.isArray(data.terms)) {
            terms = data.terms;
        }

        attr.terms = terms.map(t => ({
            id: t.id,
            name: decodeHtml(t.name || ''),
            slug: t.slug || '',
            count: t.count !== undefined ? t.count : 0
        }));
    } catch (err) {
        console.error(`Failed to load terms for attribute ${attrId}:`, err);
        showToast('error', `Failed to load values for "${attr.name}"`);
        attr.terms = [];
    }

    attr.isLoadingTerms = false;
    attr.dropdownOpen = true;
    renderProductAttributes();
}

/** Render all added attribute cards with Multi-Select Terms Dropdowns */
function renderProductAttributes() {
    const container = document.getElementById('attributesList');
    container.innerHTML = '';

    if (state.productAttributes.length === 0) {
        container.innerHTML = `
            <div style="text-align: center; padding: 20px; color: var(--text-muted); font-size: 13.5px; border: 1.5px dashed var(--border); border-radius: var(--radius);">
                No attributes added to this product yet. Select an attribute above and click <strong>"+ Add Attribute"</strong>.
            </div>
        `;
        return;
    }

    state.productAttributes.forEach(attr => {
        const card = document.createElement('div');
        card.className = 'attribute-card';

        // Build selected chips inside the dropdown trigger
        const selectedTerms = attr.terms.filter(t => attr.selectedTermIds.includes(t.id));
        const chipsHtml = selectedTerms.map(t => `
            <span class="ms-chip">
                ${escapeHtml(t.name)}
                <span class="remove-chip" onclick="event.stopPropagation(); removeAttributeTerm(${attr.id}, ${t.id});">&times;</span>
            </span>
        `).join('');

        // Build filtered options list
        const filter = (attr.filterText || '').toLowerCase();
        const filteredTerms = attr.terms.filter(t => t.name.toLowerCase().includes(filter));

        let optionsHtml = '';
        if (attr.isLoadingTerms) {
            optionsHtml = `<div class="ms-loading" style="padding: 20px; text-align: center;">Loading ${escapeHtml(attr.name)} values<span class="loading-dots"></span></div>`;
        } else if (attr.terms.length === 0) {
            optionsHtml = `
                <div class="ms-empty" style="padding: 20px; text-align: center;">
                    No values found for this attribute.<br>
                    <button type="button" class="btn-xs" style="margin-top: 10px; color: var(--primary); font-weight: 600;"
                            onclick="openAddTermModal(${attr.id}, '${escapeHtml(attr.name)}')">
                        + Create First Value
                    </button>
                </div>
            `;
        } else if (filteredTerms.length === 0) {
            optionsHtml = `<div class="ms-empty" style="padding: 16px; text-align: center;">No matching values found</div>`;
        } else {
            optionsHtml = filteredTerms.map(term => {
                const isSelected = attr.selectedTermIds.includes(term.id);
                return `
                    <label class="ms-option" onclick="event.stopPropagation()">
                        <div class="ms-option-left">
                            <input type="checkbox" value="${term.id}" ${isSelected ? 'checked' : ''}
                                   onchange="toggleAttributeTerm(${attr.id}, ${term.id})">
                            <span style="font-weight: ${isSelected ? '600' : '500'};">${escapeHtml(term.name)}</span>
                        </div>
                        ${term.count ? `<span class="ms-option-count">${term.count} products</span>` : ''}
                    </label>
                `;
            }).join('');
        }

        card.innerHTML = `
            <div class="attribute-card-header">
                <div class="attribute-card-title">
                    <span>${escapeHtml(attr.name)}</span>
                    ${attr.slug ? `<span class="attribute-card-slug">${escapeHtml(attr.slug)}</span>` : ''}
                </div>
                <div class="attribute-card-actions">
                    <button type="button" class="btn-link-danger" onclick="removeAttributeFromProduct(${attr.id})">Remove</button>
                </div>
            </div>
            <div class="attribute-card-body">

                <!-- Terms Multi-Select Dropdown -->
                <div class="form-group" style="margin-bottom: 14px; position: relative;">
                    <label style="margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
                        <span>Select ${escapeHtml(attr.name)} Terms / Values <span class="required-star">*</span></span>
                        <span style="font-size: 12px; color: var(--text-muted); font-weight: 500;">
                            ${selectedTerms.length} of ${attr.terms.length} selected
                        </span>
                    </label>

                    <div class="multi-select" id="termMultiSelect-${attr.id}">
                        <div class="multi-select-trigger ${attr.dropdownOpen ? 'open' : ''}"
                             id="termTrigger-${attr.id}"
                             onclick="toggleTermDropdown(${attr.id})">
                            ${selectedTerms.length === 0 ? `<span class="placeholder">Click to select ${escapeHtml(attr.name)} values...</span>` : chipsHtml}
                            <span class="arrow">▾</span>
                        </div>

                        <div class="multi-select-dropdown ${attr.dropdownOpen ? 'open' : ''}"
                             id="termDropdown-${attr.id}"
                             onclick="event.stopPropagation()">
                            
                            <!-- Search & Action Toolbar -->
                            <div class="ms-toolbar">
                                <input type="text" class="ms-search-input" placeholder="Search ${escapeHtml(attr.name)} values..."
                                       value="${escapeHtml(attr.filterText || '')}"
                                       oninput="filterTermOptions(${attr.id}, this.value)">
                                <div class="ms-actions">
                                    <button type="button" class="btn-xs" onclick="selectAllAttributeTerms(${attr.id})">Select all</button>
                                    <button type="button" class="btn-xs" onclick="selectNoneAttributeTerms(${attr.id})">Select none</button>
                                    <button type="button" class="btn-xs" onclick="openAddTermModal(${attr.id}, '${escapeHtml(attr.name)}')" style="color: var(--primary); font-weight: 600;">+ Add New Value</button>
                                </div>
                            </div>

                            <!-- Options Checkbox List -->
                            <div class="ms-options-list">
                                ${optionsHtml}
                            </div>
                        </div>
                    </div>
                </div>

                <div class="attribute-options-row">
                    <label class="checkbox-inline">
                        <input type="checkbox" ${attr.isVisible ? 'checked' : ''} onchange="toggleAttributeOption(${attr.id}, 'isVisible', this.checked)">
                        <span>Visible on the product page</span>
                    </label>
                    <label class="checkbox-inline">
                        <input type="checkbox" ${attr.isVariation ? 'checked' : ''} onchange="toggleAttributeOption(${attr.id}, 'isVariation', this.checked)">
                        <span>Used for variations</span>
                    </label>
                </div>
            </div>
        `;
        container.appendChild(card);
    });
}

function toggleTermDropdown(attrId) {
    const attr = state.productAttributes.find(a => a.id === attrId);
    if (!attr) return;

    const willOpen = !attr.dropdownOpen;
    // Close other term dropdowns
    state.productAttributes.forEach(a => { if (a.id !== attrId) a.dropdownOpen = false; });
    attr.dropdownOpen = willOpen;
    renderProductAttributes();
}

function closeAllTermDropdowns() {
    let changed = false;
    state.productAttributes.forEach(a => {
        if (a.dropdownOpen) {
            a.dropdownOpen = false;
            changed = true;
        }
    });
    if (changed) renderProductAttributes();
}

function filterTermOptions(attrId, text) {
    const attr = state.productAttributes.find(a => a.id === attrId);
    if (attr) {
        attr.filterText = text;
        renderProductAttributes();
    }
}

function toggleAttributeTerm(attrId, termId) {
    const attr = state.productAttributes.find(a => a.id === attrId);
    if (!attr) return;

    const idx = attr.selectedTermIds.indexOf(termId);
    if (idx > -1) {
        attr.selectedTermIds.splice(idx, 1);
    } else {
        attr.selectedTermIds.push(termId);
    }
    renderProductAttributes();
}

function removeAttributeTerm(attrId, termId) {
    const attr = state.productAttributes.find(a => a.id === attrId);
    if (!attr) return;

    const idx = attr.selectedTermIds.indexOf(termId);
    if (idx > -1) {
        attr.selectedTermIds.splice(idx, 1);
        renderProductAttributes();
    }
}

function selectAllAttributeTerms(attrId) {
    const attr = state.productAttributes.find(a => a.id === attrId);
    if (!attr) return;
    attr.selectedTermIds = attr.terms.map(t => t.id);
    renderProductAttributes();
}

function selectNoneAttributeTerms(attrId) {
    const attr = state.productAttributes.find(a => a.id === attrId);
    if (!attr) return;
    attr.selectedTermIds = [];
    renderProductAttributes();
}

function toggleAttributeOption(attrId, prop, value) {
    const attr = state.productAttributes.find(a => a.id === attrId);
    if (attr) {
        attr[prop] = Boolean(value);
    }
}

/** Modal to add a new global attribute */
async function createGlobalAttribute() {
    const nameInput = document.getElementById('newAttributeName');
    const slugInput = document.getElementById('newAttributeSlug');
    const btn = document.getElementById('createAttributeBtn');
    const name = nameInput.value.trim();
    const slug = slugInput.value.trim();

    if (!name) {
        showToast('error', 'Attribute name is required');
        nameInput.classList.add('input-error');
        return;
    }
    nameInput.classList.remove('input-error');

    btn.disabled = true;
    btn.textContent = 'Creating...';

    try {
        const res = await fetch(CONFIG.ATTRIBUTE_CREATE_API_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: name,
                slug: slug || undefined,
                type: 'select',
                order_by: 'menu_order'
            })
        });
        const data = await res.json();
        const attrObj = data.attribute || (data.id ? data : null);

        if (attrObj && attrObj.id) {
            showToast('success', `Attribute "${decodeHtml(attrObj.name)}" created`);
            await loadAvailableAttributes();
            closeModal('attribute');
            nameInput.value = '';
            slugInput.value = '';

            // Auto-select in dropdown
            document.getElementById('availableAttributesSelect').value = attrObj.id;
        } else {
            showToast('error', data.message || 'Failed to create attribute');
        }
    } catch (err) {
        console.error('Create attribute error:', err);
        showToast('error', 'Failed to create attribute');
    }

    btn.disabled = false;
    btn.textContent = 'Create';
}

/** Modal to add a term/value to a specific attribute */
function openAddTermModal(attrId, attrName) {
    document.getElementById('newTermAttributeId').value = attrId;
    document.getElementById('termModalTitle').textContent = `Add Value to "${attrName}"`;
    document.getElementById('newTermName').value = '';
    document.getElementById('newTermSlug').value = '';
    document.getElementById('termModal').classList.add('open');
    setTimeout(() => document.getElementById('newTermName').focus(), 100);
}

async function createAttributeTerm() {
    const attrId = parseInt(document.getElementById('newTermAttributeId').value);
    const nameInput = document.getElementById('newTermName');
    const slugInput = document.getElementById('newTermSlug');
    const btn = document.getElementById('createTermBtn');
    const name = nameInput.value.trim();
    const slug = slugInput.value.trim();

    if (!name) {
        showToast('error', 'Term value name is required');
        nameInput.classList.add('input-error');
        return;
    }
    nameInput.classList.remove('input-error');

    btn.disabled = true;
    btn.textContent = 'Adding...';

    try {
        const res = await fetch(CONFIG.ATTRIBUTE_TERM_CREATE_API_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                attribute_id: attrId,
                name: name,
                slug: slug || undefined
            })
        });
        const data = await res.json();
        const termObj = data.term || (data.id ? data : null);

        if (termObj && termObj.id) {
            showToast('success', `Value "${decodeHtml(termObj.name)}" added`);
            closeModal('term');
            nameInput.value = '';
            slugInput.value = '';

            // Reload terms for this attribute and auto-select new term
            await loadTermsForAttribute(attrId);
            const attr = state.productAttributes.find(a => a.id === attrId);
            if (attr && !attr.selectedTermIds.includes(termObj.id)) {
                attr.selectedTermIds.push(termObj.id);
                renderProductAttributes();
            }
        } else {
            showToast('error', data.message || 'Failed to add attribute value');
        }
    } catch (err) {
        console.error('Create term error:', err);
        showToast('error', 'Failed to add attribute value');
    }

    btn.disabled = false;
    btn.textContent = 'Add Value';
}


/* ==========================================================================
   9. VARIATIONS GENERATOR & ACCORDION MANAGEMENT
   ========================================================================== */

/**
 * Generate all variations from Cartesian product of selected terms
 * of all attributes marked as isVariation = true
 */
function generateAllVariations() {
    const variationAttrs = state.productAttributes.filter(
        a => a.isVariation && a.selectedTermIds.length > 0
    );

    if (variationAttrs.length === 0) {
        showToast('error', 'Please select at least one attribute value marked for variations.');
        return;
    }

    // Build array of term arrays: [[{id, name, option}], [{id, name, option}]]
    const factorArrays = variationAttrs.map(attr => {
        return attr.terms
            .filter(t => attr.selectedTermIds.includes(t.id))
            .map(t => ({
                id: attr.id,
                name: attr.name,
                option: t.name
            }));
    });

    // Cartesian product algorithm
    const combos = factorArrays.reduce((acc, curr) => {
        const res = [];
        acc.forEach(a => {
            curr.forEach(b => {
                res.push([...a, b]);
            });
        });
        return res;
    }, [[]]);

    if (combos.length === 0 || combos[0].length === 0) {
        showToast('error', 'No combinations could be generated.');
        return;
    }

    // Convert combos into variation objects
    state.variations = combos.map(combo => {
        return createDefaultVariationObject(combo);
    });

    showToast('success', `Generated ${state.variations.length} variations!`);
    renderVariations();
}

/** Add a manual variation */
function addCustomVariation() {
    const variationAttrs = state.productAttributes.filter(a => a.isVariation);
    const defaultCombo = variationAttrs.map(attr => {
        const firstTerm = attr.terms.find(t => attr.selectedTermIds.includes(t.id)) || attr.terms[0];
        return {
            id: attr.id,
            name: attr.name,
            option: firstTerm ? firstTerm.name : ''
        };
    });

    const newVar = createDefaultVariationObject(defaultCombo);
    state.variations.unshift(newVar); // Add to top
    renderVariations();
    showToast('info', 'Added new variation');
}

/** Helper to construct a default variation object */
function createDefaultVariationObject(attributesCombo) {
    const id = state.variationIdCounter++;
    return {
        id: id,
        attributes: attributesCombo, // [{id, name, option}]
        sku: '',
        gtin: '',
        enabled: true,
        downloadable: false,
        virtual: false,
        manage_stock: false,
        regular_price: '',
        sale_price: '',
        stock_status: 'instock',
        stock_quantity: '',
        weight: '',
        dimensions: { length: '', width: '', height: '' },
        shipping_class: 'same_as_parent',
        description: '',
        collapsed: false,
        imageFile: null,
        imagePreviewUrl: ''
    };
}

/** Render all variation cards (matching WooCommerce screenshot) */
function renderVariations() {
    const container = document.getElementById('variationsContainer');
    const countBadge = document.getElementById('variationCountBadge');
    countBadge.textContent = `${state.variations.length} Variation${state.variations.length === 1 ? '' : 's'}`;

    if (state.variations.length === 0) {
        container.innerHTML = `
            <div class="empty-variations-placeholder" id="emptyVariationsPlaceholder">
                <div class="empty-variations-icon">📦</div>
                <h4>No variations generated yet</h4>
                <p style="font-size: 13px; margin-top: 4px;">Select attributes and terms above, then click <strong>"Generate All Variations"</strong>.</p>
            </div>
        `;
        return;
    }

    container.innerHTML = '';

    state.variations.forEach((v, index) => {
        const card = document.createElement('div');
        card.className = `variation-card ${v.collapsed ? 'collapsed' : ''}`;
        card.id = `variation-card-${v.id}`;

        // Attribute selectors for this variation (e.g. #9329 [ 100 ML v ])
        const attrSelectorsHtml = v.attributes.map(attr => {
            const productAttr = state.productAttributes.find(pa => pa.id === attr.id);
            const availableOptions = productAttr ? productAttr.terms : [];

            return `
                <div class="variation-attribute-selector">
                    <select class="variation-attribute-select"
                            onchange="updateVariationAttribute(${v.id}, ${attr.id}, this.value)">
                        ${availableOptions.map(opt => `
                            <option value="${escapeHtml(opt.name)}" ${opt.name === attr.option ? 'selected' : ''}>
                                ${escapeHtml(opt.name)}
                            </option>
                        `).join('')}
                    </select>
                </div>
            `;
        }).join('');

        card.innerHTML = `
            <!-- ===== HEADER ===== -->
            <div class="variation-card-header" onclick="toggleVariationCollapse(${v.id})">
                <div class="variation-header-left" onclick="event.stopPropagation()">
                    <span class="variation-id-badge">#${v.id}</span>
                    ${attrSelectorsHtml}
                </div>
                <div class="variation-header-right" onclick="event.stopPropagation()">
                    <button type="button" class="btn-variation-link btn-variation-remove" onclick="removeVariation(${v.id})">Remove</button>
                    <button type="button" class="btn-variation-link btn-variation-edit" onclick="toggleVariationCollapse(${v.id})">
                        ${v.collapsed ? 'Edit' : 'Close'}
                    </button>
                </div>
            </div>

            <!-- ===== BODY ===== -->
            <div class="variation-card-body">

                <!-- Top Row: Image (left) + SKU/GTIN (right) -->
                <div class="variation-top-row">
                    <!-- Image Upload box -->
                    <div class="variation-image-box" onclick="triggerVariationImageUpload(${v.id})">
                        <input type="file" id="var-img-input-${v.id}" accept=".jpg,.jpeg,.png,.webp"
                               onchange="handleVariationImageUpload(${v.id}, event)" onclick="event.stopPropagation()">
                        ${v.imagePreviewUrl ? `
                            <img src="${v.imagePreviewUrl}" class="variation-img-preview" alt="Variation image">
                            <button type="button" class="remove-var-img" onclick="event.stopPropagation(); removeVariationImage(${v.id});">&times;</button>
                        ` : `
                            <svg class="variation-img-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
                                <rect x="3" y="3" width="18" height="18" rx="3" ry="3"></rect>
                                <circle cx="8.5" cy="8.5" r="1.5"></circle>
                                <polyline points="21 15 16 10 5 21"></polyline>
                            </svg>
                        `}
                    </div>

                    <!-- SKU and GTIN fields -->
                    <div class="variation-meta-fields">
                        <div class="form-group" style="margin-bottom: 0;">
                            <label>SKU <span class="help-tip" data-tip="Stock Keeping Unit for this specific variation">?</span></label>
                            <input type="text" placeholder="e.g. VAR-SKU-${v.id}" value="${escapeHtml(v.sku || '')}"
                                   oninput="updateVariationField(${v.id}, 'sku', this.value)">
                        </div>
                        <div class="form-group" style="margin-bottom: 0;">
                            <label>GTIN, UPC, EAN, or ISBN <span class="help-tip" data-tip="Unique barcode or identifier">?</span></label>
                            <input type="text" placeholder="e.g. 012345678905" value="${escapeHtml(v.gtin || '')}"
                                   oninput="updateVariationField(${v.id}, 'gtin', this.value)">
                        </div>
                    </div>
                </div>

                <!-- Flags Row (Checkboxes) -->
                <div class="variation-flags-row">
                    <label class="checkbox-inline">
                        <input type="checkbox" ${v.enabled ? 'checked' : ''}
                               onchange="updateVariationField(${v.id}, 'enabled', this.checked)">
                        <span>Enabled</span>
                    </label>
                    <label class="checkbox-inline">
                        <input type="checkbox" ${v.downloadable ? 'checked' : ''}
                               onchange="updateVariationField(${v.id}, 'downloadable', this.checked)">
                        <span>Downloadable</span>
                    </label>
                    <label class="checkbox-inline">
                        <input type="checkbox" ${v.virtual ? 'checked' : ''}
                               onchange="updateVariationField(${v.id}, 'virtual', this.checked)">
                        <span>Virtual</span>
                    </label>
                    <label class="checkbox-inline">
                        <input type="checkbox" ${v.manage_stock ? 'checked' : ''}
                               onchange="updateVariationField(${v.id}, 'manage_stock', this.checked); renderVariations();">
                        <span>Manage stock?</span>
                    </label>
                </div>

                <!-- Pricing Row -->
                <div class="grid-2" style="margin-bottom: 16px;">
                    <div class="form-group" style="margin-bottom: 0;">
                        <label>Regular price (₹) <span class="required-star">*</span></label>
                        <input type="number" placeholder="Variation price (required)" min="0" step="0.01"
                               value="${v.regular_price || ''}"
                               oninput="updateVariationField(${v.id}, 'regular_price', this.value)">
                    </div>
                    <div class="form-group" style="margin-bottom: 0;">
                        <label>Sale price (₹) <span class="optional"><a href="#" style="color: #0284c7; text-decoration:none; margin-left: 4px;" onclick="event.preventDefault()">Schedule</a></span></label>
                        <input type="number" placeholder="0.00" min="0" step="0.01"
                               value="${v.sale_price || ''}"
                               oninput="updateVariationField(${v.id}, 'sale_price', this.value)">
                    </div>
                </div>

                <!-- Stock Row -->
                <div class="form-group" style="margin-bottom: 16px;">
                    <label>Stock status <span class="help-tip" data-tip="Controls whether this variation is in stock">?</span></label>
                    <select onchange="updateVariationField(${v.id}, 'stock_status', this.value)">
                        <option value="instock" ${v.stock_status === 'instock' ? 'selected' : ''}>In stock</option>
                        <option value="outofstock" ${v.stock_status === 'outofstock' ? 'selected' : ''}>Out of stock</option>
                        <option value="onbackorder" ${v.stock_status === 'onbackorder' ? 'selected' : ''}>On backorder</option>
                    </select>
                </div>

                ${v.manage_stock ? `
                    <div class="form-group var-quantity-box" style="margin-bottom: 16px;">
                        <label>Stock quantity <span class="required-star">*</span></label>
                        <input type="number" placeholder="Enter stock quantity" min="0" step="1"
                               value="${v.stock_quantity || ''}"
                               oninput="updateVariationField(${v.id}, 'stock_quantity', this.value)">
                    </div>
                ` : ''}

                <!-- Weight & Dimensions Row -->
                <div class="grid-2" style="margin-bottom: 16px;">
                    <div class="form-group" style="margin-bottom: 0;">
                        <label>Weight (kg) <span class="help-tip" data-tip="Weight in decimal format">?</span></label>
                        <input type="text" placeholder="e.g. 0.5" value="${escapeHtml(v.weight || '')}"
                               oninput="updateVariationField(${v.id}, 'weight', this.value)">
                    </div>
                    <div class="form-group" style="margin-bottom: 0;">
                        <label>Dimensions (L×W×H) (cm) <span class="help-tip" data-tip="Length, width, and height">?</span></label>
                        <div class="dimensions-wrap">
                            <input type="text" placeholder="Length" value="${escapeHtml(v.dimensions?.length || '')}"
                                   oninput="updateVariationDimension(${v.id}, 'length', this.value)">
                            <input type="text" placeholder="Width" value="${escapeHtml(v.dimensions?.width || '')}"
                                   oninput="updateVariationDimension(${v.id}, 'width', this.value)">
                            <input type="text" placeholder="Height" value="${escapeHtml(v.dimensions?.height || '')}"
                                   oninput="updateVariationDimension(${v.id}, 'height', this.value)">
                        </div>
                    </div>
                </div>

                <!-- Shipping Class -->
                <div class="form-group" style="margin-bottom: 16px;">
                    <label>Shipping class</label>
                    <select onchange="updateVariationField(${v.id}, 'shipping_class', this.value)">
                        <option value="same_as_parent" selected>Same as parent</option>
                    </select>
                </div>

                <!-- Description -->
                <div class="form-group" style="margin-bottom: 0;">
                    <label>Description <span class="help-tip" data-tip="Shown on product page when this variation is selected">?</span></label>
                    <textarea placeholder="Enter variation description..." oninput="updateVariationField(${v.id}, 'description', this.value)">${escapeHtml(v.description || '')}</textarea>
                </div>

            </div>
        `;

        container.appendChild(card);
    });
}

function toggleVariationCollapse(varId) {
    const v = state.variations.find(item => item.id === varId);
    if (v) {
        v.collapsed = !v.collapsed;
        const card = document.getElementById(`variation-card-${varId}`);
        if (card) {
            card.classList.toggle('collapsed', v.collapsed);
            const editBtn = card.querySelector('.btn-variation-edit');
            if (editBtn) editBtn.textContent = v.collapsed ? 'Edit' : 'Close';
        }
    }
}

function toggleAllVariationsCollapse(collapsed) {
    state.variations.forEach(v => v.collapsed = collapsed);
    renderVariations();
}

function removeVariation(varId) {
    const idx = state.variations.findIndex(v => v.id === varId);
    if (idx > -1) {
        state.variations.splice(idx, 1);
        renderVariations();
    }
}

function removeAllVariations() {
    if (state.variations.length === 0) return;
    if (confirm('Are you sure you want to remove all variations?')) {
        state.variations = [];
        renderVariations();
    }
}

function updateVariationField(varId, field, value) {
    const v = state.variations.find(item => item.id === varId);
    if (v) {
        v[field] = value;
    }
}

function updateVariationDimension(varId, dim, value) {
    const v = state.variations.find(item => item.id === varId);
    if (v) {
        v.dimensions = v.dimensions || {};
        v.dimensions[dim] = value;
    }
}

function updateVariationAttribute(varId, attrId, optionValue) {
    const v = state.variations.find(item => item.id === varId);
    if (v) {
        const targetAttr = v.attributes.find(a => a.id === attrId);
        if (targetAttr) {
            targetAttr.option = optionValue;
        }
    }
}

function triggerVariationImageUpload(varId) {
    const input = document.getElementById(`var-img-input-${varId}`);
    if (input) input.click();
}

function handleVariationImageUpload(varId, event) {
    const file = event.target.files[0];
    if (!file) return;

    if (!isValidImageType(file)) {
        showToast('error', 'Invalid image file. Use JPG, PNG, or WebP.');
        return;
    }

    const v = state.variations.find(item => item.id === varId);
    if (v) {
        v.imageFile = file;
        v.imagePreviewUrl = URL.createObjectURL(file);
        renderVariations();
    }
}

function removeVariationImage(varId) {
    const v = state.variations.find(item => item.id === varId);
    if (v) {
        v.imageFile = null;
        v.imagePreviewUrl = '';
        renderVariations();
    }
}

function applyBulkPrice() {
    const regPrice = document.getElementById('bulkRegularPrice').value;
    const salePrice = document.getElementById('bulkSalePrice').value;

    if (!regPrice || parseFloat(regPrice) < 0) {
        showToast('error', 'Please enter a valid regular price.');
        return;
    }

    state.variations.forEach(v => {
        v.regular_price = regPrice;
        if (salePrice) v.sale_price = salePrice;
    });

    closeModal('bulkPrice');
    renderVariations();
    showToast('success', `Applied prices to all ${state.variations.length} variations`);
}


/* ==========================================================================
   10. FORM VALIDATION & SUBMISSION
   ========================================================================== */

function validateForm() {
    const errors = [];

    // Product name
    const name = document.getElementById('productName').value.trim();
    if (!name) errors.push('Product name is required.');

    // Description
    const desc = document.getElementById('productDescription').value.trim();
    if (!desc) errors.push('Description is required.');

    // Main image
    const imgInput = document.getElementById('productImage');
    if (!imgInput.files || !imgInput.files[0]) {
        errors.push('Main product image is required.');
    } else if (!isValidImageType(imgInput.files[0])) {
        errors.push('Product image must be JPG, PNG, or WebP.');
    }

    // Attributes check
    if (state.productAttributes.length === 0) {
        errors.push('Please add at least one product attribute.');
    }

    // Variations check
    if (state.variations.length === 0) {
        errors.push('Please generate at least one variation for the product.');
    } else {
        // Validate each variation has regular_price
        for (let i = 0; i < state.variations.length; i++) {
            const v = state.variations[i];
            if (!v.regular_price || parseFloat(v.regular_price) < 0) {
                errors.push(`Variation #${v.id}: Regular price is required.`);
            }
            if (v.manage_stock && (!v.stock_quantity || parseInt(v.stock_quantity) < 0)) {
                errors.push(`Variation #${v.id}: Stock quantity is required when managing stock.`);
            }
        }
    }

    return { valid: errors.length === 0, errors };
}

async function handleSubmit(e) {
    e.preventDefault();
    if (state.isSubmitting) return;

    // Flush any pending tag typed in the tag input field
    flushPendingTags();

    const { valid, errors } = validateForm();
    if (!valid) {
        errors.forEach(err => showToast('error', err));
        return;
    }

    await submitVariableProduct();
}

async function submitVariableProduct() {
    const btn = document.getElementById('submitBtn');
    state.isSubmitting = true;
    btn.disabled = true;
    btn.classList.add('loading');

    // Make sure pending tags are saved
    flushPendingTags();

    const formData = new FormData();

    // 1. General product text fields
    formData.append('name', document.getElementById('productName').value.trim());
    formData.append('description', document.getElementById('productDescription').value.trim());

    // 2. Categories & Brand & Tags
    formData.append('categories', JSON.stringify(state.selectedCategories));
    const brandId = document.getElementById('brandSelect').value;
    formData.append('brand', brandId || '');
    formData.append('tags', JSON.stringify(state.tags));

    // 3. Parent SKU
    const parentSku = document.getElementById('parentSku').value.trim();
    if (parentSku) {
        formData.append('sku', parentSku);
    }

    // 4. Product attributes payload
    const attributesPayload = state.productAttributes.map(attr => {
        const selectedTerms = attr.terms.filter(t => attr.selectedTermIds.includes(t.id));
        return {
            id: attr.id,
            name: attr.name,
            options: selectedTerms.map(t => t.name),
            variation: attr.isVariation,
            visible: attr.isVisible
        };
    });
    formData.append('attributes', JSON.stringify(attributesPayload));

    // 5. Variations payload
    const variationsPayload = state.variations.map(v => ({
        attributes: v.attributes.map(a => ({
            id: a.id,
            name: a.name,
            option: a.option
        })),
        regular_price: v.regular_price,
        sale_price: v.sale_price || '',
        sku: v.sku || '',
        gtin: v.gtin || '',
        stock_status: v.stock_status,
        manage_stock: v.manage_stock,
        stock_quantity: v.manage_stock ? v.stock_quantity : null,
        weight: v.weight || '',
        dimensions: v.dimensions || {},
        description: v.description || '',
        virtual: v.virtual,
        downloadable: v.downloadable
    }));
    formData.append('variations', JSON.stringify(variationsPayload));

    // 6. Main image
    const imgInput = document.getElementById('productImage');
    formData.append('product_image', imgInput.files[0]);

    // 7. Gallery images
    const galleryInput = document.getElementById('galleryImages');
    if (galleryInput.files && galleryInput.files.length > 0) {
        for (let i = 0; i < galleryInput.files.length; i++) {
            formData.append(`gallery_image_${i}`, galleryInput.files[i]);
        }
        formData.append('gallery_count', galleryInput.files.length);
    } else {
        formData.append('gallery_count', '0');
    }

    // 8. Individual Variation Images
    state.variations.forEach((v, idx) => {
        if (v.imageFile) {
            formData.append(`variation_image_${idx}`, v.imageFile);
        }
    });

    try {
        const res = await fetch(CONFIG.CREATE_VARIABLE_PRODUCT_API_URL, {
            method: 'POST',
            body: formData
        });

        const data = await res.json();

        if (data.success || data.product?.id || data.id) {
            const prodName = data.product?.name || data.name || 'Variable Product';
            const varCount = data.product?.variations_created || state.variations.length;
            showToast('success', `Product "${decodeHtml(prodName)}" created with ${varCount} variations!`);
            resetForm();
        } else {
            showToast('error', data.message || 'Failed to create variable product');
        }
    } catch (err) {
        console.error('Submit error:', err);
        showToast('error', 'Failed to create variable product. Please check connection and webhook URL.');
    }

    state.isSubmitting = false;
    btn.disabled = false;
    btn.classList.remove('loading');
}

function resetForm() {
    document.getElementById('variableProductForm').reset();
    document.getElementById('mainImagePreview').innerHTML = '';
    document.getElementById('galleryPreview').innerHTML = '';

    state.selectedCategories = [];
    state.tags = [];
    state.productAttributes = [];
    state.variations = [];

    renderSelectedCategories();
    renderCategoryOptions();
    renderTags();
    renderAvailableAttributesSelect();
    renderProductAttributes();
    renderVariations();

    document.getElementById('brandSelect').value = '';
}


/* ==========================================================================
   11. MODAL MANAGEMENT
   ========================================================================== */
function openModal(type) {
    if (type === 'category') {
        updateParentCategorySelect();
        document.getElementById('categoryModal').classList.add('open');
        document.getElementById('newCategoryName').value = '';
        setTimeout(() => document.getElementById('newCategoryName').focus(), 100);
    } else if (type === 'brand') {
        document.getElementById('brandModal').classList.add('open');
        document.getElementById('newBrandName').value = '';
        setTimeout(() => document.getElementById('newBrandName').focus(), 100);
    } else if (type === 'attribute') {
        document.getElementById('attributeModal').classList.add('open');
        document.getElementById('newAttributeName').value = '';
        document.getElementById('newAttributeSlug').value = '';
        setTimeout(() => document.getElementById('newAttributeName').focus(), 100);
    } else if (type === 'bulkPrice') {
        document.getElementById('bulkPriceModal').classList.add('open');
        document.getElementById('bulkRegularPrice').value = '';
        document.getElementById('bulkSalePrice').value = '';
        setTimeout(() => document.getElementById('bulkRegularPrice').focus(), 100);
    }
}

function closeModal(type) {
    const modalMap = {
        category: 'categoryModal',
        brand: 'brandModal',
        attribute: 'attributeModal',
        term: 'termModal',
        bulkPrice: 'bulkPriceModal'
    };

    const modalId = modalMap[type];
    if (modalId) {
        document.getElementById(modalId).classList.remove('open');
    }
}

// Close modals on overlay click
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal-overlay')) {
        e.target.classList.remove('open');
    }
});

// Close modals on Escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        document.querySelectorAll('.modal-overlay.open').forEach(m => m.classList.remove('open'));
    }
});


/* ==========================================================================
   12. TOAST NOTIFICATIONS
   ========================================================================== */
function showToast(type, message) {
    const container = document.getElementById('toastContainer');
    const icons = { success: '✓', error: '✕', info: 'ℹ' };
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <span class="toast-icon" style="font-weight:700; font-size:16px;">${icons[type] || '•'}</span>
        <span>${escapeHtml(message)}</span>
    `;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(30px)';
        setTimeout(() => toast.remove(), 300);
    }, 4500);
}


/* ==========================================================================
   13. UTILITY FUNCTIONS
   ========================================================================== */
function escapeHtml(str) {
    if (!str && str !== 0) return '';
    const div = document.createElement('div');
    div.textContent = str.toString();
    return div.innerHTML;
}

function decodeHtml(str) {
    if (!str) return '';
    const textarea = document.createElement('textarea');
    textarea.innerHTML = str;
    return textarea.value;
}
