# React Native WooCommerce Product Creation Suite — AI Agent Master Prompt

Use this prompt to guide an AI coding agent or developers in implementing the complete WooCommerce Simple and Variable Product creation flow in a React Native app.

---

## 🎯 Role & Objective

You are an expert React Native & TypeScript Mobile Engineer. Your task is to build a complete, production-ready **WooCommerce Product Creation Suite** in this React Native application. 

The suite must support creating both **Simple Products** and **Variable Products** with full WooCommerce feature parity, including parent and child variation image uploads, category hierarchy selection & creation, brand assignment, tag chip management, dynamic global attributes & terms multi-selection, Cartesian variation generation, and individual variation management.

---

## 1. Backend Webhook APIs & Architecture

All requests communicate with the following hosted n8n webhooks:

### API Endpoints Configuration

```typescript
export const API_CONFIG = {
  // Categories
  GET_CATEGORIES: "https://n8n.srv917960.hstgr.cloud/webhook/get-categories-acordell",
  CREATE_CATEGORY: "https://n8n.srv917960.hstgr.cloud/webhook/create-category-acordell",

  // Brands
  GET_BRANDS: "https://n8n.srv917960.hstgr.cloud/webhook/get-brands-acordell",
  CREATE_BRAND: "https://n8n.srv917960.hstgr.cloud/webhook/create-brand-acordell",

  // Attributes & Terms
  GET_ATTRIBUTES: "https://n8n.srv917960.hstgr.cloud/webhook/get-attributes-acordell",
  CREATE_ATTRIBUTE: "https://n8n.srv917960.hstgr.cloud/webhook/create-attribute-acordell",
  GET_ATTRIBUTE_TERMS: "https://n8n.srv917960.hstgr.cloud/webhook/get-attribute-terms-acordell", // ?attribute_id={id}
  CREATE_ATTRIBUTE_TERM: "https://n8n.srv917960.hstgr.cloud/webhook/create-attribute-term-acordell",

  // Product Creation
  CREATE_SIMPLE_PRODUCT: "https://n8n.srv917960.hstgr.cloud/webhook/create-product-acordell",
  CREATE_VARIABLE_PRODUCT: "https://n8n.srv917960.hstgr.cloud/webhook/create-variable-product-acordell"
};
```

---

## 2. API Contracts & Payload Schemas

### A. GET Endpoints (JSON Responses)

1. **GET Categories**: `GET /webhook/get-categories-acordell`
   - Response: `Array<{ id: number, name: string, slug: string, parent: number, count: number }>`
2. **GET Brands**: `GET /webhook/get-brands-acordell`
   - Response: `Array<{ id: number, name: string, slug: string, count: number }>`
3. **GET Attributes**: `GET /webhook/get-attributes-acordell`
   - Response: `Array<{ id: number, name: string, slug: string, type: string, order_by: string }>`
4. **GET Attribute Terms**: `GET /webhook/get-attribute-terms-acordell?attribute_id={id}`
   - Response: `{ success: boolean, attribute_id: number, terms: Array<{ id: number, name: string, slug: string, count: number }> }`

---

### B. POST Taxonomy Creation Endpoints (JSON Payloads)

1. **Create Category**: `POST /webhook/create-category-acordell`
   - Payload: `{ "name": "Men's Apparel", "parent": 0 }`
2. **Create Brand**: `POST /webhook/create-brand-acordell`
   - Payload: `{ "name": "Nike" }`
3. **Create Attribute**: `POST /webhook/create-attribute-acordell`
   - Payload: `{ "name": "Size", "slug": "pa_size" }`
4. **Create Attribute Term**: `POST /webhook/create-attribute-term-acordell`
   - Payload: `{ "attribute_id": 2, "name": "120 ML" }`

---

### C. POST Product Creation Endpoints (Multipart/Form-Data)

#### 1. Simple Product (`POST /webhook/create-product-acordell`)

