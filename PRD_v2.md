
# Product Requirements Document: Locus Assistant v2

## 1. Introduction

The Locus Assistant is a web-based application designed to streamline the process of validating Goods Receipt Notes (GRNs) against order data from the Locus platform. The core challenge is that GRNs are often inconsistent, with missing SKU numbers, product names in different languages (Arabic), and varying units of measurement. This application solves this by using Google's Gemini AI and the GS1 GTIN database to intelligently and automatically validate deliveries, ensuring accuracy and efficiency.

## 2. User Personas

| Persona | Description |
| :--- | :--- |
| **Logistics Coordinator** | Responsible for overseeing the delivery process, ensuring that orders are fulfilled correctly, and resolving any discrepancies between the order and the delivery. Needs a clear, at-a-glance view of validation status and detailed reports for investigating issues. |

## 3. Functional Requirements

### 3.1. Dashboard & Order Management

| Requirement ID | Description |
| :--- | :--- |
| **DASH-001** | The application shall display a dashboard with a list of orders for a selected date, defaulting to the current date. |
| **DASH-002** | **Search:** The user shall be able to perform a real-time search on the dashboard by Order ID, Location Name, Rider Name, and Vehicle Registration. |
| **DASH-003** | **Filtering:** The user shall be able to filter the orders list by:
- Validation Status (All, Validated, Pending Validation, Invalid)
- Date |
| **DASH-004** | The dashboard view for each order shall include: Order ID, Location, Rider Name, Order Status, and a clear visual indicator of the GRN Validation Status (e.g., a colored badge: Green for "Valid", Red for "Invalid", Grey for "Pending"). |

### 3.2. Order Validation Workflow

This workflow is triggered when a user initiates a validation for an order.

| Step | Action | System Requirement |
| :--- | :--- | :--- |
| 1 | **Data Fetching** | The system fetches the order details (including line items) and the GRN image URL from the Locus API. |
| 2 | **AI Data Extraction** | The system sends the GRN image to the Google Gemini AI with a detailed prompt to extract all visible text, focusing on item names, quantities, units, SKUs, and any 13-digit numbers (potential GTINs). |
| 3 | **Item Matching** | For each item in the original order, the system attempts to find a corresponding item in the data extracted from the GRN using the following prioritized logic: |
| 3a | **Primary Match: SKU** | The system first attempts to match the `order.sku_id` with an `extracted_sku` from the GRN. |
| 3b | **Secondary Match: GTIN** | If no SKU match is found, the system looks for an `extracted_gtin` in the GRN data. It then queries the GS1 API ("GTIN Explorer") with this GTIN. |
| 3c | **Fuzzy Name Matching** | If the GS1 lookup is successful, the system performs a fuzzy match between the product name returned by GS1 and the `extracted_name` from the GRN (which may be in Arabic). The `calculate_bilingual_match` function is used for this. If the names are a close match, the GRN item is linked to the order item. |
| 4 | **Quantity Validation** | Once an item is matched, the system validates the quantity. It must be able to handle discrepancies in the Unit of Measurement (UoM). For example, if the order specifies "12 units" and the GRN shows "1 box", the AI-driven extraction should be prompted to recognize and equate these. |
| 5 | **Discrepancy Identification** | The system identifies and flags all discrepancies, including: `MISSING_ITEM`, `EXTRA_ITEM`, `QUANTITY_MISMATCH`, `GTIN_NAME_MISMATCH`, and `GTIN_NOT_VERIFIED`. |
| 6 | **Data Persistence** | The entire validation result, including the raw AI response, extracted items, discrepancies, and GTIN verification details, is saved to the PostgreSQL database (`ValidationResult` table). This prevents the need for re-processing. |

### 3.3. Order Details & Validation View

| Requirement ID | Description |
| :--- | :--- |
| **DETAIL-001** | When a user clicks an order, they are taken to the Order Detail page, which shall be divided into clear sections. |
| **DETAIL-002** | **Order Summary:** Displays key order info: Order ID, Location, Rider, etc. |
| **DETAIL-003** | **Validation Summary:** Displays the final validation status (`VALID`/`INVALID`), overall confidence score, and a summary of findings (e.g., "3 items matched, 1 missing, 1 quantity mismatch"). |
| **DETAIL-004** | **Side-by-Side View:** Presents a clear, two-column table:
- **Column 1: Expected Items (from Order):** Shows `Name`, `SKU`, `Quantity`.
- **Column 2: Found Items (from GRN):** Shows the matched item with its `Extracted Name`, `Extracted Quantity`, and the source of the match (`SKU` or `GTIN`). Discrepancies in quantity should be highlighted in red. |
| **DETAIL-005** | **Discrepancy Report:** A list of all identified discrepancies with detailed descriptions (e.g., "Expected: 10, Actual: 8"). |
| **DETAIL-006** | **Unmatched GRN Items:** A list of items that were found on the GRN but could not be matched to any item in the order. |
| **DETAIL-007** | **GTIN Verification Details:** If a GTIN was used for matching, this section will show the GTIN, the product info returned from GS1, and the confidence score of the fuzzy name match. |

### 3.4. Data Models & Persistence

| Requirement ID | Description |
| :--- | :--- |
| **DATA-001** | All order and validation data must be stored in the PostgreSQL database to ensure data integrity and avoid redundant API calls. |
| **DATA-002** | The `orders` table shall cache the primary order data fetched from Locus. |
| **DATA-003** | The `validation_results` table shall store the complete output of a validation run, including `is_valid`, `confidence_score`, `extracted_items` (as JSON), `discrepancies` (as JSON), and `gtin_verification` (as JSON). |

## 4. Non-Functional Requirements

| Requirement ID | Description |
| :--- | :--- |
| **NFR-001** | **Performance:** The application should be responsive, with page load times under 3 seconds. Dashboard filtering and search should be instantaneous. |
| **NFR-002** | **Usability:** The UI must be intuitive. Discrepancies and validation results should be presented in a clear, color-coded, and easy-to-understand manner. |
| **NFR-003** | **Data Accuracy:** The fuzzy matching algorithm for Arabic names must be tuned for high accuracy. The system's confidence in a validation should be clearly communicated to the user. |
| **NFR-004** | **Reliability:** The application must handle API errors (Locus, Google AI, GS1) gracefully and provide informative error messages to the user. |

## 5. API Dependencies

| API | Purpose |
| :--- | :--- |
| **Locus API** | To fetch order and delivery data. |
| **Google Gemini AI API** | For analyzing GRN documents and extracting information. |
| **GS1 API** | For verifying GTIN (barcode) information. |