`multipart/form-data` fields:
- `name` *(string, required)*: Product Title
- `description` *(string, required)*: Product Description
- `regular_price` *(string/number, required)*: Regular Price
- `sale_price` *(string/number, optional)*: Sale Price
- `sku` *(string, optional)*: Product SKU
- `stock_mode` *(string)*: `'in_stock'` | `'out_of_stock'` | `'track_quantity'`
- `quantity` *(number, required if stock_mode === 'track_quantity')*: Stock quantity
- `categories` *(string)*: JSON stringified array of category IDs, e.g. `"[12, 45]"`
- `brand` / `brands` *(string/array, optional)*: Brand ID or JSON stringified array of brand IDs, e.g. `"[12, 34]"` or `"12"`
- `tags` *(string)*: JSON stringified array of tag strings, e.g. `'["cotton", "summer"]'`
- `product_image` *(file, required)*: Main Image binary
- `gallery_image_0`, `gallery_image_1`, ... *(file, optional)*: Gallery image binaries
- `gallery_count` *(string/number)*: Number of gallery images sent

---

#### 2. Variable Product (`POST /webhook/create-variable-product-acordell`)

`multipart/form-data` fields:
- `name` *(string, required)*: Parent Product Title
- `description` *(string, required)*: Parent Product Description
- `sku` *(string, optional)*: Parent SKU
- `categories` *(string)*: JSON stringified array of category IDs, e.g. `"[12, 45]"`
- `brand` / `brands` *(string/array, optional)*: Brand ID or JSON stringified array of brand IDs, e.g. `"[12, 34]"` or `"12"`
- `tags` *(string)*: JSON stringified array of tag strings, e.g. `'["tshirt", "men"]'`
- `attributes` *(string, required)*: JSON stringified array of attributes:
  ```json
  [
    {
      "id": 1,
      "name": "Color",
      "options": ["Red", "Blue"],
      "variation": true,
      "visible": true
    },
    {
      "id": 2,
      "name": "Size",
      "options": ["100 ML", "200 ML"],
      "variation": true,
      "visible": true
    }
  ]
  ```
- `variations` *(string, required)*: JSON stringified array of variation objects:
  ```json
  [
    {
      "attributes": [
        { "id": 1, "name": "Color", "option": "Red" },
        { "id": 2, "name": "Size", "option": "100 ML" }
      ],
      "regular_price": "499",
      "sale_price": "399",
      "sku": "TSHIRT-RED-100",
      "gtin": "123456789012",
      "manage_stock": true,
      "stock_quantity": 25,
      "stock_status": "instock",
      "weight": "0.3",
      "dimensions": { "length": "10", "width": "5", "height": "2" },
      "description": "Red 100ML edition",
      "virtual": false,
      "downloadable": false
    }
  ]
  ```
- `product_image` *(file, required)*: Parent product main image binary
- `gallery_image_0`, `gallery_image_1`, ... *(file, optional)*: Parent gallery images
- `gallery_count` *(string/number)*: Number of parent gallery images
- `variation_image_0`, `variation_image_1`, ... *(file, optional)*: **Individual child variation photos** attached to the variation at index `0`, `1`, etc.

---

## 3. React Native UI/UX Specifications

### A. Navigation & Top Mode Selector
- Segmented Control / Tab Switcher: `[ Simple Product | Variable Product ]`.

### B. Media & Image Picking
- Use `react-native-image-picker` or `expo-image-picker`.
- **Main Image**: Prominent upload box with preview thumbnail, replace, and remove actions.
- **Gallery Images**: Horizontal scrollable list or grid with `+ Add Image` button and delete badge on each thumbnail.
- **Child Variation Photos**: Each variation card must have its own dedicated square image picker with preview thumbnail.
- **React Native FormData Helper**:
  ```typescript
  export const formatFileForFormData = (imageAsset: { uri: string; fileName?: string; type?: string }) => ({
    uri: Platform.OS === 'android' ? imageAsset.uri : imageAsset.uri.replace('file://', ''),
    name: imageAsset.fileName || `image_${Date.now()}.jpg`,
    type: imageAsset.type || 'image/jpeg'
  });
  ```

### C. Taxonomies & Metadata
1. **Category Picker**:
   - Multi-select modal / bottom sheet with search bar.
   - Display hierarchical category tree with indentation (`— Subcategory`).
   - Quick `+ New Category` button opening an inline modal (`POST /webhook/create-category-acordell`).
2. **Brand Picker**:
   - Single-select modal / dropdown with search.
   - `+ New Brand` button opening an inline modal (`POST /webhook/create-brand-acordell`).
3. **Tags Input**:
   - Tag chip input component.
   - Automatically convert typed text to a tag chip when pressing **Comma**, **Enter**, or on **Blur**.
   - Show removable chips (`[ Cotton × ] [ Summer × ]`).

---

### D. Variable Product Dynamic Attributes & Terms Selection Flow

1. **Global Attributes Dropdown**:
   - Fetches global attributes from `GET /webhook/get-attributes-acordell`.
   - Dropdown with `+ Add Attribute` button and `+ Create New Attribute` modal button.
2. **Attribute Card & Dynamic Terms Dropdown**:
   - Adding an attribute renders a dedicated card for that attribute.
   - **Immediately fetches terms** for that attribute: `GET /webhook/get-attribute-terms-acordell?attribute_id={id}`.
   - Renders an interactive **Multi-Select Terms Dropdown / Bottom Sheet**:
     - Live search filter to find terms.
     - Quick action buttons: **Select All**, **Select None**, and **`+ Add New Value`** (creates a new term in WooCommerce via `POST /webhook/create-attribute-term-acordell`).
     - List of terms with checkboxes and product count badges (e.g. `[✓] 100 ML (2 products)`).
     - Selected terms rendered as chips with `×` remove buttons.
   - Checkbox options: `[x] Visible on product page`, `[x] Used for variations`.

---

### E. Variations Generator & Card Management

1. **Cartesian Product Generator**:
   - Compute all combinations across selected terms of attributes where `isVariation === true`.
   ```typescript
   export function cartesianProduct<T>(arrays: T[][]): T[][] {
     return arrays.reduce<T[][]>(
       (acc, curr) => acc.flatMap(a => curr.map(c => [...a, c])),
       [[]]
     );
   }
   ```
2. **Bulk Pricing Toolbar**:
   - "⚡ Apply Bulk Regular & Sale Price to All Variations" modal.
3. **Variation Accordion Card Layout** *(Matching WooCommerce UI)*:
   - **Header**: `#<Index> [ <Selected Term 1> / <Selected Term 2> ]` with `Expand / Collapse` and `Remove` button.
   - **Body (when expanded)**:
     - **Image Picker Box**: Tap to upload child variation photo with preview & remove.
     - **SKU & GTIN/UPC/EAN Inputs**: With helper labels.
     - **Flags Row**: `[x] Enabled`, `[ ] Manage stock?`, `[ ] Virtual`, `[ ] Downloadable`.
     - **Pricing Row**: `Regular price (₹)` *(Required)* and `Sale price (₹)`.
     - **Stock Config**: `Stock status` dropdown (`In stock`, `Out of stock`, `On backorder`) OR `Stock quantity` input when `Manage stock?` is checked.
     - **Physical Dimensions**: `Weight (kg)`, `Dimensions (L × W × H) (cm)` with Length, Width, Height inputs.
     - **Variation Description**: Multi-line text input.

---

---

## 4. Frontend Required Fields & Validation Matrix

The React Native UI **must strictly enforce visual indicators** (red required asterisk `<Text style={{ color: '#ef4444' }}>*</Text>`) and validate all required inputs prior to triggering the network request:

### A. Simple Product Screen Field Matrix

| Field | Requirement | Visual Indicator | Validation Rule & Error Message |
|---|---|---|---|
| **Product Name / Title** | **Required** | `Product Name *` | Non-empty string. Error: *"Product name is required."* |
| **Description** | **Required** | `Description *` | Non-empty string. Error: *"Description is required."* |
| **Main Product Image** | **Required** | `Product Image *` | Must pick 1 valid image (JPG, PNG, WebP). Error: *"Main product image is required."* |
| **Categories** | **Required** | `Categories *` | Must select at least 1 category ID. Error: *"Please select at least one category."* |
| **Regular Price (₹)** | **Required** | `Regular price (₹) *` | Must be a valid positive number (`>= 0`). Error: *"Regular price is required and must be ≥ 0."* |
| **Sale Price (₹)** | *Optional* | `Sale price (₹) (Optional)` | If filled, must be `< Regular Price`. Error: *"Sale price cannot exceed regular price."* |
| **Stock Management** | *Conditional* | Depends on mode | If `track_quantity` selected, `Quantity *` is required (`>= 1` integer). Error: *"Quantity is required when tracking stock."* |
| **Brand** | *Optional* | `Brand (Optional)` | Single brand ID or empty. |
| **Product Tags** | *Optional* | `Tags (Optional)` | Array of strings or empty. Flush pending text on blur/submit. |
| **SKU** | *Optional* | `SKU (Optional)` | String or empty. |
| **Gallery Images** | *Optional* | `Gallery Images (Optional)` | Array of images or empty. |

---

### B. Variable Product Screen Field Matrix

| Field | Requirement | Visual Indicator | Validation Rule & Error Message |
|---|---|---|---|
| **Parent Product Name** | **Required** | `Product Name *` | Non-empty string. Error: *"Product name is required."* |
| **Parent Description** | **Required** | `Description *` | Non-empty string. Error: *"Description is required."* |
| **Parent Main Image** | **Required** | `Product Image *` | Must pick 1 valid image. Error: *"Main product image is required."* |
| **Categories** | **Required** | `Categories *` | Must select at least 1 category. Error: *"Please select at least one category."* |
| **Attributes Section** | **Required** | `Product Attributes *` | Must add at least 1 attribute. Error: *"Please add at least one product attribute."* |
| **Attribute Terms** | **Required** | `Select Terms / Values *` | Each added attribute must have `>= 1` term selected. Error: *"Please select at least one value for attribute <Name>."* |
| **Generated Variations** | **Required** | `Variations *` | Must click 'Generate All Variations' and have `>= 1` variation card. Error: *"Please generate at least one variation."* |
| **Variation Regular Price** | **Required (Per Variation)** | `Regular price (₹) *` | **Each individual variation child card** must have `regular_price >= 0`. Error: *"Variation #<ID>: Regular price is required."* |
| **Variation Manage Stock** | *Conditional (Per Variation)* | `Stock quantity *` | If `manage_stock` is checked on a variation, `stock_quantity >= 0` is required. Error: *"Variation #<ID>: Stock quantity is required when managing stock."* |
| **Variation Sale Price** | *Optional* | `Sale price (₹)` | If filled, must be `< regular_price`. |
| **Variation Photo / Image**| *Optional* | `Photo (Optional)` | Specific child image binary. |
| **Variation SKU & GTIN** | *Optional* | `SKU / GTIN (Optional)` | String or empty. |
| **Variation Dimensions** | *Optional* | `Dimensions (Optional)` | Weight (kg), Length, Width, Height. |
| **Variation Description** | *Optional* | `Description (Optional)` | Text or empty. |
| **Parent SKU** | *Optional* | `Parent SKU (Optional)` | String or empty. |
| **Brand & Tags** | *Optional* | `(Optional)` | Brand ID & Tags array. |
| **Gallery Images** | *Optional* | `(Optional)` | Parent gallery images array. |

---

### C. Taxonomy Creation Modals Field Matrix

| Modal | Required Field | Validation Rule |
|---|---|---|
| **Add New Category** | `Category Name *` | Non-empty string. Parent category is optional. |
| **Add New Brand** | `Brand Name *` | Non-empty string. |
| **Add New Attribute** | `Attribute Name *` | Non-empty string. Slug is optional. |
| **Add New Attribute Term** | `Term / Value Name *` | Non-empty string. |

---

## 5. Form Validation & Submission Workflow

1. **Pre-Submission Validation Sequence**:
   ```typescript
   export function validateVariableProductForm(
     formData: VariableProductFormState,
     attributes: ProductAttributeState[],
     variations: VariationItem[],
     mainImage: ImageAsset | null
   ): { isValid: boolean; errors: string[] } {
     const errors: string[] = [];

     if (!formData.name.trim()) errors.push('Product name is required.');
     if (!formData.description.trim()) errors.push('Description is required.');
     if (!mainImage) errors.push('Main product image is required.');
     if (formData.selectedCategories.length === 0) errors.push('Please select at least one category.');
     if (attributes.length === 0) errors.push('Please add at least one product attribute.');
     
     attributes.forEach(attr => {
       if (attr.selectedTermIds.length === 0) {
         errors.push(`Attribute "${attr.name}" has no values selected.`);
       }
     });

     if (variations.length === 0) {
       errors.push('Please click "Generate All Variations" to generate product variations.');
     } else {
       variations.forEach((v, index) => {
         if (!v.regular_price || parseFloat(v.regular_price) < 0) {
           errors.push(`Variation #${index + 1}: Regular price is required and must be ≥ 0.`);
         }
         if (v.manage_stock && (v.stock_quantity === null || v.stock_quantity === undefined || v.stock_quantity < 0)) {
           errors.push(`Variation #${index + 1}: Stock quantity is required when managing stock.`);
         }
         if (v.sale_price && parseFloat(v.sale_price) >= parseFloat(v.regular_price)) {
           errors.push(`Variation #${index + 1}: Sale price must be less than regular price.`);
         }
       });
     }

     return { isValid: errors.length === 0, errors };
   }
   ```

2. **Submission Progress & Error Handling**:
   - Show a full-screen or modal loading spinner with progress text (*"Uploading images & creating WooCommerce product..."*).
   - If validation fails, display a toast or Alert dialog with the exact list of missing required fields.
   - On network failure or n8n error, display the server error message with a *"Retry"* button.
   - On success, show a confirmation modal with the created Product ID and a *"Create Another Product"* action.

---

## 6. TypeScript Interfaces

```typescript
export interface Category {
  id: number;
  name: string;
  slug: string;
  parent: number;
  count: number;
}

export interface Brand {
  id: number;
  name: string;
  slug: string;
  count: number;
}

export interface Attribute {
  id: number;
  name: string;
  slug: string;
  type?: string;
  order_by?: string;
}

export interface AttributeTerm {
  id: number;
  name: string;
  slug: string;
  count: number;
}

export interface ProductAttributeState {
  id: number;
  name: string;
  slug: string;
  terms: AttributeTerm[];
  selectedTermIds: number[];
  isVariation: boolean;
  isVisible: boolean;
  isLoadingTerms?: boolean;
}

export interface VariationAttributeSelection {
  id: number;
  name: string;
  option: string;
}

export interface VariationItem {
  id: number;
  attributes: VariationAttributeSelection[];
  regular_price: string;
  sale_price: string;
  sku: string;
  gtin: string;
  stock_status: 'instock' | 'outofstock' | 'onbackorder';
  manage_stock: boolean;
  stock_quantity: number | null;
  weight: string;
  dimensions: {
    length: string;
    width: string;
    height: string;
  };
  description: string;
  virtual: boolean;
  downloadable: boolean;
  imageFile?: { uri: string; fileName?: string; type?: string } | null;
  imagePreviewUrl?: string;
}
```
